"""Transactional snapshot repository with a durable derived-artifact work queue."""

from __future__ import annotations

import re
from collections.abc import Callable

from infinitecontex.core.models import PromptMode, Snapshot
from infinitecontex.core.serde import dump_json, load_json, write_text
from infinitecontex.storage.db import Database
from infinitecontex.storage.layout import InfctxLayout


def validate_snapshot_id(snapshot_id: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", snapshot_id):
        raise ValueError(f"invalid snapshot id: {snapshot_id}")
    return snapshot_id


class SnapshotRepository:
    """SQLite commits are authoritative; files can always be regenerated."""

    def __init__(self, db: Database, layout: InfctxLayout) -> None:
        self.db = db
        self.layout = layout

    def initialize(self, render: Callable[[Snapshot], str]) -> None:
        version = int(self.db.query("PRAGMA user_version")[0][0]) if self.db.db_path.exists() else 0
        if version > 2:
            raise ValueError(f"unsupported storage version {version}; upgrade infinitecontex")
        self.db.migrate()
        if version == 2:
            self._update_manifest()
            return
        # Older versions treated JSON as canonical. Adopt JSON-only records once,
        # but prefer a committed database row when both representations exist.
        legacy: list[Snapshot] = []
        for path in sorted(self.layout.snapshots.glob("*.json")):
            snapshot_id = validate_snapshot_id(path.stem)
            if not self.db.query("SELECT 1 FROM snapshots WHERE id = ?", (snapshot_id,)):
                snapshot = Snapshot.model_validate_json(path.read_bytes())
                if snapshot.id != snapshot_id:
                    raise ValueError(f"snapshot id does not match filename: {path.name}")
                legacy.append(snapshot)
        with self.db.transaction() as conn:
            for snapshot in legacy:
                conn.execute(
                    "INSERT INTO snapshots VALUES (?, ?, ?)",
                    (
                        snapshot.id,
                        snapshot.created_at.isoformat(),
                        snapshot.model_dump_json(),
                    ),
                )
            conn.execute("DELETE FROM search_docs WHERE source = 'snapshot'")
            for row in conn.execute("SELECT id, payload_json FROM snapshots").fetchall():
                snapshot = Snapshot.model_validate_json(row["payload_json"])
                validate_snapshot_id(snapshot.id)
                if snapshot.id != row["id"]:
                    raise ValueError("database snapshot id does not match payload")
                conn.execute("INSERT INTO search_docs VALUES ('snapshot', ?, ?)", (snapshot.id, render(snapshot)))
                conn.execute("INSERT OR REPLACE INTO artifact_jobs VALUES (?, 'write')", (snapshot.id,))
            # Remove stale search rows left by older cleanup implementations.
            conn.execute("INSERT OR REPLACE INTO repository_state VALUES ('derived_dirty', '1')")
            conn.execute("PRAGMA user_version = 2")

        self._update_manifest()

    def _update_manifest(self) -> None:
        path = self.layout.metadata / "manifest.json"
        if path.exists():
            manifest = load_json(path)
            if int(manifest.get("schema_version", 1)) > 2:
                raise ValueError("unsupported storage manifest version; upgrade infinitecontex")
            if manifest.get("schema_version") != 2:
                manifest["schema_version"] = 2
                dump_json(path, manifest)

    def save(self, snapshot: Snapshot, prompt: str) -> None:
        validate_snapshot_id(snapshot.id)
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT INTO snapshots VALUES (?, ?, ?)",
                (
                    snapshot.id,
                    snapshot.created_at.isoformat(),
                    snapshot.model_dump_json(),
                ),
            )
            conn.execute("INSERT INTO search_docs VALUES ('snapshot', ?, ?)", (snapshot.id, prompt))
            conn.execute("INSERT OR REPLACE INTO artifact_jobs VALUES (?, 'write')", (snapshot.id,))
            conn.execute("INSERT OR REPLACE INTO repository_state VALUES ('derived_dirty', '1')")

    def load(self, snapshot_id: str) -> Snapshot:
        validate_snapshot_id(snapshot_id)
        if not self.db.db_path.exists():
            raise ValueError(f"snapshot not found: {snapshot_id}")
        rows = self.db.query("SELECT payload_json FROM snapshots WHERE id = ?", (snapshot_id,))
        if not rows:
            raise ValueError(f"snapshot not found: {snapshot_id}")
        snapshot = Snapshot.model_validate_json(rows[0]["payload_json"])
        if snapshot.id != snapshot_id:
            raise ValueError("database snapshot id does not match payload")
        return snapshot

    def ids(self, limit: int | None = None) -> list[str]:
        if limit is not None and limit < 0:
            raise ValueError("limit must be nonnegative")
        if not self.db.db_path.exists():
            return []
        sql = "SELECT id FROM snapshots ORDER BY created_at DESC, id DESC"
        rows = self.db.query(sql if limit is None else sql + " LIMIT ?", () if limit is None else (limit,))
        return [validate_snapshot_id(str(row["id"])) for row in rows]

    def prune(self, keep: int) -> list[str]:
        if keep < 0:
            raise ValueError("keep must be nonnegative")
        deleted = self.ids()[keep:]
        with self.db.transaction() as conn:
            for snapshot_id in deleted:
                conn.execute("DELETE FROM snapshots WHERE id = ?", (snapshot_id,))
                conn.execute("DELETE FROM search_docs WHERE source = 'snapshot' AND key = ?", (snapshot_id,))
                conn.execute("INSERT OR REPLACE INTO artifact_jobs VALUES (?, 'delete')", (snapshot_id,))
            conn.execute("INSERT OR REPLACE INTO repository_state VALUES ('derived_dirty', '1')")
        return deleted

    def schedule_rebuild(self, render: Callable[[Snapshot], str]) -> None:
        known = set(self.ids())
        orphaned = {validate_snapshot_id(p.stem) for p in self.layout.snapshots.glob("*.json")} - known
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM search_docs WHERE source = 'snapshot'")
            for snapshot_id in known:
                row = conn.execute("SELECT payload_json FROM snapshots WHERE id = ?", (snapshot_id,)).fetchone()
                snapshot = Snapshot.model_validate_json(row[0])
                conn.execute("INSERT INTO search_docs VALUES ('snapshot', ?, ?)", (snapshot_id, render(snapshot)))
            for snapshot_id in orphaned:
                conn.execute("INSERT OR REPLACE INTO artifact_jobs VALUES (?, 'delete')", (snapshot_id,))
            conn.execute("INSERT OR REPLACE INTO artifact_jobs SELECT id, 'write' FROM snapshots")
            conn.execute("INSERT OR REPLACE INTO repository_state VALUES ('derived_dirty', '1')")

    def repair(self, render: Callable[[Snapshot], str], publish_latest: Callable[[Snapshot, str], None]) -> int:
        jobs = self.db.query("SELECT snapshot_id, action FROM artifact_jobs")
        for job in jobs:
            snapshot_id = validate_snapshot_id(str(job["snapshot_id"]))
            if job["action"] == "delete":
                (self.layout.snapshots / f"{snapshot_id}.json").unlink(missing_ok=True)
                for path in self.layout.prompts.glob(f"{snapshot_id}*.md"):
                    # IDs may share prefixes. Only remove the canonical or known mode names.
                    allowed = {f"{snapshot_id}.prompt.md", *(f"{snapshot_id}-{m.value}.md" for m in PromptMode)}
                    if path.name in allowed:
                        path.unlink()
                (self.layout.summaries / f"restore-{snapshot_id}.json").unlink(missing_ok=True)
            else:
                snapshot = self.load(snapshot_id)
                prompt = render(snapshot)
                dump_json(self.layout.snapshots / f"{snapshot_id}.json", snapshot.model_dump(mode="json"))
                write_text(self.layout.prompts / f"{snapshot_id}.prompt.md", prompt)
                with self.db.transaction() as conn:
                    conn.execute("DELETE FROM search_docs WHERE source = 'snapshot' AND key = ?", (snapshot_id,))
                    conn.execute("INSERT INTO search_docs VALUES ('snapshot', ?, ?)", (snapshot_id, prompt))
            self.db.execute("DELETE FROM artifact_jobs WHERE snapshot_id = ?", (snapshot_id,))
        dirty = self.db.query("SELECT 1 FROM repository_state WHERE key = 'derived_dirty'")
        if dirty:
            ids = self.ids(limit=1)
            if ids:
                snapshot = self.load(ids[0])
                publish_latest(snapshot, render(snapshot))
            else:
                for name in ("overview", "architecture", "decisions", "behavioral", "recent_changes", "instructions"):
                    (self.layout.agents / f"{name}.md").unlink(missing_ok=True)
                for name in ("inside.infinite_context.json", "inside.infinite_context.md"):
                    (self.layout.project / name).unlink(missing_ok=True)
                (self.layout.graph / "context_graph.json").unlink(missing_ok=True)
            self.db.execute("DELETE FROM repository_state WHERE key = 'derived_dirty'")
        return len(jobs)
