from __future__ import annotations

from pathlib import Path

import pytest
from click.exceptions import Exit
from pytest import MonkeyPatch
from typer.testing import CliRunner
from watchfiles import Change

import infinitecontex.cli as cli_module
from infinitecontex.cli import _emit, _filter_watch_changes, _matches_pattern, _run_action, app
from infinitecontex.core.config import AppConfig, save_repo_config


def test_cli_init_and_status(tmp_repo: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["init", "--project-root", str(tmp_repo), "--json"])
    assert result.exit_code == 0
    assert "initialized" in result.stdout

    result2 = runner.invoke(app, ["status", "--project-root", str(tmp_repo), "--json"])
    assert result2.exit_code == 0
    assert "project_root" in result2.stdout


def test_cli_accepts_project_root_as_global_option(tmp_repo: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["--project-root", str(tmp_repo), "init", "--json"])

    assert result.exit_code == 0
    assert (tmp_repo / ".infctx").exists()


def test_cli_search_renders_search_result_fields(tmp_repo: Path) -> None:
    config = AppConfig()
    config.policies.privacy.persist_chat_ingest = True
    save_repo_config(tmp_repo, config)
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


def test_cli_ingest_chat_auto_indexes_discovered_text(tmp_repo: Path, monkeypatch: MonkeyPatch) -> None:
    config = AppConfig()
    config.policies.privacy.persist_chat_ingest = True
    save_repo_config(tmp_repo, config)
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


def test_cli_config_resolves_set_file_from_project_root(tmp_repo: Path, monkeypatch: MonkeyPatch) -> None:
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


def test_cli_core_commands_and_renderers(tmp_repo: Path, tmp_path: Path) -> None:
    runner = CliRunner()

    init_result = runner.invoke(app, ["init", "--project-root", str(tmp_repo)])
    assert init_result.exit_code == 0

    note = runner.invoke(
        app,
        [
            "note",
            "--summary",
            "Use compact snapshots",
            "--rationale",
            "Keeps prompts focused",
            "--alternative",
            "Full transcript",
            "--impact",
            "Lower token use",
            "--tag",
            "memory",
            "--project-root",
            str(tmp_repo),
        ],
    )
    assert note.exit_code == 0
    assert "Saved decision" in note.stdout

    decisions = runner.invoke(app, ["decisions", "--project-root", str(tmp_repo)])
    assert decisions.exit_code == 0
    assert "Use compact snapshots" in decisions.stdout

    snapshot = runner.invoke(app, ["snapshot", "--goal", "cover cli", "--project-root", str(tmp_repo)])
    assert snapshot.exit_code == 0
    assert "Snapshot created" in snapshot.stdout

    prompt = runner.invoke(app, ["prompt", "--project-root", str(tmp_repo), "--token-budget", "500"])
    assert prompt.exit_code == 0
    assert "Restore Brief" in prompt.stdout

    restore = runner.invoke(app, ["restore", "--project-root", str(tmp_repo)])
    assert restore.exit_code == 0
    assert "Restore Report" in restore.stdout

    diff = runner.invoke(app, ["diff-summary", "--project-root", str(tmp_repo)])
    assert diff.exit_code == 0
    assert "clean" in diff.stdout.lower()

    doctor = runner.invoke(app, ["doctor", "--project-root", str(tmp_repo)])
    assert doctor.exit_code == 0
    assert "Doctor Diagnostics" in doctor.stdout

    config_json = runner.invoke(app, ["config", "--project-root", str(tmp_repo), "--json"])
    assert config_json.exit_code == 0
    assert "capture_max_files" in config_json.stdout

    archive = tmp_path / "ctx.tgz"
    export_result = runner.invoke(app, ["export", "--output", str(archive), "--project-root", str(tmp_repo)])
    assert export_result.exit_code == 0
    assert archive.exists()

    imported_repo = tmp_path / "imported"
    imported_repo.mkdir()
    import_result = runner.invoke(
        app,
        ["import", "--archive", str(archive), "--project-root", str(imported_repo)],
    )
    assert import_result.exit_code == 0
    assert "Import complete" in import_result.stdout


def test_cli_setup_agent_targets_and_errors(tmp_repo: Path) -> None:
    runner = CliRunner()

    for agent, expected_path in [
        ("cursor", ".cursorrules"),
        ("claude", "CLAUDE.md"),
        ("windsurf", ".windsurfrules"),
        ("copilot", ".github/copilot-instructions.md"),
    ]:
        result = runner.invoke(app, ["setup-agent", agent, "--project-root", str(tmp_repo)])
        assert result.exit_code == 0
        assert (tmp_repo / expected_path).exists()

    unsupported = runner.invoke(app, ["setup-agent", "unknown", "--project-root", str(tmp_repo)])
    assert unsupported.exit_code == 1
    assert "Unsupported agent" in unsupported.stdout


def test_cli_error_paths(tmp_repo: Path) -> None:
    runner = CliRunner()

    no_command = runner.invoke(app, [])
    assert no_command.exit_code == 0
    assert "Usage:" in no_command.stdout

    missing_chat_source = runner.invoke(app, ["ingest-chat", "--project-root", str(tmp_repo)])
    assert missing_chat_source.exit_code == 1
    assert "Must provide" in missing_chat_source.stdout

    config_missing_file = runner.invoke(
        app,
        ["config", "--set-file", "missing.json", "--project-root", str(tmp_repo)],
    )
    assert config_missing_file.exit_code == 1
    assert "was not found" in config_missing_file.stdout

    unpin_missing = runner.invoke(app, ["unpin", "--path", "missing.py", "--project-root", str(tmp_repo)])
    assert unpin_missing.exit_code == 1
    assert "No pin exists" in unpin_missing.stdout


def test_cli_auto_ingest_edge_cases(tmp_repo: Path, monkeypatch: MonkeyPatch) -> None:
    runner = CliRunner()

    monkeypatch.setattr("infinitecontex.capture.chat_auto_discover.auto_ingest_chat", lambda: "bad")
    bad_payload = runner.invoke(app, ["ingest-chat", "--auto", "--project-root", str(tmp_repo)])
    assert bad_payload.exit_code == 1
    assert "usable payload" in bad_payload.stdout

    monkeypatch.setattr(
        "infinitecontex.capture.chat_auto_discover.auto_ingest_chat",
        lambda: {"selected_source": None},
    )
    no_source = runner.invoke(app, ["ingest-chat", "--auto", "--project-root", str(tmp_repo)])
    assert no_source.exit_code == 0
    assert "No local chat source" in no_source.stdout


def test_cli_cleanup_requires_confirmation_and_removes_old_snapshots(tmp_repo: Path) -> None:
    runner = CliRunner()

    assert runner.invoke(app, ["init", "--project-root", str(tmp_repo)]).exit_code == 0
    assert runner.invoke(app, ["snapshot", "--goal", "one", "--project-root", str(tmp_repo)]).exit_code == 0
    (tmp_repo / "app.py").write_text("def run():\n    return 2\n", encoding="utf-8")
    assert runner.invoke(app, ["snapshot", "--goal", "two", "--project-root", str(tmp_repo)]).exit_code == 0

    dry_run = runner.invoke(app, ["cleanup", "--keep", "1", "--project-root", str(tmp_repo)])
    assert dry_run.exit_code == 1
    assert "Re-run with `--yes`" in dry_run.stdout

    cleanup = runner.invoke(app, ["cleanup", "--keep", "1", "--yes", "--project-root", str(tmp_repo)])
    assert cleanup.exit_code == 0
    assert "Removed 1 old snapshots" in cleanup.stdout

    no_op = runner.invoke(app, ["cleanup", "--keep", "5", "--project-root", str(tmp_repo)])
    assert no_op.exit_code == 0
    assert "Kept all" in no_op.stdout


def test_cli_helpers_filter_watch_changes(tmp_repo: Path) -> None:
    keep = tmp_repo / "src" / "app.py"
    skip = tmp_repo / ".infctx" / "state.db"
    outside = tmp_repo.parent / "outside.py"

    assert _matches_pattern(".infctx/state.db", [".infctx/**"]) is True
    assert _matches_pattern("cache.py", ["**/cache.py"]) is True
    assert _matches_pattern("foo/cache.py", ["**/cache.py"]) is True
    assert _matches_pattern("src/app.py", ["src/*.py"]) is True
    assert _matches_pattern("src/app.py", ["docs/**"]) is False

    changes = {
        (Change.modified, str(keep)),
        (Change.added, str(skip)),
        (Change.deleted, str(outside)),
    }

    assert _filter_watch_changes(changes, tmp_repo, [".infctx/**"]) == ["src/app.py"]


def test_cli_run_action_prints_errors() -> None:
    def fail() -> object:
        raise ValueError("broken action")

    with pytest.raises(Exit):
        _run_action(fail)


def test_cli_emit_human_renderers(capsys: pytest.CaptureFixture[str]) -> None:
    _emit("plain text", False)
    _emit({"a": [], "b": ["x"], "c": "value"}, False)
    _emit({"check": "ok", "other": "bad"}, False, "doctor")
    _emit(
        {
            "project_root": "/repo",
            "latest_snapshot": "snap-a",
            "latest_snapshot_created_at": "now",
            "snapshot_count": 2,
            "branch": "main",
            "pins": ["app.py"],
            "recent_commits": ["abc123"],
            "developer_goal": "ship",
            "active_tasks": ["test"],
            "unresolved_issues": ["none"],
        },
        False,
        "status",
    )
    _emit(
        {
            "developer_goal": "ship",
            "active_tasks": ["test"],
            "decisions": ["decide"],
            "unresolved_issues": ["issue"],
            "selected_source": "file",
            "selected_path": "chat.txt",
        },
        False,
        "ingest_chat",
    )
    _emit({"project_root": "/repo", "goal": "ship", "snapshot_id": "snap-a"}, False, "session")
    _emit({"capture_max_files": 10}, False, "config")
    _emit({"snapshot_id": "snap-a", "changed_items": []}, False, "restore")
    _emit(
        {
            "id": "snap-a",
            "created_at": "now",
            "working_set": {"branch": "main", "active_files": ["app.py"]},
            "intent": {"developer_goal": "ship", "active_tasks": ["test"], "unresolved_issues": ["issue"]},
            "prompt_path": "prompt.md",
            "metrics": {"files": 1},
        },
        False,
        "snapshot_detail",
    )
    _emit(
        {
            "from_snapshot_id": "snap-a",
            "to_snapshot_id": "snap-b",
            "from_goal": "old",
            "to_goal": "new",
            "from_branch": "main",
            "to_branch": "main",
            "summary": "changed",
            "metric_deltas": {"files": 1},
            "changed_tracked_files": ["app.py"],
            "added_tasks": ["task"],
            "removed_tasks": [],
            "added_issues": [],
            "removed_issues": ["issue"],
        },
        False,
        "snapshot_compare",
    )
    _emit(
        {
            "from_snapshot_id": "snap-a",
            "to_snapshot_id": "snap-b",
            "summary": "same",
            "metric_deltas": {},
            "changed_tracked_files": [],
            "added_tasks": [],
            "removed_tasks": [],
            "added_issues": [],
            "removed_issues": [],
        },
        False,
        "snapshot_compare",
    )
    _emit({"diff_summary": ["modified app.py"]}, False, "diff_summary")
    _emit([{"id": "d1", "summary": "decision", "created_at": "2026-01-01T00:00:00"}], False, "decisions")
    _emit([], False, "decisions")
    _emit(
        [
            {
                "id": "snap-a",
                "created_at": "2026-01-01T00:00:00",
                "developer_goal": "ship",
                "branch": "main",
                "file_count": 3,
                "active_task_count": 1,
            }
        ],
        False,
        "snapshots",
    )
    _emit([], False, "snapshots")
    _emit([{"path": "app.py", "note": "entry", "created_at": "2026-01-01T00:00:00"}], False, "pins")
    _emit([], False, "pins")
    _emit([{"source": "chat", "key": "goal", "snippet": "ship"}], False, "search")
    _emit([], False, "search")
    _emit(["a", "b"], False)
    _emit(42, False)

    out = capsys.readouterr().out
    assert "plain text" in out
    assert "Doctor Diagnostics" in out
    assert "Snapshot Comparison" in out


def test_cli_config_rejects_invalid_json(tmp_repo: Path) -> None:
    runner = CliRunner()
    bad_config = tmp_repo / "bad.json"
    bad_config.write_text("{bad", encoding="utf-8")

    result = runner.invoke(app, ["config", "--set-file", str(bad_config), "--project-root", str(tmp_repo)])

    assert result.exit_code == 1
    assert "Failed to load configuration" in result.stdout


def test_cli_session_json_requires_once(tmp_repo: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["session", "--json", "--project-root", str(tmp_repo)])

    assert result.exit_code == 1
    assert "only supported together with `--once`" in result.stdout


def test_cli_session_rejects_missing_initial_snapshot_id(tmp_repo: Path, monkeypatch: MonkeyPatch) -> None:
    runner = CliRunner()

    monkeypatch.setattr(cli_module.InfiniteContextService, "snapshot", lambda _self, goal="": object())

    result = runner.invoke(app, ["session", "--once", "--project-root", str(tmp_repo)])

    assert result.exit_code == 1
    assert "Failed to create the initial session snapshot" in result.stdout


class _DummyLive:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        self.updates = 0

    def __enter__(self) -> "_DummyLive":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def update(self, _panel: object) -> None:
        self.updates += 1


def test_cli_session_live_handles_change_batches(tmp_repo: Path, monkeypatch: MonkeyPatch) -> None:
    runner = CliRunner()

    def fake_watch(_root: Path, debounce: int) -> list[set[tuple[Change, str]]]:
        assert debounce == 1
        return [
            {(Change.modified, str(tmp_repo / ".infctx" / "ignored"))},
            {(Change.modified, str(tmp_repo / "app.py"))},
        ]

    monkeypatch.setattr(cli_module, "Live", _DummyLive)
    monkeypatch.setattr(cli_module, "watch", fake_watch)

    result = runner.invoke(
        app,
        ["session", "--project-root", str(tmp_repo), "--debounce-ms", "1", "--min-interval-sec", "0"],
    )

    assert result.exit_code == 0


def test_cli_session_live_handles_cooldown_and_snapshot_failure(tmp_repo: Path, monkeypatch: MonkeyPatch) -> None:
    runner = CliRunner()

    def fake_watch(_root: Path, debounce: int) -> list[set[tuple[Change, str]]]:
        return [
            {(Change.modified, str(tmp_repo / "app.py"))},
            {(Change.modified, str(tmp_repo / "README.md"))},
        ]

    original_snapshot = cli_module.InfiniteContextService.snapshot
    calls = {"count": 0}

    def flaky_snapshot(self: object, goal: str = "") -> object:
        calls["count"] += 1
        if calls["count"] == 2:
            raise ValueError("snapshot failed")
        return original_snapshot(self, goal=goal)  # type: ignore[arg-type]

    times = iter([10_000.0, 10_000.5, 10_002.0])

    monkeypatch.setattr(cli_module, "Live", _DummyLive)
    monkeypatch.setattr(cli_module, "watch", fake_watch)
    monkeypatch.setattr(cli_module.time, "time", lambda: next(times))
    monkeypatch.setattr(cli_module.InfiniteContextService, "snapshot", flaky_snapshot)

    result = runner.invoke(
        app,
        ["session", "--project-root", str(tmp_repo), "--debounce-ms", "1", "--min-interval-sec", "1"],
    )

    assert result.exit_code == 0
    assert calls["count"] == 2


def test_cli_watch_delegates_to_session(tmp_repo: Path, monkeypatch: MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_session(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(cli_module, "session", fake_session)

    cli_module.watch_loop(goal="ship", project_root=tmp_repo, debounce_ms=9, min_interval_sec=8)

    assert captured == {
        "goal": "ship",
        "project_root": tmp_repo,
        "debounce_ms": 9,
        "min_interval_sec": 8,
        "once": False,
        "json": False,
    }


def test_setup_agent_preserves_user_instructions_and_is_idempotent(tmp_repo: Path) -> None:
    runner = CliRunner()
    path = tmp_repo / "CLAUDE.md"
    path.write_text("# Existing project rules\nKeep user changes.\n")
    for _ in range(2):
        result = runner.invoke(app, ["setup-agent", "claude", "--project-root", str(tmp_repo)])
        assert result.exit_code == 0
    content = path.read_text()
    assert content.startswith("# Existing project rules\nKeep user changes.")
    assert content.count("<!-- infinitecontex:start -->") == 1


def test_setup_agent_rejects_symlink_destination(tmp_repo: Path, tmp_path: Path) -> None:
    external = tmp_path / "external.md"
    external.write_text("Keep me")
    (tmp_repo / "CLAUDE.md").symlink_to(external)
    result = CliRunner().invoke(app, ["setup-agent", "claude", "--project-root", str(tmp_repo)])
    assert result.exit_code == 1
    assert external.read_text() == "Keep me"


def test_cli_repair_and_preview(tmp_repo: Path, tmp_path: Path) -> None:
    chat = tmp_path / "chat.txt"
    chat.write_text("goal: previewmarker")
    runner = CliRunner()
    result = runner.invoke(app, ["ingest-chat", "--file", str(chat), "--project-root", str(tmp_repo)])
    assert result.exit_code == 0
    assert "preview only" in result.stdout
    result = runner.invoke(app, ["repair", "--project-root", str(tmp_repo), "--json"])
    assert result.exit_code == 0
    assert '"status": "repaired"' in result.stdout


def test_json_output_preserves_long_strings_and_markup(capsys: pytest.CaptureFixture[str]) -> None:
    import json

    payload = {"path": "/very/long/" * 40 + "[bold]literal[/bold]"}
    _emit(payload, True)
    assert json.loads(capsys.readouterr().out) == payload
