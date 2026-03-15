"""Application service orchestration for Infinite Context."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import uuid4

import orjson

from infinitecontex.capture.chat_ingest import ingest_chat_text
from infinitecontex.capture.git_state import recent_commits, recent_diff_summary
from infinitecontex.capture.repo_scan import scan_behavioral, scan_structural
from infinitecontex.capture.terminal import summarize_terminal_log
from infinitecontex.capture.working_set import build_working_set
from infinitecontex.core.config import AppConfig, load_app_config, save_repo_config
from infinitecontex.core.models import DecisionRecord, PromptMode, Snapshot
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
        return {
            "project_root": str(self.project_root),
            "branch": self._branch(),
            "latest_snapshot": latest,
            "pins": pins,
            "recent_commits": recent_commits(self.project_root, limit=5),
        }

    def snapshot(self, goal: str = "") -> Snapshot:
        self._ensure_ready()
        cfg = load_app_config(self.project_root)
        redact_patterns = cfg.policies.privacy.redact_patterns

        structural, fingerprints = scan_structural(
            self.project_root,
            max_files=cfg.capture_max_files,
            include_patterns=cfg.include_patterns,
            exclude_patterns=cfg.exclude_patterns,
        )
        behavioral = scan_behavioral(self.project_root, [fp.path for fp in fingerprints])

        terminal = summarize_terminal_log(self.layout.working_set / "terminal.log")
        terminal_success = redact_list(terminal["successful"], redact_patterns)
        terminal_failed = redact_list(terminal["failed"], redact_patterns)
        terminal_traces = redact_list(terminal["stack_traces"], redact_patterns)
        terminal_tests = redact_list(terminal["failing_tests"], redact_patterns)
        working = build_working_set(
            self.project_root,
            pins=self.list_pins(),
            last_successful_commands=terminal_success,
            last_failed_commands=terminal_failed,
            stack_traces=terminal_traces,
            failing_tests=terminal_tests,
        )

        recent_decisions = [d.summary for d in self.decisions.list_recent(limit=15)]
        intent_payload = self._load_intent_state()
        developer_goal = goal or cast(str, intent_payload.get("developer_goal", ""))
        intent_decisions = cast(list[str], intent_payload.get("decisions", []))
        assumptions = cast(list[str], intent_payload.get("assumptions", []))
        active_tasks = cast(list[str], intent_payload.get("active_tasks", []))
        unresolved_issues = cast(list[str], intent_payload.get("unresolved_issues", []))

        from infinitecontex.core.models import IntentContext

        intent = IntentContext(
            developer_goal=developer_goal,
            decisions=recent_decisions + intent_decisions,
            assumptions=assumptions,
            active_tasks=active_tasks,
            unresolved_issues=unresolved_issues,
            inferred_change_purpose="Focused edits on active files",
        )

        snapshot = Snapshot(
            id=self._new_snapshot_id(),
            project_root=str(self.project_root),
            structural=structural,
            behavioral=behavioral,
            intent=intent,
            working_set=working,
            fingerprints=fingerprints,
            metrics={"file_count": len(fingerprints), "token_budget": cfg.policies.token.default_budget},
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

    def ingest_chat(self, chat_path: Path) -> dict[str, object]:
        self._ensure_ready()
        cfg = load_app_config(self.project_root)
        patterns = cfg.policies.privacy.redact_patterns
        payload = ingest_chat_text(chat_path)
        payload = {
            key: redact_text(value, patterns) if isinstance(value, str) else redact_list(value, patterns)
            for key, value in payload.items()
        }
        dump_json(self.layout.working_set / "intent_state.json", payload)
        chat_body = chat_path.read_text(encoding="utf-8", errors="ignore")
        self.retrieval.index_document("chat", chat_path.name, redact_text(chat_body, patterns))
        EventLogger(self.layout.events / "events.jsonl").log("ingest_chat", {"file": str(chat_path)})
        return cast(dict[str, object], payload)

    def diff_summary(self) -> list[str]:
        return recent_diff_summary(self.project_root)

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
        if (not self.layout.root.exists()) or (not manifest_path.exists()) or any(
            not path.exists() for path in required_dirs
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

    def _load_intent_state(self) -> dict[str, list[str] | str]:
        path = self.layout.working_set / "intent_state.json"
        if not path.exists():
            return {}
        return cast(dict[str, list[str] | str], orjson.loads(path.read_bytes()))

    def _new_snapshot_id(self) -> str:
        ts = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        return f"snap-{ts}-{uuid4().hex[:8]}"

    def _write_project_handoff(self, snapshot: Snapshot, prompt_text: str) -> None:
        handoff_payload = {
            "snapshot_id": snapshot.id,
            "updated_at": datetime.now(UTC).isoformat(),
            "project_root": snapshot.project_root,
            "branch": snapshot.working_set.branch,
            "goal": snapshot.intent.developer_goal,
            "next_action": snapshot.working_set.next_likely_action,
            "active_files": snapshot.working_set.active_files[:25],
            "recent_diffs": snapshot.working_set.recent_diffs[:25],
            "decisions": snapshot.intent.decisions[:25],
            "unresolved_issues": snapshot.intent.unresolved_issues[:25],
            "prompt_path": str((self.layout.prompts / f"{snapshot.id}.prompt.md").relative_to(self.project_root)),
        }
        dump_json(self.layout.project / "inside.infinite_context.json", handoff_payload)

        handoff_md = "\n".join(
            [
                "# Inside Infinite Context",
                "",
                f"Snapshot: {snapshot.id}",
                f"Updated: {handoff_payload['updated_at']}",
                f"Branch: {snapshot.working_set.branch}",
                f"Goal: {snapshot.intent.developer_goal or 'n/a'}",
                f"Next action: {snapshot.working_set.next_likely_action or 'n/a'}",
                "",
                "## Active Files",
                *[f"- {path}" for path in snapshot.working_set.active_files[:25]],
                "",
                "## Recent Diffs",
                *[f"- {line}" for line in snapshot.working_set.recent_diffs[:25]],
                "",
                "## Decisions",
                *[f"- {item}" for item in snapshot.intent.decisions[:25]],
                "",
                "## Unresolved Issues",
                *[f"- {item}" for item in snapshot.intent.unresolved_issues[:25]],
                "",
                "## Compact Restore Prompt",
                "",
                prompt_text,
            ]
        )
        (self.layout.project / "inside.infinite_context.md").write_text(handoff_md, encoding="utf-8")

    def _branch(self) -> str:
        try:
            from infinitecontex.capture.git_state import current_branch

            return current_branch(self.project_root)
        except Exception:
            return "unknown"
