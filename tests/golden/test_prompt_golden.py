from __future__ import annotations

from pathlib import Path

from infinitecontex.core.models import PromptMode
from infinitecontex.service import InfiniteContextService


def test_prompt_contains_required_sections(tmp_repo: Path) -> None:
    svc = InfiniteContextService(tmp_repo)
    svc.init()
    snap = svc.snapshot(goal="refactor")

    out = svc.prompt(PromptMode.COPILOT_RESTORE, token_budget=900, snapshot_id=snap.id)

    assert "## Project Card" in out
    assert "## Structural Packet" in out
    assert "## Behavioral Packet" in out
    assert "## Working Set" in out
    assert "## Decisions" in out
    assert "## Restore Brief" in out


def test_prompt_includes_non_empty_working_set_and_decisions(tmp_repo: Path) -> None:
    svc = InfiniteContextService(tmp_repo)
    svc.init()
    svc._finalize_ingest(
        {
            "developer_goal": "fix prompts",
            "decisions": ["Use structured sessions"],
            "assumptions": [],
            "active_tasks": ["Improve packet budgeting"],
            "unresolved_issues": ["Prompt sections are empty"],
            "open_questions": ["Should each section get a minimum budget?"],
            "signal_sources": {"developer_goal": ["manual"]},
            "selected_source": "file",
            "selected_path": "/tmp/chat.txt",
        }
    )

    (tmp_repo / "README.md").write_text("changed readme\n", encoding="utf-8")
    snap = svc.snapshot(goal="fix prompts")

    out = svc.prompt(PromptMode.GENERIC_AGENT_RESTORE, token_budget=1200, snapshot_id=snap.id)

    assert "## Working Set" in out
    assert "Active files:" in out
    assert "## Decisions" in out
    assert "Decisions:" in out
    assert "## Restore Brief" in out
    assert "Restore checklist:" in out
