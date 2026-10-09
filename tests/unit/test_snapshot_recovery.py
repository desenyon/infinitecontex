from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from infinitecontex.core.models import PromptMode
from infinitecontex.core.serde import atomic_write
from infinitecontex.service import InfiniteContextService
from infinitecontex.storage.db import Database
from infinitecontex.storage.layout import initialize_layout


def test_atomic_write_preserves_old_file_on_failure(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_bytes(b"old")
    with patch("infinitecontex.core.serde.os.replace", side_effect=OSError("injected replace failure")):
        with pytest.raises(OSError):
            atomic_write(path, b"new")
    assert path.read_bytes() == b"old"
    assert list(tmp_path.iterdir()) == [path]


def test_snapshot_and_search_commit_or_rollback_together(tmp_repo: Path) -> None:
    svc = InfiniteContextService(tmp_repo)
    svc.init()
    svc.db.execute(
        "CREATE TRIGGER fail_index BEFORE INSERT ON search_docs_content BEGIN SELECT RAISE(ABORT, 'injected'); END"
    )
    with pytest.raises(sqlite3.Error):
        svc.snapshot(goal="rollbackmarker")
    assert svc.snapshots_recent() == []
    assert svc.search("rollbackmarker") == []
    assert list(svc.layout.snapshots.glob("*.json")) == []
    assert svc.db.query("SELECT * FROM artifact_jobs") == []


def test_committed_snapshot_survives_artifact_failure_and_restarts(tmp_repo: Path) -> None:
    svc = InfiniteContextService(tmp_repo)
    svc.init()
    with patch("infinitecontex.storage.snapshots.dump_json", side_effect=OSError("injected full disk")):
        with pytest.warns(RuntimeWarning, match="repair"):
            snapshot = svc.snapshot(goal="durablemarker")
    assert svc.snapshot_details(snapshot.id)["id"] == snapshot.id
    assert len(svc.search("durablemarker")) == 1
    assert "repair needed" in svc.doctor()["recovery"]
    restarted = InfiniteContextService(tmp_repo)
    restarted.repair()
    assert (svc.layout.snapshots / f"{snapshot.id}.json").exists()
    assert snapshot.id in (svc.layout.agents / "overview.md").read_text()
    assert restarted.doctor()["recovery"] == "ok"
    assert restarted.doctor()["artifacts"] == "ok"


def test_corrupt_or_missing_cache_cannot_override_database(tmp_repo: Path) -> None:
    svc = InfiniteContextService(tmp_repo)
    snapshot = svc.snapshot(goal="canonicalmarker")
    path = svc.layout.snapshots / f"{snapshot.id}.json"
    path.write_text("broken")
    assert svc.snapshot_details(snapshot.id)["intent"]["developer_goal"] == "canonicalmarker"
    assert "repair needed" in svc.doctor()["artifacts"]
    svc.repair()
    path.unlink()
    assert svc.snapshot_details(snapshot.id)["id"] == snapshot.id
    svc.repair()
    assert path.exists()


def test_cleanup_removes_search_prompts_restore_and_latest_handoff(tmp_repo: Path) -> None:
    svc = InfiniteContextService(tmp_repo)
    old = svc.snapshot(goal="oldmarker")
    svc.prompt(PromptMode.HUMAN_HANDOFF, 700, old.id)
    svc.restore(old.id)
    latest = svc.snapshot(goal="newmarker")
    assert svc.cleanup(keep=1) == [old.id]
    assert svc.search("oldmarker") == []
    assert not list(svc.layout.prompts.glob(f"{old.id}*"))
    assert not (svc.layout.summaries / f"restore-{old.id}.json").exists()
    with pytest.raises(ValueError, match="not found"):
        svc.snapshot_details(old.id)
    assert latest.id in (svc.layout.agents / "overview.md").read_text()
    svc.cleanup(keep=0)
    assert svc.snapshots_recent() == []
    assert not list(svc.layout.agents.glob("*.md"))
    assert not (svc.layout.graph / "context_graph.json").exists()
    assert not list(svc.layout.project.glob("inside.infinite_context.*"))
    assert svc.search("newmarker") == []


def test_interrupted_cleanup_is_recoverable(tmp_repo: Path) -> None:
    svc = InfiniteContextService(tmp_repo)
    snapshot = svc.snapshot(goal="deletedmarker")
    svc.repository.prune(0)  # Simulate termination after the metadata commit.
    assert svc.search("deletedmarker") == []
    assert (svc.layout.snapshots / f"{snapshot.id}.json").exists()
    InfiniteContextService(tmp_repo).repair()
    assert not (svc.layout.snapshots / f"{snapshot.id}.json").exists()
    assert svc.db.query("SELECT * FROM artifact_jobs") == []


def test_v1_migration_recovers_json_only_and_preserves_notes(tmp_repo: Path) -> None:
    svc = InfiniteContextService(tmp_repo)
    snapshot = svc.snapshot(goal="legacymarker")
    svc.note("Keep SQLite", "local state", [], "", [])
    svc.db.execute("DELETE FROM snapshots")
    svc.db.execute("PRAGMA user_version = 0")
    svc.db.execute("INSERT INTO search_docs VALUES ('snapshot', 'gone', 'stale')")
    svc.repair()
    assert svc.snapshot_details(snapshot.id)["id"] == snapshot.id
    assert svc.decisions_recent()[0]["summary"] == "Keep SQLite"
    assert svc.search("stale") == []
    assert len(svc.search("legacymarker")) == 1
    assert svc.db.query("PRAGMA user_version")[0][0] == 2


def test_invalid_legacy_file_does_not_complete_migration(tmp_repo: Path) -> None:
    layout = initialize_layout(tmp_repo)
    db = Database(layout.metadata / "state.db")
    db.migrate()
    (layout.snapshots / "snap-legacy.json").write_text("bad")
    with pytest.raises(ValueError):
        InfiniteContextService(tmp_repo).repair()
    assert db.query("PRAGMA user_version")[0][0] == 0
    assert (layout.snapshots / "snap-legacy.json").read_text() == "bad"


@pytest.mark.parametrize("snapshot_id", ["../secrets", "/tmp/secrets", "snap/a", "snap\\a", "", ".."])
def test_rejects_unsafe_snapshot_ids(tmp_repo: Path, snapshot_id: str) -> None:
    svc = InfiniteContextService(tmp_repo)
    svc.init()
    with pytest.raises(ValueError, match="invalid snapshot id"):
        svc.snapshot_details(snapshot_id)


def test_doctor_does_not_initialize_empty_project(tmp_path: Path) -> None:
    svc = InfiniteContextService(tmp_path)
    assert svc.doctor()["sqlite"] == "missing"
    assert not (tmp_path / ".infctx").exists()


def test_negative_retention_is_rejected(tmp_repo: Path) -> None:
    svc = InfiniteContextService(tmp_repo)
    svc.snapshot()
    with pytest.raises(ValueError, match="nonnegative"):
        svc.cleanup(-1)
    assert len(svc.snapshots_recent()) == 1


def test_failed_repair_preserves_search_for_committed_snapshots(tmp_repo: Path) -> None:
    svc = InfiniteContextService(tmp_repo)
    svc.snapshot(goal="searchmarker")
    with patch("infinitecontex.storage.snapshots.dump_json", side_effect=OSError("injected full disk")):
        with pytest.raises(OSError):
            svc.repair()
    assert len(svc.search("searchmarker")) == 1


def test_import_crash_gap_restores_previous_tree(tmp_repo: Path) -> None:
    svc = InfiniteContextService(tmp_repo)
    snapshot = svc.snapshot(goal="recoveredmarker")
    svc.layout.root.rename(tmp_repo / ".infctx-import-backup")
    restarted = InfiniteContextService(tmp_repo)
    assert restarted.snapshot_details(snapshot.id)["id"] == snapshot.id
    assert svc.layout.root.exists()
    assert not (tmp_repo / ".infctx-import-backup").exists()
