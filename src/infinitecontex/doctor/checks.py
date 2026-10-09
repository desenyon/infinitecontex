"""Read-only health and integrity diagnostics; repair is an explicit operation."""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import orjson

from infinitecontex.core.models import Snapshot
from infinitecontex.storage.layout import build_layout
from infinitecontex.storage.snapshots import validate_snapshot_id


def run_doctor(project_root: Path) -> dict[str, str]:
    checks = {"git": "ok" if shutil.which("git") else "missing"}
    try:
        layout = build_layout(project_root)
    except ValueError as exc:
        return {**checks, "layout": f"unsafe: {exc}"}
    checks["layout"] = "ok" if layout.root.exists() else "missing"
    checks["manifest"] = "ok" if (layout.metadata / "manifest.json").exists() else "missing"
    checks["graph"] = "ok" if (layout.graph / "context_graph.json").exists() else "missing"
    checks["retrieval"] = "ok" if layout.retrieval.exists() else "missing"
    db_path = layout.metadata / "state.db"
    if not db_path.exists():
        return {**checks, "sqlite": "missing"}
    try:
        conn = sqlite3.connect(f"{db_path.as_uri()}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        return {**checks, "sqlite": f"error: {exc}"}
    try:
        checks["sqlite"] = str(conn.execute("PRAGMA integrity_check").fetchone()[0])
        version = int(conn.execute("PRAGMA user_version").fetchone()[0])
        checks["schema"] = "ok" if version == 2 else f"version {version}; run repair to migrate"
        invalid = 0
        missing = 0
        for snapshot_id, payload in conn.execute("SELECT id, payload_json FROM snapshots"):
            try:
                snapshot = Snapshot.model_validate_json(payload)
                if snapshot.id != snapshot_id:
                    invalid += 1
                validate_snapshot_id(snapshot.id)
                path = layout.snapshots / f"{snapshot.id}.json"
                if not path.is_file() or path.read_bytes() != orjson.dumps(
                    snapshot.model_dump(mode="json"),
                    option=orjson.OPT_INDENT_2,
                ):
                    missing += 1
                if not (layout.prompts / f"{snapshot.id}.prompt.md").is_file():
                    missing += 1
            except (ValueError, OSError):
                invalid += 1
        checks["snapshots"] = "ok" if not invalid else f"error: {invalid} invalid records"
        checks["artifacts"] = "ok" if not missing else f"repair needed: {missing} missing or divergent files"
        if version == 2:
            pending = conn.execute("SELECT count(*) FROM artifact_jobs").fetchone()[0]
            pending += conn.execute("SELECT count(*) FROM repository_state WHERE key='derived_dirty'").fetchone()[0]
            checks["recovery"] = "ok" if not pending else f"repair needed: {pending} pending operations"
            stale = conn.execute(
                "SELECT count(*) FROM search_docs WHERE source='snapshot' AND key NOT IN (SELECT id FROM snapshots)"
            ).fetchone()[0]
            checks["search"] = "ok" if not stale else f"repair needed: {stale} orphan search documents"
    except (sqlite3.Error, ValueError) as exc:
        checks["sqlite"] = f"error: {exc}"
    finally:
        conn.close()
    return checks
