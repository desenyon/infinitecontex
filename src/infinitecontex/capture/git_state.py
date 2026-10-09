"""Git-aware state collection with NUL-delimited paths and index awareness."""

from __future__ import annotations

import subprocess
from pathlib import Path


def _run_git(project_root: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=project_root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout if result.returncode == 0 else ""


def current_branch(project_root: Path) -> str:
    return _run_git(project_root, ["branch", "--show-current"]).strip() or "detached"


def _status(project_root: Path) -> list[tuple[str, str, str]]:
    fields = iter(_run_git(project_root, ["status", "--porcelain=v1", "-z", "--untracked-files=all"]).split("\0"))
    records = []
    for field in fields:
        if len(field) < 4:
            continue
        status, path = field[:2], field[3:]
        original = next(fields, "") if "R" in status or "C" in status else ""
        if path.split("/", 1)[0].startswith(".infctx") or path.split("/", 1)[0] == ".git":
            continue
        records.append((status, path, original))
    return records


def recent_diff_summary(project_root: Path, limit: int = 20) -> list[str]:
    # Preserve the historical `M\tpath` output for unstaged-only changes.
    lines = []
    for status, path, original in _status(project_root):
        label = status.strip()
        if status[0] not in {" ", "?"}:
            label += " (staged)" if status[1] == " " else " (staged + unstaged)"
        name = f"{original} -> {path}" if original else path
        lines.append(f"{label}\t{name}")
    return lines[: max(0, limit)]


def recent_commits(project_root: Path, limit: int = 10) -> list[str]:
    return _run_git(project_root, ["log", f"--max-count={max(0, limit)}", "--pretty=%h %s"]).splitlines()


def git_status_files(project_root: Path, limit: int = 50) -> list[str]:
    return [path for _, path, _ in _status(project_root)][: max(0, limit)]
