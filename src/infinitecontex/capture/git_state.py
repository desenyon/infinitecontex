"""Git-aware project state collection."""

from __future__ import annotations

import subprocess
from pathlib import Path


def _run_git(project_root: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.rstrip()


def current_branch(project_root: Path) -> str:
    return _run_git(project_root, ["branch", "--show-current"]) or "detached"


def recent_diff_summary(project_root: Path, limit: int = 20) -> list[str]:
    output = _run_git(project_root, ["diff", "--name-status"])
    if not output:
        return []
    return output.splitlines()[:limit]


def recent_commits(project_root: Path, limit: int = 10) -> list[str]:
    out = _run_git(project_root, ["log", f"--max-count={limit}", "--pretty=%h %s"])
    if not out:
        return []
    return out.splitlines()


def git_status_files(project_root: Path, limit: int = 50) -> list[str]:
    out = _run_git(project_root, ["status", "--short"])
    if not out:
        return []
    files: list[str] = []
    for line in out.splitlines():
        if len(line) < 4:
            continue
        path_part = line[3:].strip()
        if " -> " in path_part:
            path_part = path_part.split(" -> ", 1)[1].strip()
        files.append(path_part)
    return files[:limit]
