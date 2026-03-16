"""Chat log auto-discovery for AI coding assistants."""

from pathlib import Path
from typing import Any

from infinitecontex.capture.chat_ingest import extract_chat_text, ingest_chat_text


def _find_recent_file(directory: Path, pattern: str) -> Path | None:
    if not directory.exists():
        return None
    files = list(directory.rglob(pattern))
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def discover_cursor_sessions() -> Path | None:
    """Find the most recently modified Cursor Workspace Storage db that looks like a session."""
    # Cursor stores active conversations in workspaceStorage SQLite databases.
    # For a robust, fast scan without sqlite3 dependency issues across environments,
    # we can just find any `.cursor/sessions/` if it exists locally as some versions do,
    # or fallback to globalStorage recent chats if possible.
    home = Path.home()

    # 1. Check local project .cursorrules/.cursor/sessions? (Sometimes used)
    local_cursor = Path(".cursor")
    if local_cursor.exists():
        recent = _find_recent_file(local_cursor, "*.json")
        if recent:
            return recent

    # 2. Heuristic check in global App Support
    import sys

    if sys.platform == "darwin":
        storage = home / "Library/Application Support/Cursor/User/workspaceStorage"
    elif sys.platform == "win32":
        storage = home / "AppData/Roaming/Cursor/User/workspaceStorage"
    else:
        storage = home / ".config/Cursor/User/workspaceStorage"

    if storage.exists():
        recent_db = _find_recent_file(storage, "state.vscdb")
        if recent_db:
            return recent_db

    return None


def discover_copilot_logs() -> Path | None:
    """Find Copilot chat logs in VS Code."""
    home = Path.home()
    import sys

    if sys.platform == "darwin":
        storage = home / "Library/Application Support/Code/User/globalStorage/github.copilot-chat"
    elif sys.platform == "win32":
        storage = home / "AppData/Roaming/Code/User/globalStorage/github.copilot-chat"
    else:
        storage = home / ".config/Code/User/globalStorage/github.copilot-chat"

    if storage.exists():
        candidates: list[Path] = []
        for pattern in ("*chat*.json", "*conversation*.json", "*session*.json", "*.jsonl", "*.txt"):
            recent = _find_recent_file(storage, pattern)
            if recent is not None:
                candidates.append(recent)
        if candidates:
            return max(candidates, key=lambda path: path.stat().st_mtime)
    return None


def discover_claude_logs() -> Path | None:
    """Find local CLAUDE.md or Claude logs."""
    local_claude = Path("CLAUDE.md")
    if local_claude.exists() and local_claude.is_file():
        return local_claude
    return None


def auto_ingest_chat() -> dict[str, Any]:
    """Discover recent AI chat logs and extract context from them."""
    checked_sources: list[dict[str, str | None]] = []
    candidates: list[tuple[str, Path]] = []

    for source_name, discover in (
        ("claude", discover_claude_logs),
        ("copilot", discover_copilot_logs),
        ("cursor", discover_cursor_sessions),
    ):
        path = discover()
        status = "missing"
        if path is not None:
            status = "unsupported" if path.suffix == ".vscdb" else "found"
        checked_sources.append(
            {
                "source": source_name,
                "status": status,
                "path": str(path) if path else None,
            }
        )
        if path is not None and path.suffix != ".vscdb":
            candidates.append((source_name, path))

    if not candidates:
        return {
            "developer_goal": "",
            "decisions": [],
            "assumptions": [],
            "active_tasks": [],
            "unresolved_issues": [],
            "open_questions": [],
            "signal_sources": {},
            "selected_source": None,
            "selected_path": None,
            "checked_sources": checked_sources,
        }

    for source_name, target in candidates:
        payload = ingest_chat_text(target)
        if payload["developer_goal"] or payload["decisions"] or payload["active_tasks"] or payload["open_questions"]:
            payload["selected_source"] = source_name
            payload["selected_path"] = str(target)
            payload["checked_sources"] = checked_sources
            payload["source_text"] = extract_chat_text(target)
            return payload

    return {
        "developer_goal": "",
        "decisions": [],
        "assumptions": [],
        "active_tasks": [],
        "unresolved_issues": [],
        "open_questions": [],
        "signal_sources": {},
        "selected_source": None,
        "selected_path": None,
        "checked_sources": checked_sources,
    }
