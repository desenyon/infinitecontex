from __future__ import annotations

import subprocess
from pathlib import Path


def test_module_entrypoint_version() -> None:
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [str(root / ".venv" / "bin" / "python"), "-m", "infinitecontex", "--help"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Infinite Context" in result.stdout
