from __future__ import annotations

from pathlib import Path

from infinitecontex.core.models import PromptMode
from infinitecontex.service import InfiniteContextService


def test_snapshot_restore_and_prompt(tmp_repo: Path) -> None:
    svc = InfiniteContextService(tmp_repo)
    svc.init()
    snap = svc.snapshot(goal="ship tests")
    assert snap.id.startswith("snap-")
    assert (tmp_repo / ".infctx" / "project" / "inside.infinite_context.md").exists()
    assert (tmp_repo / ".infctx" / "project" / "inside.infinite_context.json").exists()

    report = svc.restore(snap.id)
    assert report["snapshot_id"] == snap.id

    prompt = svc.prompt(PromptMode.GENERIC_AGENT_RESTORE, token_budget=1000, snapshot_id=snap.id)
    assert "Project Card" in prompt
    assert "Restore Brief" in prompt
