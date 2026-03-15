from __future__ import annotations

from pathlib import Path

from infinitecontex.core.config import load_app_config


def test_load_default_config(tmp_path: Path) -> None:
    cfg = load_app_config(tmp_path)
    assert cfg.policies.token.default_budget >= cfg.policies.token.min_budget
    assert "generic-agent-restore" in cfg.modes
