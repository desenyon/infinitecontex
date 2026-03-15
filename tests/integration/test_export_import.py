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
