from __future__ import annotations

from pathlib import Path

from infinitecontex.api.client import InfiniteContextClient


def test_api_client_basic_flow(tmp_repo: Path) -> None:
    client = InfiniteContextClient(tmp_repo)
    client.init()
    snap = client.snapshot(goal="qa")
    status = client.status()
    assert snap.id.startswith("snap-")
    assert str(tmp_repo) == status["project_root"]
