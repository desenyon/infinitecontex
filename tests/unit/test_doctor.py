from __future__ import annotations

from pathlib import Path

from infinitecontex.service import InfiniteContextService


def test_doctor_reports_ok_after_init(tmp_repo: Path) -> None:
    svc = InfiniteContextService(tmp_repo)
    svc.init()
    out = svc.doctor()
    assert out["layout"] == "ok"
    assert out["manifest"] == "ok"
    assert out["sqlite"] == "ok"
