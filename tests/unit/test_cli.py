from __future__ import annotations

from pathlib import Path

from pytest import MonkeyPatch
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


def test_cli_search_renders_search_result_fields(tmp_repo: Path) -> None:
    runner = CliRunner()

    init_result = runner.invoke(app, ["init", "--project-root", str(tmp_repo)])
    assert init_result.exit_code == 0

    chat = tmp_repo / "chat.txt"
    chat.write_text("goal: ship release\n", encoding="utf-8")
    ingest_result = runner.invoke(app, ["ingest-chat", "--file", str(chat), "--project-root", str(tmp_repo)])
    assert ingest_result.exit_code == 0

    search_result = runner.invoke(app, ["search", "--query", "ship", "--project-root", str(tmp_repo)])
    assert search_result.exit_code == 0
    assert "chat" in search_result.stdout
    assert "ship release" in search_result.stdout


def test_cli_session_once_creates_initial_snapshot(tmp_repo: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["session", "--goal", "ship release", "--project-root", str(tmp_repo), "--once", "--json"],
    )

    assert result.exit_code == 0
    assert '"snapshot_id"' in result.stdout
    assert '"goal": "ship release"' in result.stdout


def test_cli_ingest_chat_auto_indexes_discovered_text(
    tmp_repo: Path, monkeypatch: MonkeyPatch
) -> None:
    runner = CliRunner()
    init_result = runner.invoke(app, ["init", "--project-root", str(tmp_repo)])
    assert init_result.exit_code == 0

    monkeypatch.setattr(
        "infinitecontex.capture.chat_auto_discover.auto_ingest_chat",
        lambda: {
            "developer_goal": "overhaul search",
            "decisions": ["Use structured sessions"],
            "assumptions": [],
            "active_tasks": ["Fix search rendering"],
            "unresolved_issues": [],
            "open_questions": [],
            "signal_sources": {"developer_goal": ["auto"]},
            "selected_source": "copilot",
            "selected_path": str(tmp_repo / "copilot-chat.json"),
            "checked_sources": [],
            "source_text": "We need to overhaul search and fix result rendering.",
        },
    )

    ingest_result = runner.invoke(app, ["ingest-chat", "--auto", "--project-root", str(tmp_repo)])
    assert ingest_result.exit_code == 0

    search_result = runner.invoke(app, ["search", "--query", "overhaul", "--project-root", str(tmp_repo)])
    assert search_result.exit_code == 0
    assert "overhaul search" in search_result.stdout.lower()


def test_cli_config_resolves_set_file_from_project_root(
    tmp_repo: Path, monkeypatch: MonkeyPatch
) -> None:
    runner = CliRunner()
    (tmp_repo / "config").mkdir()
    (tmp_repo / "config" / "default.json").write_text('{"capture_max_files": 42}', encoding="utf-8")
    monkeypatch.chdir(tmp_repo.parent)

    result = runner.invoke(
        app,
        [
            "config",
            "--project-root",
            str(tmp_repo),
            "--set-file",
            "config/default.json",
        ],
    )

    assert result.exit_code == 0


def test_cli_snapshot_history_compare_and_pin_management(tmp_repo: Path) -> None:
    runner = CliRunner()

    init_result = runner.invoke(app, ["init", "--project-root", str(tmp_repo)])
    assert init_result.exit_code == 0

    first = runner.invoke(app, ["snapshot", "--goal", "baseline", "--project-root", str(tmp_repo), "--json"])
    assert first.exit_code == 0

    (tmp_repo / "app.py").write_text("def run():\n    return 2\n", encoding="utf-8")
    second = runner.invoke(
        app,
        ["snapshot", "--goal", "upgrade tooling", "--project-root", str(tmp_repo), "--json"],
    )
    assert second.exit_code == 0

    history = runner.invoke(app, ["snapshots", "--project-root", str(tmp_repo), "--json"])
    assert history.exit_code == 0
    assert '"developer_goal": "upgrade tooling"' in history.stdout

    show = runner.invoke(app, ["show-snapshot", "--project-root", str(tmp_repo), "--json"])
    assert show.exit_code == 0
    assert '"prompt_path"' in show.stdout

    compare = runner.invoke(app, ["compare-snapshots", "--project-root", str(tmp_repo), "--json"])
    assert compare.exit_code == 0
    assert "changed_tracked_files" in compare.stdout
    assert "app.py" in compare.stdout

    pin = runner.invoke(app, ["pin", "--path", "app.py", "--note", "entry", "--project-root", str(tmp_repo)])
    assert pin.exit_code == 0

    pins = runner.invoke(app, ["pins", "--project-root", str(tmp_repo), "--json"])
    assert pins.exit_code == 0
    assert '"path": "app.py"' in pins.stdout
    assert '"note": "entry"' in pins.stdout

    unpin = runner.invoke(app, ["unpin", "--path", "app.py", "--project-root", str(tmp_repo)])
    assert unpin.exit_code == 0

    pins_after = runner.invoke(app, ["pins", "--project-root", str(tmp_repo), "--json"])
    assert pins_after.exit_code == 0
    assert pins_after.stdout.strip() == "[]"
