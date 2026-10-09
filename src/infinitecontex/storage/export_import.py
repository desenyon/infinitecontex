"""Bounded, staged archives containing only regular files beneath `.infctx`."""

from __future__ import annotations

import os
import shutil
import sqlite3
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

from infinitecontex.core.config import AppConfig
from infinitecontex.core.models import PromptMode
from infinitecontex.distill.summarizer import compile_packet
from infinitecontex.prompt.compiler import PromptCompiler
from infinitecontex.storage.db import Database
from infinitecontex.storage.layout import initialize_layout
from infinitecontex.storage.locking import project_lock
from infinitecontex.storage.paths import checked_path, relative_path, validate_state_tree
from infinitecontex.storage.snapshots import SnapshotRepository, validate_snapshot_id

MAX_MEMBERS = 20_000
MAX_FILE_BYTES = 256 * 1024 * 1024
MAX_TOTAL_BYTES = 1024 * 1024 * 1024


def _copy_state(source: Path, target: Path, *, include_exports: bool = True) -> None:
    """Copy state under the writer lock, using SQLite backup to include committed WAL data."""
    if not source.exists():
        target.mkdir(mode=0o700)
        return

    def ignored(directory: str, names: list[str]) -> set[str]:
        if Path(directory) == source / "metadata":
            return set(names) & {"state.db", "state.db-wal", "state.db-shm"}
        if Path(directory) == source and not include_exports:
            return {"exports"}
        return set()

    shutil.copytree(source, target, ignore=ignored)
    db_path = source / "metadata" / "state.db"
    if db_path.exists():
        destination = target / "metadata" / "state.db"
        destination.parent.mkdir(parents=True, exist_ok=True)
        src = sqlite3.connect(f"{db_path.as_uri()}?mode=ro", uri=True)
        dst = sqlite3.connect(destination)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()


def export_state(project_root: Path, output_path: Path) -> Path:
    project_root = project_root.resolve()
    output_path = output_path.absolute()
    with project_lock(project_root):
        validate_state_tree(project_root)
        state_dir = project_root / ".infctx"
        if not state_dir.is_dir():
            raise ValueError("no .infctx state to export")
        if output_path.is_symlink():
            raise ValueError("export destination must not be a symlink")
        resolved_output = output_path.resolve()
        if resolved_output.is_relative_to(state_dir) and not resolved_output.is_relative_to(state_dir / "exports"):
            raise ValueError("exports inside .infctx must use its exports directory")
        if resolved_output == project_root / ".infctx.lock":
            raise ValueError("export destination is the repository lock")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="infctx-export-") as temporary:
            staged = Path(temporary) / ".infctx"
            _copy_state(state_dir, staged, include_exports=False)
            # Archives are never included in archives, including the current destination.
            (staged / "exports").mkdir()
            fd, name = tempfile.mkstemp(prefix=".infctx-export-", dir=output_path.parent)
            os.close(fd)
            try:
                with tarfile.open(name, "w:gz") as tar:
                    tar.add(staged, arcname=".infctx")
                os.replace(name, output_path)
            finally:
                Path(name).unlink(missing_ok=True)
    return output_path


def _validate_members(tar: tarfile.TarFile) -> list[tuple[tarfile.TarInfo, PurePosixPath]]:
    members: list[tuple[tarfile.TarInfo, PurePosixPath]] = []
    seen: dict[str, bool] = {}
    total = 0
    for member in tar:
        name = member.name
        if name.startswith("./"):
            name = name[2:]
        name = name.rstrip("/") if member.isdir() else name
        path = relative_path(name)
        if path.parts[0] != ".infctx" or (len(path.parts) == 1 and not member.isdir()):
            raise ValueError(f"archive entry must be beneath .infctx: {member.name}")
        if not (member.isfile() or member.isdir()) or member.issparse():
            raise ValueError(f"archive contains unsupported entry: {member.name}")
        normalized = name.casefold()
        if normalized in seen:
            raise ValueError(f"archive contains duplicate entry: {member.name}")
        if member.size < 0 or member.size > MAX_FILE_BYTES:
            raise ValueError(f"archive entry exceeds size limit: {member.name}")
        total += member.size
        if total > MAX_TOTAL_BYTES or len(members) >= MAX_MEMBERS:
            raise ValueError("archive exceeds total size or entry limit")
        seen[normalized] = member.isdir()
        members.append((member, path))
    if not members:
        raise ValueError("archive contains no .infctx state")
    for _, path in members:
        if any(seen.get(str(parent).casefold()) is False for parent in path.parents):
            raise ValueError(f"archive contains file/directory collision: {path}")
    return members


def import_state(project_root: Path, archive_path: Path) -> None:
    project_root = project_root.resolve()
    with project_lock(project_root):
        validate_state_tree(project_root)
        state_dir = project_root / ".infctx"
        with tarfile.open(archive_path, "r:gz") as tar:
            members = _validate_members(tar)
            # Stage on the same filesystem so publication uses directory renames.
            with tempfile.TemporaryDirectory(prefix=".infctx-import-", dir=project_root) as temporary:
                staged = Path(temporary) / ".infctx"
                _copy_state(state_dir, staged)
                if any(str(rel) == ".infctx/metadata/state.db" for _, rel in members):
                    # An imported database replaces history. Do not adopt destination
                    # JSON as legacy or retain its prompts when migrating that database.
                    for directory, pattern in (
                        ("snapshots", "*.json"),
                        ("prompts", "*.md"),
                        ("summaries", "restore-*.json"),
                    ):
                        for path in (staged / directory).glob(pattern):
                            if path.is_file():
                                path.unlink()
                for member, rel in members:
                    destination = Path(temporary).joinpath(*rel.parts)
                    if member.isdir():
                        destination.mkdir(parents=True, exist_ok=True)
                    else:
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        stream = tar.extractfile(member)
                        if stream is None:
                            raise ValueError(f"archive entry is unreadable: {member.name}")
                        with stream, destination.open("wb") as output:
                            shutil.copyfileobj(stream, output, length=1024 * 1024)
                db_path = staged / "metadata" / "state.db"
                if db_path.exists():
                    conn = sqlite3.connect(db_path)
                    try:
                        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                            raise ValueError("archive contains a corrupt SQLite database")
                        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                    finally:
                        conn.close()
                config = staged / "config.json"
                if config.exists():
                    AppConfig.model_validate_json(config.read_bytes())
                # Validate and migrate the staged repository before touching live state.
                layout = initialize_layout(Path(temporary))
                repository = SnapshotRepository(Database(layout.metadata / "state.db"), layout)
                repository.initialize(
                    lambda snapshot: PromptCompiler().compile(
                        compile_packet(snapshot, budget=int(snapshot.metrics.get("token_budget", 1200))),
                        PromptMode.GENERIC_AGENT_RESTORE,
                    )
                )
                for snapshot_id in repository.ids():
                    snapshot = repository.load(snapshot_id)
                    # Rendering metadata is validated before publication as well.
                    int(snapshot.metrics.get("token_budget", 1200))
                for job in repository.db.query("SELECT snapshot_id, action FROM artifact_jobs"):
                    validate_snapshot_id(str(job["snapshot_id"]))
                    if job["action"] not in {"write", "delete"}:
                        raise ValueError("archive contains an invalid recovery job")
                    if job["action"] == "write":
                        repository.load(str(job["snapshot_id"]))
                backup = checked_path(project_root, project_root / ".infctx-import-backup")
                if backup.exists():
                    # A previous publication succeeded but backup removal was interrupted.
                    shutil.rmtree(backup)
                if state_dir.exists():
                    state_dir.rename(backup)
                try:
                    staged.rename(state_dir)
                except BaseException:
                    if backup.exists():
                        backup.rename(state_dir)
                    raise
                if backup.exists():
                    shutil.rmtree(backup)
