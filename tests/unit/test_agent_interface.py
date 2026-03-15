from __future__ import annotations

from pathlib import Path

from infinitecontex.agent.interface import AgentToolInterface


def test_agent_tools_smoke(tmp_repo: Path) -> None:
    tools = AgentToolInterface(tmp_repo)
    snap = tools.tool_snapshot(goal="agent")
    assert "snapshot_id" in snap

    prompt = tools.tool_prompt(mode="generic-agent-restore", token_budget=800)
    assert prompt["mode"] == "generic-agent-restore"
    assert isinstance(prompt["prompt"], str)
