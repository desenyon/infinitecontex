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


def test_api_client_snapshot_and_pin_extensions(tmp_repo: Path) -> None:
    client = InfiniteContextClient(tmp_repo)
    client.init()
    first = client.snapshot(goal="baseline")
    (tmp_repo / "app.py").write_text("def run():\n    return 3\n", encoding="utf-8")
    second = client.snapshot(goal="improve memory")

    history = client.snapshots(limit=5)
    assert history[0].id == second.id

    details = client.show_snapshot(second.id)
    assert details["id"] == second.id

    comparison = client.compare_snapshots(first.id, second.id)
    assert "app.py" in comparison.changed_tracked_files

    client.pin("app.py", "entry")
    pins = client.pins()
    assert pins[0].path == "app.py"
    assert client.unpin("app.py") is True
