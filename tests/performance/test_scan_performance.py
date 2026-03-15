from __future__ import annotations

import time
from pathlib import Path

from infinitecontex.capture.repo_scan import scan_structural


def test_scan_performance_reasonable(tmp_path: Path) -> None:
    repo = tmp_path / "large"
    repo.mkdir()
    for i in range(800):
        (repo / f"f{i}.py").write_text("def x():\n    return 1\n", encoding="utf-8")

    start = time.perf_counter()
    structural, fps = scan_structural(repo)
    elapsed = time.perf_counter() - start

    assert structural.repo_tree_top
    assert len(fps) == 800
    assert elapsed < 3.0
