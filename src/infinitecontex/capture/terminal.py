"""Terminal command/error capture helpers."""

from __future__ import annotations

from pathlib import Path


def summarize_terminal_log(path: Path, max_lines: int = 400) -> dict[str, list[str]]:
    if not path.exists():
        return {"successful": [], "failed": [], "stack_traces": [], "failing_tests": []}

    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()[-max_lines:]
    successful: list[str] = []
    failed: list[str] = []
    stack_traces: list[str] = []
    failing_tests: list[str] = []

    for line in lines:
        low = line.lower()
        if "exit 0" in low or "success" in low:
            successful.append(line.strip())
        if "error" in low or "failed" in low or "exit 1" in low:
            failed.append(line.strip())
        if "traceback" in low or low.startswith("  file "):
            stack_traces.append(line.strip())
        if "::" in line and "failed" in low:
            failing_tests.append(line.strip())

    return {
        "successful": successful[-30:],
        "failed": failed[-30:],
        "stack_traces": stack_traces[-20:],
        "failing_tests": failing_tests[-20:],
    }
