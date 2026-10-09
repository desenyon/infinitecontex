from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from infinitecontex.service import InfiniteContextService


def test_concurrent_processes_publish_consistent_snapshots(tmp_repo: Path) -> None:
    # Exercise the OS lock, not only the in-process mutex. No external services.
    script = (
        "from infinitecontex.service import InfiniteContextService; "
        "from pathlib import Path; import sys; "
        "InfiniteContextService(Path(sys.argv[1])).snapshot(goal=sys.argv[2])"
    )
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src")}
    processes = [
        subprocess.Popen(
            [sys.executable, "-c", script, str(tmp_repo), f"concurrentmarker{i}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        for i in range(3)
    ]
    for process in processes:
        output, error = process.communicate(timeout=30)
        assert process.returncode == 0, output + error
    svc = InfiniteContextService(tmp_repo)
    snapshots = svc.snapshots_recent()
    assert len(snapshots) == 3
    assert snapshots[0].id in (svc.layout.agents / "overview.md").read_text()
    assert len(svc.search("concurrentmarker0")) == 1
    assert svc.doctor()["recovery"] == "ok"
