"""Portable export/import for `.infctx` state."""

from __future__ import annotations

import tarfile
from pathlib import Path


def export_state(project_root: Path, output_path: Path) -> Path:
    state_dir = project_root / ".infctx"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output_path, "w:gz") as tar:
        tar.add(state_dir, arcname=".infctx")
    return output_path


def import_state(project_root: Path, archive_path: Path) -> None:
    with tarfile.open(archive_path, "r:gz") as tar:
        base = project_root.resolve()
        for member in tar.getmembers():
            member_path = (project_root / member.name).resolve()
            if not str(member_path).startswith(str(base)):
                raise ValueError(f"archive contains unsafe path: {member.name}")
        tar.extractall(project_root, filter="data")
