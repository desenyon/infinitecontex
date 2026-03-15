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
