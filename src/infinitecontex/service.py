"""Application service orchestration for Infinite Context."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import orjson

from infinitecontex.capture.chat_ingest import extract_chat_text, ingest_chat_text
from infinitecontex.capture.git_state import recent_commits, recent_diff_summary
from infinitecontex.capture.repo_scan import scan_behavioral, scan_structural
from infinitecontex.capture.terminal import summarize_terminal_log
from infinitecontex.capture.working_set import build_working_set
from infinitecontex.core.config import AppConfig, load_app_config, save_repo_config
from infinitecontex.core.models import (
    BehavioralContext,
    DecisionRecord,
    IntentContext,
    PinRecord,
    PromptMode,
    Snapshot,
    SnapshotComparison,
    SnapshotSummary,
    StructuralContext,
    WorkingSetContext,
)
from infinitecontex.core.redaction import redact_list, redact_text
from infinitecontex.core.serde import dump_json
from infinitecontex.decisions.store import DecisionStore
from infinitecontex.distill.summarizer import compile_packet
from infinitecontex.doctor.checks import run_doctor
from infinitecontex.events.logger import EventLogger
from infinitecontex.graph.store import ContextGraphStore
from infinitecontex.prompt.compiler import PromptCompiler
from infinitecontex.restore.engine import validate_restore
from infinitecontex.retrieval.search import RetrievalEngine
from infinitecontex.storage.db import Database
from infinitecontex.storage.export_import import export_state, import_state
from infinitecontex.storage.layout import build_layout, initialize_layout


class InfiniteContextService:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.layout = build_layout(project_root)
        self.db = Database(self.layout.metadata / "state.db")
        self.retrieval = RetrievalEngine(self.db)
        self.decisions = DecisionStore(self.db)
        self.compiler = PromptCompiler()

    def init(self) -> dict[str, str]:
        self.layout = initialize_layout(self.project_root)
        self.db = Database(self.layout.metadata / "state.db")
        self.db.migrate()
        EventLogger(self.layout.events / "events.jsonl").log("init", {"root": str(self.project_root)})
        return {"status": "initialized", "root": str(self.layout.root)}

    def status(self) -> dict[str, object]:
        latest = self._latest_snapshot_id()
        pins = self.list_pins()
        intent_payload = self._status_intent_payload(latest)
        latest_snapshot = self._load_snapshot(latest) if latest is not None else None
        return {
            "project_root": str(self.project_root),
            "branch": self._branch(),
            "latest_snapshot": latest,
            "latest_snapshot_created_at": (
                latest_snapshot.created_at.isoformat() if latest_snapshot is not None else None
            ),
            "snapshot_count": len(self._snapshot_ids_desc()),
            "pins": pins,
            "recent_commits": recent_commits(self.project_root, limit=5),
            "developer_goal": cast(str, intent_payload.get("developer_goal", "")),
            "active_tasks": cast(list[str], intent_payload.get("active_tasks", [])),
            "unresolved_issues": cast(list[str], intent_payload.get("unresolved_issues", [])),
            "selected_source": cast(str | None, intent_payload.get("selected_source")),
        }

    def snapshot(self, goal: str = "") -> Snapshot:
        self._ensure_ready()
        cfg = load_app_config(self.project_root)
        structural, behavioral, fingerprints = self._capture_repo_context(cfg)
        runtime = self._capture_runtime_context(cfg)
        working = self._capture_working_context(runtime)
        intent = self._capture_intent_context(goal=goal, working=working)

        snapshot = Snapshot(
            id=self._new_snapshot_id(),
            project_root=str(self.project_root),
            structural=structural,
            behavioral=behavioral,
            intent=intent,
            working_set=working,
            fingerprints=fingerprints,
            metrics={
                "file_count": len(fingerprints),
                "token_budget": cfg.policies.token.default_budget,
                "decision_count": len(intent.decisions),
                "active_task_count": len(intent.active_tasks),
                "file_insight_count": len(structural.file_insights),
            },
        )

        self._save_snapshot(snapshot)
        packet = compile_packet(snapshot, budget=cfg.policies.token.default_budget)
        prompt_text = self.compiler.compile(packet, PromptMode.GENERIC_AGENT_RESTORE)
        prompt_path = self.layout.prompts / f"{snapshot.id}.prompt.md"
        prompt_path.write_text(prompt_text, encoding="utf-8")
        self._write_project_handoff(snapshot, prompt_text)

        graph = ContextGraphStore(self.layout.graph / "context_graph.json")
        graph.add_file_nodes([fp.path for fp in snapshot.fingerprints])
        graph.add_calls(snapshot.behavioral.call_hints)
        graph.save()

        self.retrieval.index_document("snapshot", snapshot.id, prompt_text)
        EventLogger(self.layout.events / "events.jsonl").log("snapshot", {"id": snapshot.id})
        return snapshot

    def restore(self, snapshot_id: str | None = None) -> dict[str, object]:
        resolved_id = snapshot_id if snapshot_id is not None else self._latest_snapshot_id(required=True)
        if resolved_id is None:
            raise ValueError("no snapshots found")
        snapshot = self._load_snapshot(resolved_id)
        report = validate_restore(snapshot, self.project_root)
        out_path = self.layout.summaries / f"restore-{snapshot.id}.json"
        dump_json(out_path, report.model_dump(mode="json"))
        EventLogger(self.layout.events / "events.jsonl").log("restore", {"snapshot": snapshot.id})
        return report.model_dump(mode="json")

    def note(self, summary: str, rationale: str, alternatives: list[str], impact: str, tags: list[str]) -> str:
        self._ensure_ready()
        record = DecisionRecord(
            id=f"dec-{uuid4().hex[:12]}",
            summary=summary,
            rationale=rationale,
            alternatives=alternatives,
            impact=impact,
            tags=tags,
        )
        self.decisions.add(record)
        EventLogger(self.layout.events / "events.jsonl").log("decision", {"id": record.id, "summary": summary})
        return record.id

    def pin(self, path: str, note: str) -> None:
        self._ensure_ready()
        self.db.execute(
            "INSERT OR REPLACE INTO pins(path, note, created_at) VALUES (?, ?, ?)",
            (path, note, datetime.now(UTC).isoformat()),
        )
        EventLogger(self.layout.events / "events.jsonl").log("pin", {"path": path, "note": note})

    def list_pins(self) -> list[str]:
        if not (self.layout.metadata / "state.db").exists():
            return []
        rows = self.db.query("SELECT path FROM pins ORDER BY created_at DESC")
        return [str(row["path"]) for row in rows]

    def pin_records(self) -> list[PinRecord]:
        if not (self.layout.metadata / "state.db").exists():
            return []
        rows = self.db.query("SELECT path, note, created_at FROM pins ORDER BY created_at DESC")
        return [
            PinRecord(
                path=str(row["path"]),
                note=str(row["note"]),
                created_at=datetime.fromisoformat(str(row["created_at"])),
            )
            for row in rows
        ]

    def unpin(self, path: str) -> bool:
        self._ensure_ready()
        existing = self.db.query("SELECT 1 FROM pins WHERE path = ? LIMIT 1", (path,))
        if not existing:
            return False
        self.db.execute("DELETE FROM pins WHERE path = ?", (path,))
        EventLogger(self.layout.events / "events.jsonl").log("unpin", {"path": path})
        return True

    def ingest_chat(self, chat_path: Path) -> dict[str, object]:
        self._ensure_ready()
        payload = ingest_chat_text(chat_path)
        payload["selected_source"] = "file"
        payload["selected_path"] = str(chat_path)
        payload["source_text"] = extract_chat_text(chat_path)
        return self.ingest_chat_payload(payload)

    def ingest_chat_payload(self, payload: dict[str, Any]) -> dict[str, object]:
        self._ensure_ready()
        cfg = load_app_config(self.project_root)
        patterns = cfg.policies.privacy.redact_patterns
        source_text = str(payload.get("source_text", ""))
        source_path = str(payload.get("selected_path") or payload.get("file") or "")

        if source_text:
            source_key = Path(source_path).name if source_path else str(payload.get("selected_source", "auto-chat"))
            self.retrieval.index_document("chat", source_key, redact_text(source_text, patterns))

        EventLogger(self.layout.events / "events.jsonl").log(
            "ingest_chat",
            {"file": source_path or str(payload.get("selected_source", "auto"))},
        )
        persisted_payload = dict(payload)
        persisted_payload.pop("source_text", None)
        return self._finalize_ingest(persisted_payload)

    def _finalize_ingest(self, payload: dict[str, Any]) -> dict[str, object]:
        cfg = load_app_config(self.project_root)
        patterns = cfg.policies.privacy.redact_patterns
        payload_redacted = cast(dict[str, object], self._redact_value(payload, patterns))
        dump_json(self.layout.working_set / "intent_state.json", payload_redacted)
        return payload_redacted

    def diff_summary(self) -> list[str]:
        return recent_diff_summary(self.project_root)

    def snapshots_recent(self, limit: int = 20) -> list[SnapshotSummary]:
        snapshot_ids = self._snapshot_ids_desc(limit=limit)
        return [self._snapshot_summary(self._load_snapshot(snapshot_id)) for snapshot_id in snapshot_ids]

    def snapshot_details(self, snapshot_id: str | None = None) -> dict[str, object]:
        resolved_id = snapshot_id if snapshot_id is not None else self._latest_snapshot_id(required=True)
        if resolved_id is None:
            raise ValueError("no snapshots found")
        snapshot = self._load_snapshot(resolved_id)
        payload = snapshot.model_dump(mode="json")
        payload["prompt_path"] = str(self.layout.prompts / f"{snapshot.id}.prompt.md")
        payload["agent_dir"] = str(self.layout.agents)
        return payload

    def compare_snapshots(
        self, from_snapshot_id: str | None = None, to_snapshot_id: str | None = None
    ) -> SnapshotComparison:
        snapshot_ids = self._snapshot_ids_desc()
        if not snapshot_ids:
            raise ValueError("no snapshots found")

        resolved_to = to_snapshot_id or snapshot_ids[0]
        if from_snapshot_id is None:
            if resolved_to not in snapshot_ids:
                raise ValueError(f"snapshot not found: {resolved_to}")
            resolved_to_index = snapshot_ids.index(resolved_to)
            if resolved_to_index + 1 >= len(snapshot_ids):
                raise ValueError("at least two snapshots are required to compare")
            resolved_from = snapshot_ids[resolved_to_index + 1]
        else:
            resolved_from = from_snapshot_id

        before = self._load_snapshot(resolved_from)
        after = self._load_snapshot(resolved_to)

        before_files = {fp.path: fp.sha1 for fp in before.fingerprints}
        after_files = {fp.path: fp.sha1 for fp in after.fingerprints}
        shared_files = set(before_files) & set(after_files)

        before_active_files = set(before.working_set.active_files)
        after_active_files = set(after.working_set.active_files)
        before_tasks = set(before.intent.active_tasks)
        after_tasks = set(after.intent.active_tasks)
        before_issues = set(before.intent.unresolved_issues)
        after_issues = set(after.intent.unresolved_issues)

        metric_deltas: dict[str, float] = {}
        for key in sorted(set(before.metrics) | set(after.metrics)):
            before_value = before.metrics.get(key)
            after_value = after.metrics.get(key)
            if isinstance(before_value, (int, float)) and isinstance(after_value, (int, float)):
                metric_deltas[key] = round(float(after_value) - float(before_value), 2)

        comparison = SnapshotComparison(
            from_snapshot_id=before.id,
            to_snapshot_id=after.id,
            from_created_at=before.created_at,
            to_created_at=after.created_at,
            from_goal=before.intent.developer_goal,
            to_goal=after.intent.developer_goal,
            from_branch=before.working_set.branch,
            to_branch=after.working_set.branch,
            added_tracked_files=sorted(set(after_files) - set(before_files)),
            removed_tracked_files=sorted(set(before_files) - set(after_files)),
            changed_tracked_files=sorted(path for path in shared_files if before_files[path] != after_files[path]),
            added_active_files=sorted(after_active_files - before_active_files),
            removed_active_files=sorted(before_active_files - after_active_files),
            added_tasks=sorted(after_tasks - before_tasks),
            removed_tasks=sorted(before_tasks - after_tasks),
            added_issues=sorted(after_issues - before_issues),
            removed_issues=sorted(before_issues - after_issues),
            metric_deltas=metric_deltas,
            summary=(
                f"tracked:+{len(set(after_files) - set(before_files))}"
                f"/-{len(set(before_files) - set(after_files))}"
                f"/~{len([path for path in shared_files if before_files[path] != after_files[path]])} "
                f"tasks:+{len(after_tasks - before_tasks)}/-{len(before_tasks - after_tasks)} "
                f"issues:+{len(after_issues - before_issues)}/-{len(before_issues - after_issues)}"
            ),
        )
        return comparison

    def decisions_recent(self, limit: int = 20) -> list[dict[str, object]]:
        return [d.model_dump(mode="json") for d in self.decisions.list_recent(limit=limit)]

    def search(self, query: str, limit: int = 10) -> list[dict[str, object]]:
        return [r.model_dump(mode="json") for r in self.retrieval.search(query, limit)]

    def prompt(self, mode: PromptMode, token_budget: int, snapshot_id: str | None = None) -> str:
        resolved_id = snapshot_id if snapshot_id is not None else self._latest_snapshot_id(required=True)
        if resolved_id is None:
            raise ValueError("no snapshots found")
        snapshot = self._load_snapshot(resolved_id)
        packet = compile_packet(snapshot, budget=token_budget)
        text = self.compiler.compile(packet, mode)
        out = self.layout.prompts / f"{snapshot.id}-{mode.value}.md"
        out.write_text(text, encoding="utf-8")
        return text

    def export(self, output: Path) -> Path:
        self._ensure_ready()
        return export_state(self.project_root, output)

    def import_archive(self, archive: Path) -> None:
        import_state(self.project_root, archive)
        self._ensure_ready()

    def doctor(self) -> dict[str, str]:
        return run_doctor(self.project_root)

    def config_get(self) -> dict[str, object]:
        return load_app_config(self.project_root).model_dump(mode="json")

    def config_set(self, config: AppConfig) -> None:
        save_repo_config(self.project_root, config)

    def _ensure_ready(self) -> None:
        manifest_path = self.layout.metadata / "manifest.json"
        required_dirs = [
            self.layout.metadata,
            self.layout.snapshots,
            self.layout.prompts,
            self.layout.events,
            self.layout.graph,
            self.layout.working_set,
        ]
        if (
            (not self.layout.root.exists())
            or (not manifest_path.exists())
            or any(not path.exists() for path in required_dirs)
        ):
            self.init()
        self.db.migrate()

    def _save_snapshot(self, snapshot: Snapshot) -> None:
        path = self.layout.snapshots / f"{snapshot.id}.json"
        dump_json(path, snapshot.model_dump(mode="json"))
        self.db.execute(
            "INSERT INTO snapshots(id, created_at, payload_json) VALUES (?, ?, ?)",
            (snapshot.id, snapshot.created_at.isoformat(), orjson.dumps(snapshot.model_dump(mode="json")).decode()),
        )

    def _load_snapshot(self, snapshot_id: str) -> Snapshot:
        path = self.layout.snapshots / f"{snapshot_id}.json"
        if path.exists():
            payload = orjson.loads(path.read_bytes())
            return Snapshot.model_validate(payload)

        rows = self.db.query("SELECT payload_json FROM snapshots WHERE id = ?", (snapshot_id,))
        if not rows:
            raise ValueError(f"snapshot not found: {snapshot_id}")
        payload = orjson.loads(str(rows[0]["payload_json"]))
        return Snapshot.model_validate(payload)

    def _latest_snapshot_id(self, required: bool = False) -> str | None:
        if not (self.layout.metadata / "state.db").exists():
            if required:
                raise ValueError("no snapshots found")
            return None
        rows = self.db.query("SELECT id FROM snapshots ORDER BY created_at DESC LIMIT 1")
        if not rows:
            if required:
                raise ValueError("no snapshots found")
            return None
        return str(rows[0]["id"])

    def _snapshot_ids_desc(self, limit: int | None = None) -> list[str]:
        if not (self.layout.metadata / "state.db").exists():
            return []
        sql = "SELECT id FROM snapshots ORDER BY created_at DESC"
        params: tuple[object, ...] = ()
        if limit is not None:
            sql += " LIMIT ?"
            params = (limit,)
        rows = self.db.query(sql, params)
        return [str(row["id"]) for row in rows]

    def _load_intent_state(self) -> dict[str, Any]:
        path = self.layout.working_set / "intent_state.json"
        if not path.exists():
            return {}
        return cast(dict[str, Any], orjson.loads(path.read_bytes()))

    def _status_intent_payload(self, latest_snapshot_id: str | None) -> dict[str, Any]:
        intent_payload = self._load_intent_state()
        if latest_snapshot_id is None:
            return intent_payload

        snapshot_intent = self._load_snapshot(latest_snapshot_id).intent.model_dump(mode="json")
        merged = dict(snapshot_intent)
        for key, value in intent_payload.items():
            if value not in ("", [], {}, None):
                merged[key] = value
        return merged

    def _new_snapshot_id(self) -> str:
        ts = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        return f"snap-{ts}-{uuid4().hex[:8]}"

    def _snapshot_summary(self, snapshot: Snapshot) -> SnapshotSummary:
        return SnapshotSummary(
            id=snapshot.id,
            created_at=snapshot.created_at,
            branch=snapshot.working_set.branch,
            developer_goal=snapshot.intent.developer_goal,
            active_task_count=len(snapshot.intent.active_tasks),
            active_file_count=len(snapshot.working_set.active_files),
            file_count=len(snapshot.fingerprints),
            prompt_path=str(self.layout.prompts / f"{snapshot.id}.prompt.md"),
        )

    def _write_project_handoff(self, snapshot: Snapshot, prompt_text: str) -> None:
        agents_dir = self.layout.agents
        agents_dir.mkdir(parents=True, exist_ok=True)

        # 1. Overview
        overview_md = "\n".join(
            [
                "# Infinite Context - Project Overview",
                f"- **Snapshot:** `{snapshot.id}`",
                f"- **Branch:** `{snapshot.working_set.branch}`",
                f"- **Developer Goal:** {snapshot.intent.developer_goal or 'None active'}",
                f"- **Next Likely Action:** {snapshot.working_set.next_likely_action or 'None'}",
                "",
                "## Active Tasks",
                *[f"- {task}" for task in snapshot.intent.active_tasks[:10]],
                "",
                "## Active Priority Files",
                *[f"- `{path}`" for path in snapshot.working_set.active_files[:25]],
            ]
        )
        (agents_dir / "overview.md").write_text(overview_md, encoding="utf-8")

        # 2. Architecture
        arch_md = ["# Project Architecture\n", "## Directory Map"]
        for d, summary in snapshot.structural.directory_summaries.items():
            arch_md.append(f"- **`{d}/`**: {summary}")
        arch_md.extend(
            [
                "",
                "## Key File Insights",
                *[
                    f"- `{insight.path}`: {insight.summary}"
                    + (f" ({', '.join(insight.symbols[:4])})" if insight.symbols else "")
                    for insight in snapshot.structural.file_insights[:10]
                ],
                "",
                "## Key Files",
                *[f"- `{f}`" for f in snapshot.structural.key_files],
                "",
                "## Entry Points",
                *[f"- `{f}`" for f in snapshot.structural.entry_points],
            ]
        )
        (agents_dir / "architecture.md").write_text("\n".join(arch_md), encoding="utf-8")

        # 3. Decisions
        decisions_md = ["# Architectural Decisions & Intent\n"]
        if snapshot.intent.decisions:
            decisions_md.extend([f"- {d}" for d in snapshot.intent.decisions])
        else:
            decisions_md.append("*No recent decisions recorded.*")
        decisions_md.extend(
            [
                "",
                "## Unresolved Issues",
            ]
        )
        if snapshot.intent.unresolved_issues:
            decisions_md.extend([f"- {i}" for i in snapshot.intent.unresolved_issues])
        else:
            decisions_md.append("*None*")
        decisions_md.extend(["", "## Open Questions"])
        if snapshot.intent.open_questions:
            decisions_md.extend([f"- {question}" for question in snapshot.intent.open_questions])
        else:
            decisions_md.append("*None*")
        (agents_dir / "decisions.md").write_text("\n".join(decisions_md), encoding="utf-8")

        # 4. Behavioral
        behav_md = ["# Behavioral & Logic Patterns\n", "## Commands & Routes"]
        behav_md.extend([f"- `{r}`" for r in snapshot.behavioral.routes_or_commands])
        behav_md.extend(["", "## Test Surfaces"])
        behav_md.extend([f"- `{t}`" for t in snapshot.behavioral.test_surfaces])
        (agents_dir / "behavioral.md").write_text("\n".join(behav_md), encoding="utf-8")

        # 5. Recent Changes
        changes_md = ["# Recent Changes & Work State\n", "## Uncommitted Diffs"]
        if snapshot.working_set.recent_diffs:
            changes_md.extend([f"- {d}" for d in snapshot.working_set.recent_diffs[:30]])
        else:
            changes_md.append("*Workspace is clean.*")

        if snapshot.working_set.last_failed_commands:
            changes_md.extend(["", "## Broken State (Failed Commands)"])
            changes_md.extend([f"- `{cmd}`" for cmd in snapshot.working_set.last_failed_commands])
        (agents_dir / "recent_changes.md").write_text("\n".join(changes_md), encoding="utf-8")

        # 6. Instructions format
        instructions_md = "\n".join(
            [
                "# Infinite Context Agent Instructions",
                "This project utilizes `infinitecontex` to maintain a canonical state memory.",
                "As an AI agent, you must always consult the files in this directory "
                "(`.infctx/agents/`) to understand the codebase.",
                "",
                "- Start with `overview.md` to know what the user is working on.",
                "- Use `architecture.md` to map out the codebase instantly.",
                "- Check `recent_changes.md` to see what broke or changed last.",
                "- Obey the constraints in `decisions.md`.",
            ]
        )
        (agents_dir / "instructions.md").write_text(instructions_md, encoding="utf-8")

        # Also write the legacy single json/md for non-agent backward compat
        handoff_payload = {
            "snapshot_id": snapshot.id,
            "updated_at": datetime.now(UTC).isoformat(),
            "project_root": snapshot.project_root,
        }
        dump_json(self.layout.project / "inside.infinite_context.json", handoff_payload)
        (self.layout.project / "inside.infinite_context.md").write_text(prompt_text, encoding="utf-8")

    def _branch(self) -> str:
        try:
            from infinitecontex.capture.git_state import current_branch

            return current_branch(self.project_root)
        except Exception:
            return "unknown"

    def _capture_repo_context(self, cfg: AppConfig) -> tuple[StructuralContext, BehavioralContext, list[Any]]:
        structural, fingerprints = scan_structural(
            self.project_root,
            max_files=cfg.capture_max_files,
            include_patterns=cfg.include_patterns,
            exclude_patterns=cfg.exclude_patterns,
        )
        behavioral = scan_behavioral(self.project_root, [fp.path for fp in fingerprints])
        return structural, behavioral, fingerprints

    def _capture_runtime_context(self, cfg: AppConfig) -> dict[str, list[str]]:
        terminal = summarize_terminal_log(self.layout.working_set / "terminal.log")
        redact_patterns = cfg.policies.privacy.redact_patterns
        return {
            "successful": redact_list(terminal["successful"], redact_patterns),
            "failed": redact_list(terminal["failed"], redact_patterns),
            "stack_traces": redact_list(terminal["stack_traces"], redact_patterns),
            "failing_tests": redact_list(terminal["failing_tests"], redact_patterns),
        }

    def _capture_working_context(self, runtime: dict[str, list[str]]) -> WorkingSetContext:
        return build_working_set(
            self.project_root,
            pins=self.list_pins(),
            last_successful_commands=runtime["successful"],
            last_failed_commands=runtime["failed"],
            stack_traces=runtime["stack_traces"],
            failing_tests=runtime["failing_tests"],
        )

    def _capture_intent_context(self, goal: str, working: WorkingSetContext) -> IntentContext:
        recent_decisions = [d.summary for d in self.decisions.list_recent(limit=15)]
        intent_payload = self._load_intent_state()
        developer_goal = goal or cast(str, intent_payload.get("developer_goal", ""))
        intent_decisions = cast(list[str], intent_payload.get("decisions", []))
        assumptions = cast(list[str], intent_payload.get("assumptions", []))
        active_tasks = cast(list[str], intent_payload.get("active_tasks", []))
        unresolved_issues = cast(list[str], intent_payload.get("unresolved_issues", []))
        open_questions = cast(list[str], intent_payload.get("open_questions", []))
        signal_sources = cast(dict[str, list[str]], intent_payload.get("signal_sources", {}))

        inferred_change_purpose = developer_goal or (
            "Resolve broken runtime state"
            if working.last_failed_commands or working.failing_tests
            else "Refresh active work"
        )

        return IntentContext(
            developer_goal=developer_goal,
            decisions=recent_decisions + intent_decisions,
            assumptions=assumptions,
            active_tasks=active_tasks,
            unresolved_issues=unresolved_issues,
            open_questions=open_questions,
            signal_sources=signal_sources,
            inferred_change_purpose=inferred_change_purpose,
        )

    def _redact_value(self, value: Any, patterns: list[str]) -> Any:
        if isinstance(value, str):
            return redact_text(value, patterns)
        if isinstance(value, list):
            return [self._redact_value(item, patterns) for item in value]
        if isinstance(value, dict):
            return {key: self._redact_value(item, patterns) for key, item in value.items()}
        return value
