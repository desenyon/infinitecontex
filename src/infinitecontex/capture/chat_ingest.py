"""Ingest and distill chat logs into intent signals."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import orjson

EXPLICIT_PREFIXES = {
    "developer_goal": ("goal:",),
    "decisions": ("decision:",),
    "assumptions": ("assumption:",),
    "active_tasks": ("todo:", "task:"),
}
GOAL_HINTS = ("we need to", "need to", "want to", "working on", "goal is to", "trying to", "plan to")
DECISION_HINTS = ("let's", "we should", "decided to", "we'll", "should keep", "should use")
ISSUE_HINTS = ("error", "failed", "broken", "doesn't work", "does not work", "empty", "confusing", "issue")
TASK_HINTS = ("add ", "fix ", "update ", "implement ", "bump ", "replace ", "overhaul ")
JSON_CHAT_KEYS = {"text", "content", "message", "prompt", "response", "body", "question", "answer"}


def _clean_line(line: str) -> str:
    return re.sub(r"^(user|assistant|system|human|ai)\s*:\s*", "", line.strip(), flags=re.IGNORECASE)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _collect_json_strings(node: Any, parent_key: str = "") -> list[str]:
    if isinstance(node, dict):
        strings: list[str] = []
        for key, value in node.items():
            strings.extend(_collect_json_strings(value, key.lower()))
        return strings
    if isinstance(node, list):
        items: list[str] = []
        for value in node:
            items.extend(_collect_json_strings(value, parent_key))
        return items
    if isinstance(node, str):
        stripped = node.strip()
        if not stripped:
            return []
        if parent_key in JSON_CHAT_KEYS or ("\n" in stripped) or len(stripped.split()) >= 4:
            return [stripped]
    return []


def extract_chat_text(path: Path) -> str:
    if path.suffix == ".json":
        payload = orjson.loads(path.read_bytes())
        return "\n".join(_collect_json_strings(payload))
    if path.suffix == ".jsonl":
        collected: list[str] = []
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = orjson.loads(stripped)
            except orjson.JSONDecodeError:
                collected.append(stripped)
                continue
            collected.extend(_collect_json_strings(payload))
        return "\n".join(collected)
    return path.read_text(encoding="utf-8", errors="ignore")


def ingest_chat_text(path: Path) -> dict[str, Any]:
    raw = extract_chat_text(path)
    lines = [_clean_line(line) for line in raw.splitlines() if line.strip()]

    goal = ""
    decisions: list[str] = []
    assumptions: list[str] = []
    tasks: list[str] = []
    issues: list[str] = []
    open_questions: list[str] = []
    signal_sources: dict[str, list[str]] = {
        "developer_goal": [],
        "decisions": [],
        "assumptions": [],
        "active_tasks": [],
        "unresolved_issues": [],
        "open_questions": [],
    }

    for line in lines:
        low = line.lower()

        matched_explicit = False
        for key, prefixes in EXPLICIT_PREFIXES.items():
            prefix = next((item for item in prefixes if low.startswith(item)), None)
            if prefix is None:
                continue
            content = line[len(prefix) :].strip()
            matched_explicit = True
            if key == "developer_goal" and content:
                if not goal:
                    goal = content
                signal_sources["developer_goal"].append(content)
            elif key == "decisions" and content:
                decisions.append(content)
                signal_sources["decisions"].append(content)
            elif key == "assumptions" and content:
                assumptions.append(content)
                signal_sources["assumptions"].append(content)
            elif key == "active_tasks" and content:
                tasks.append(content)
                signal_sources["active_tasks"].append(content)
            break

        if matched_explicit:
            continue

        if line.endswith("?"):
            open_questions.append(line)
            signal_sources["open_questions"].append(line)

        if any(hint in low for hint in ISSUE_HINTS):
            issues.append(line)
            signal_sources["unresolved_issues"].append(line)

        if any(hint in low for hint in GOAL_HINTS):
            if not goal:
                goal = line
            signal_sources["developer_goal"].append(line)

        if any(hint in low for hint in DECISION_HINTS):
            decisions.append(line)
            signal_sources["decisions"].append(line)

        if any(hint in low for hint in TASK_HINTS) or "we need to" in low:
            tasks.append(line)
            signal_sources["active_tasks"].append(line)

    return {
        "developer_goal": goal,
        "decisions": _dedupe(decisions)[:20],
        "assumptions": _dedupe(assumptions)[:20],
        "active_tasks": _dedupe(tasks)[:30],
        "unresolved_issues": _dedupe(issues)[:20],
        "open_questions": _dedupe(open_questions)[:20],
        "signal_sources": {key: _dedupe(values)[:20] for key, values in signal_sources.items() if values},
    }
