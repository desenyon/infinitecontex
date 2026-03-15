from __future__ import annotations

from infinitecontex.storage.db import Database
from infinitecontex.storage.layout import initialize_layout


def test_initialize_layout_creates_manifest(tmp_repo) -> None:
    layout = initialize_layout(tmp_repo)
    assert (layout.metadata / "manifest.json").exists()


def test_db_migration_creates_tables(tmp_repo) -> None:
    layout = initialize_layout(tmp_repo)
    db = Database(layout.metadata / "state.db")
    db.migrate()
    rows = db.query("SELECT name FROM sqlite_master WHERE type='table'")
    names = {str(r["name"]) for r in rows}
    assert "snapshots" in names
    assert "decisions" in names
    assert "events" in names
