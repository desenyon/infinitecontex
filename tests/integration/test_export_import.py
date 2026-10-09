from __future__ import annotations

from pathlib import Path

from infinitecontex.service import InfiniteContextService


def test_export_import_roundtrip(tmp_repo: Path, tmp_path: Path) -> None:
    svc = InfiniteContextService(tmp_repo)
    svc.init()
    svc.snapshot(goal="archive")

    archive = tmp_path / "ctx.tgz"
    out = svc.export(archive)
    assert out.exists()

    repo2 = tmp_path / "repo2"
    repo2.mkdir()
    svc2 = InfiniteContextService(repo2)
    svc2.import_archive(archive)
    assert (repo2 / ".infctx").exists()


def test_imported_database_replaces_destination_history_including_legacy(
    tmp_repo: Path,
    tmp_path: Path,
) -> None:
    from infinitecontex.storage.export_import import export_state

    source = InfiniteContextService(tmp_repo)
    incoming = source.snapshot(goal="incomingmarker")
    source.db.execute("PRAGMA user_version = 0")
    archive = export_state(tmp_repo, tmp_path / "legacy.tgz")
    destination = InfiniteContextService(tmp_path / "destination")
    old = destination.snapshot(goal="previousmarker")
    destination.import_archive(archive)
    assert [snapshot.id for snapshot in destination.snapshots_recent()] == [incoming.id]
    assert destination.search("previousmarker") == []
    assert not (destination.layout.snapshots / f"{old.id}.json").exists()
    assert not (destination.layout.prompts / f"{old.id}.prompt.md").exists()
