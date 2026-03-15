"""Health and integrity checks for Infinite Context."""

from __future__ import annotations

import shutil
from pathlib import Path

from infinitecontex.storage.db import Database
from infinitecontex.storage.layout import build_layout


def run_doctor(project_root: Path) -> dict[str, str]:
    layout = build_layout(project_root)
    checks: dict[str, str] = {}

    checks["git"] = "ok" if shutil.which("git") else "missing"
    checks["layout"] = "ok" if layout.root.exists() else "missing"
    checks["manifest"] = "ok" if (layout.metadata / "manifest.json").exists() else "missing"

    db = Database(layout.metadata / "state.db")
    try:
        db.migrate()
        checks["sqlite"] = "ok"
    except Exception:
        checks["sqlite"] = "error"

    checks["graph"] = "ok" if (layout.graph / "context_graph.json").exists() else "missing"
    checks["retrieval"] = "ok" if (layout.retrieval).exists() else "missing"

    return checks
