from __future__ import annotations

from typer.testing import CliRunner

from infinitecontex.cli import app


def test_version_flag_works_without_command() -> None:
    runner = CliRunner()
    res = runner.invoke(app, ["--version"])
    assert res.exit_code == 0
    assert "infinitecontex" in res.stdout
