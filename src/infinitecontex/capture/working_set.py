"""Working-set extraction from git and local state."""

from __future__ import annotations

from pathlib import Path

from infinitecontex.capture.git_state import current_branch, git_status_files, recent_diff_summary
from infinitecontex.core.models import WorkingSetContext


def build_working_set(
    project_root: Path,
    pins: list[str],
    last_successful_commands: list[str] | None = None,
    last_failed_commands: list[str] | None = None,
    stack_traces: list[str] | None = None,
    failing_tests: list[str] | None = None,
) -> WorkingSetContext:
    active_files = git_status_files(project_root)
    diffs = recent_diff_summary(project_root)

    next_action = "review failing tests" if failing_tests else "continue active branch changes"

    return WorkingSetContext(
        branch=current_branch(project_root),
        recent_diffs=diffs,
        active_files=active_files,
        last_successful_commands=last_successful_commands or [],
        last_failed_commands=last_failed_commands or [],
        stack_traces=stack_traces or [],
        failing_tests=failing_tests or [],
        next_likely_action=next_action,
        pins=pins,
    )
