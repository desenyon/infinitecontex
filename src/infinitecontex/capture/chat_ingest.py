"""Ingest and distill chat logs into intent signals."""

from __future__ import annotations

from pathlib import Path


def ingest_chat_text(path: Path) -> dict[str, list[str] | str]:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]

    decisions = [ln for ln in lines if ln.lower().startswith("decision:")][:20]
    assumptions = [ln for ln in lines if ln.lower().startswith("assumption:")][:20]
    tasks = [ln for ln in lines if ln.lower().startswith(("todo:", "task:"))][:30]
    issues = [ln for ln in lines if "error" in ln.lower() or "failed" in ln.lower()][:20]
    goal = next((ln.split(":", 1)[1].strip() for ln in lines if ln.lower().startswith("goal:")), "")

    return {
        "developer_goal": goal,
        "decisions": decisions,
        "assumptions": assumptions,
        "active_tasks": tasks,
        "unresolved_issues": issues,
    }
