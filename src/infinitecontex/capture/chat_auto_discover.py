"""Chat log auto-discovery for AI coding assistants."""

from pathlib import Path
from typing import Any

from infinitecontex.capture.chat_ingest import ingest_chat_text


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
        # Find the most recently modified state.vscdb
        recent_db = _find_recent_file(storage, "state.vscdb")
        if recent_db:
            # We can't trivially parse it safely here without raw text extraction,
            # so we might dump strings from it if we wanted to be extreme.
            # But let's dump a fake path indicator so the ingestion can at least try.
            # Realistically, Cursor chat is hard to parse live from binary dict form.
            pass

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
        recent = _find_recent_file(storage, "*.json")
        if recent:
            return recent
    return None


def discover_claude_logs() -> Path | None:
    """Find local CLAUDE.md or Claude logs."""
    local_claude = Path("CLAUDE.md")
    if local_claude.exists() and local_claude.is_file():
        return local_claude
    return None


def auto_ingest_chat() -> dict[str, Any]:
    """Discover recent AI chat logs and extract context from them."""
    found_paths: list[Path] = []

    # Try Claude
    claude = discover_claude_logs()
    if claude:
        found_paths.append(claude)

    # Try Copilot
    copilot = discover_copilot_logs()
    if copilot:
        found_paths.append(copilot)

    # Try Cursor
    cursor = discover_cursor_sessions()
    if cursor:
        found_paths.append(cursor)

    if not found_paths:
        return {"decisions": [], "assumptions": [], "active_tasks": [], "unresolved_issues": []}

    target = found_paths[0]  # Just use the most highly relevant/recent one found
    return ingest_chat_text(target)
