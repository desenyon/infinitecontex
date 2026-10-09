"""Containment checks shared by capture, restore, and local storage."""

from __future__ import annotations

import stat
from pathlib import Path, PurePosixPath


def relative_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or ":" in value
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise ValueError(f"unsafe relative path: {value}")
    return path


def checked_path(root: Path, path: Path) -> Path:
    """Reject symlink components and paths outside root, including dangling links."""
    root = root.resolve()
    path = path.absolute()
    try:
        rel = path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path outside project: {path}") from exc
    current = root
    for part in rel.parts:
        if part in {".", ".."}:
            raise ValueError(f"unsafe path: {path}")
        current /= part
        if current.is_symlink():
            raise ValueError(f"symlinks are unsupported: {current}")
        if current.exists():
            info = current.stat()
            if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
                raise ValueError(f"special files are unsupported: {current}")
            if stat.S_ISREG(info.st_mode) and info.st_nlink > 1:
                raise ValueError(f"hard links are unsupported: {current}")
    return path


def project_file(root: Path, value: str) -> Path:
    rel = relative_path(value)
    if any(part in {".git", ".infctx", ".infctx.lock", ".infctx-import-backup"} for part in rel.parts):
        raise ValueError(f"internal state is not a project file: {value}")
    return checked_path(root, root.resolve().joinpath(*rel.parts))


def validate_state_tree(root: Path) -> None:
    state = checked_path(root, root.resolve() / ".infctx")
    if state.exists():
        for path in state.rglob("*"):
            checked_path(root, path)
