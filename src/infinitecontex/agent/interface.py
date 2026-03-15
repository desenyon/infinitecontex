"""Agent tool interface layer for future MCP-style integrations."""

from __future__ import annotations

from pathlib import Path

from infinitecontex.core.models import PromptMode
from infinitecontex.service import InfiniteContextService


class AgentToolInterface:
    def __init__(self, project_root: str | Path = ".") -> None:
        self.svc = InfiniteContextService(Path(project_root).resolve())

    def tool_snapshot(self, goal: str = "") -> dict[str, object]:
        snapshot = self.svc.snapshot(goal=goal)
        return {"snapshot_id": snapshot.id, "created_at": snapshot.created_at.isoformat()}

    def tool_restore(self, snapshot_id: str | None = None) -> dict[str, object]:
        return self.svc.restore(snapshot_id=snapshot_id)

    def tool_prompt(self, mode: str = "generic-agent-restore", token_budget: int = 1200) -> dict[str, str | int]:
        prompt = self.svc.prompt(PromptMode(mode), token_budget)
        return {"mode": mode, "token_budget": token_budget, "prompt": prompt}

    def tool_search(self, query: str, limit: int = 10) -> list[dict[str, object]]:
        return self.svc.search(query, limit)
