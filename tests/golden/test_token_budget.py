from __future__ import annotations

from pathlib import Path

from infinitecontex.core.models import PromptMode
from infinitecontex.service import InfiniteContextService


def test_small_token_budget_truncates_output(tmp_repo: Path) -> None:
    svc = InfiniteContextService(tmp_repo)
    svc.init()
    snap = svc.snapshot(goal="tiny")

    small = svc.prompt(PromptMode.GENERIC_AGENT_RESTORE, token_budget=120, snapshot_id=snap.id)
    large = svc.prompt(PromptMode.GENERIC_AGENT_RESTORE, token_budget=2000, snapshot_id=snap.id)

    assert len(small) < len(large)
