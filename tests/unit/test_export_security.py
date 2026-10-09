from __future__ import annotations

import io
import tarfile
from pathlib import Path

import pytest

from infinitecontex.storage.export_import import import_state


def test_import_rejects_path_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "bad.tgz"
    payload = b"x"

    with tarfile.open(archive, "w:gz") as tar:
        info = tarfile.TarInfo(name="../evil.txt")
        info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))

    with pytest.raises(ValueError):
        import_state(tmp_path, archive)


def test_import_rejects_prefix_escape_path(tmp_path: Path) -> None:
    archive = tmp_path / "prefix-escape.tgz"
    payload = b"x"
    escape_root = Path("..") / f"{tmp_path.name}-escape"

    with tarfile.open(archive, "w:gz") as tar:
        info = tarfile.TarInfo(name=str(escape_root / "evil.txt"))
        info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))

    with pytest.raises(ValueError):
        import_state(tmp_path, archive)


def test_import_rejects_symlink_entries(tmp_path: Path) -> None:
    archive = tmp_path / "symlink.tgz"

    with tarfile.open(archive, "w:gz") as tar:
        info = tarfile.TarInfo(name=".infctx/link")
        info.type = tarfile.SYMTYPE
        info.linkname = "/tmp/target"
        tar.addfile(info)

    with pytest.raises(ValueError):
        import_state(tmp_path, archive)


def make_archive(path: Path, entries: list[tuple[str, bytes]]) -> None:
    with tarfile.open(path, "w:gz") as tar:
        for name, data in entries:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))


@pytest.mark.parametrize(
    "name",
    [
        ".git/config",
        "README.md",
        ".infctx/../.git/config",
        "/.infctx/file",
        ".infctx\\file",
        ".infctx/C:drive",
        ".infctx/./file",
        ".infctx//file",
    ],
)
def test_import_only_accepts_normalized_state_paths(tmp_path: Path, name: str) -> None:
    archive = tmp_path / "bad.tgz"
    make_archive(archive, [(".infctx/valid.txt", b"valid"), (name, b"unsafe")])
    with pytest.raises(ValueError):
        import_state(tmp_path, archive)
    assert not (tmp_path / ".infctx").exists()


@pytest.mark.parametrize("kind", [tarfile.LNKTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE, tarfile.BLKTYPE])
def test_import_rejects_special_entries(tmp_path: Path, kind: bytes) -> None:
    archive = tmp_path / "bad.tgz"
    with tarfile.open(archive, "w:gz") as tar:
        info = tarfile.TarInfo(".infctx/special")
        info.type = kind
        info.linkname = ".infctx/file"
        tar.addfile(info)
    with pytest.raises(ValueError, match="unsupported"):
        import_state(tmp_path, archive)


@pytest.mark.parametrize(
    "entries",
    [
        [(".infctx/file", b"first"), (".infctx/file", b"second")],
        [(".infctx/file", b"first"), (".infctx/file/child", b"second")],
    ],
)
def test_import_rejects_collisions(tmp_path: Path, entries: list[tuple[str, bytes]]) -> None:
    archive = tmp_path / "bad.tgz"
    make_archive(archive, entries)
    with pytest.raises(ValueError):
        import_state(tmp_path, archive)


def test_import_enforces_resource_limits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import infinitecontex.storage.export_import as module

    archive = tmp_path / "large.tgz"
    make_archive(archive, [(".infctx/file", b"long")])
    monkeypatch.setattr(module, "MAX_FILE_BYTES", 3)
    with pytest.raises(ValueError, match="size limit"):
        import_state(tmp_path, archive)
    assert not (tmp_path / ".infctx").exists()


def test_import_existing_symlink_cannot_escape(tmp_path: Path) -> None:
    external = tmp_path / "external"
    external.mkdir()
    state = tmp_path / ".infctx"
    state.mkdir()
    (state / "subdir").symlink_to(external, target_is_directory=True)
    archive = tmp_path / "bad.tgz"
    make_archive(archive, [(".infctx/subdir/file", b"unsafe")])
    with pytest.raises(ValueError, match="symlink"):
        import_state(tmp_path, archive)
    assert list(external.iterdir()) == []


def test_corrupt_database_import_preserves_existing_state(tmp_repo: Path, tmp_path: Path) -> None:
    from infinitecontex.service import InfiniteContextService

    svc = InfiniteContextService(tmp_repo)
    snap = svc.snapshot(goal="keepmarker")
    archive = tmp_path / "corrupt.tgz"
    make_archive(archive, [(".infctx/metadata/state.db", b"not sqlite")])
    with pytest.raises(Exception):
        svc.import_archive(archive)
    assert svc.snapshot_details(snap.id)["id"] == snap.id
    assert svc.search("keepmarker")


def test_invalid_config_import_preserves_existing_state(tmp_repo: Path, tmp_path: Path) -> None:
    from infinitecontex.service import InfiniteContextService

    svc = InfiniteContextService(tmp_repo)
    snap = svc.snapshot()
    archive = tmp_path / "invalid-config.tgz"
    make_archive(archive, [(".infctx/config.json", b'{"capture_max_files": -3}')])
    with pytest.raises(ValueError):
        svc.import_archive(archive)
    assert svc.snapshot_details(snap.id)["id"] == snap.id


def test_export_excludes_archives_and_includes_live_wal(tmp_repo: Path) -> None:
    from infinitecontex.service import InfiniteContextService

    svc = InfiniteContextService(tmp_repo)
    svc.init()
    connection = svc.db.connect()
    try:
        connection.execute("INSERT INTO pins VALUES (NULL, 'wal.py', 'committed', '2026-01-01')")
        connection.commit()
        archive = svc.layout.exports / "state.tgz"
        svc.export(archive)
        svc.export(archive)
        with tarfile.open(archive) as tar:
            names = tar.getnames()
        assert ".infctx/exports/state.tgz" not in names
        assert not any(name.endswith(("-wal", "-shm")) for name in names)
        target = tmp_repo.parent / "imported"
        imported = InfiniteContextService(target)
        imported.import_archive(archive)
        assert imported.list_pins() == ["wal.py"]
    finally:
        connection.close()


def test_export_rejects_linked_files(tmp_repo: Path, tmp_path: Path) -> None:
    from infinitecontex.service import InfiniteContextService

    svc = InfiniteContextService(tmp_repo)
    svc.init()
    external = tmp_path / "outside"
    external.write_text("outside-sentinel")
    (svc.layout.working_set / "linked").symlink_to(external)
    with pytest.raises(ValueError, match="symlink"):
        svc.export(tmp_path / "state.tgz")


def test_import_rename_failure_rolls_back(tmp_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from infinitecontex.service import InfiniteContextService

    svc = InfiniteContextService(tmp_repo)
    snap = svc.snapshot()
    archive = tmp_path / "valid.tgz"
    make_archive(archive, [(".infctx/new.txt", b"new")])
    original = Path.rename

    def fail_publish(self: Path, target: Path) -> Path:
        if self.name == ".infctx" and self.parent.name.startswith(".infctx-import-"):
            raise OSError("injected publish failure")
        return original(self, target)

    monkeypatch.setattr(Path, "rename", fail_publish)
    with pytest.raises(OSError, match="injected"):
        svc.import_archive(archive)
    assert svc.snapshot_details(snap.id)["id"] == snap.id
    assert not (svc.layout.root / "new.txt").exists()


def test_case_alias_duplicate_rejected_before_publication(tmp_path: Path) -> None:
    archive = tmp_path / "case.tgz"
    make_archive(archive, [(".infctx/File", b"first"), (".infctx/file", b"second")])
    with pytest.raises(ValueError, match="duplicate"):
        import_state(tmp_path, archive)


def test_invalid_recovery_job_import_preserves_destination(tmp_repo: Path, tmp_path: Path) -> None:
    from infinitecontex.service import InfiniteContextService
    from infinitecontex.storage.export_import import export_state

    destination = InfiniteContextService(tmp_repo)
    prior = destination.snapshot(goal="destinationmarker")
    source_root = tmp_path / "source"
    source = InfiniteContextService(source_root)
    source.snapshot(goal="sourcemarker")
    source.db.execute("INSERT INTO artifact_jobs VALUES ('../escape', 'delete')")
    archive = export_state(source_root, tmp_path / "bad-job.tgz")
    with pytest.raises(ValueError, match="invalid snapshot id"):
        destination.import_archive(archive)
    assert destination.snapshot_details()["id"] == prior.id
