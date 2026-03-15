from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from infinitecontex.cli import app


def test_cli_init_and_status(tmp_repo: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["init", "--project-root", str(tmp_repo), "--json"])
    assert result.exit_code == 0
    assert "initialized" in result.stdout

    result2 = runner.invoke(app, ["status", "--project-root", str(tmp_repo), "--json"])
    assert result2.exit_code == 0
    assert "project_root" in result2.stdout
