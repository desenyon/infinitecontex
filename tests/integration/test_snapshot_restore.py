from __future__ import annotations

import os
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


def test_restore_detects_content_change_even_when_mtime_matches(tmp_repo: Path) -> None:
    svc = InfiniteContextService(tmp_repo)
    svc.init()

    target = tmp_repo / "app.py"
    snap = svc.snapshot(goal="detect restore drift")
    original_mtime = target.stat().st_mtime

    target.write_text("def run():\n    return 2\n", encoding="utf-8")
    os.utime(target, (original_mtime, original_mtime))

    report = svc.restore(snap.id)

    assert "app.py" in report["changed_items"]
