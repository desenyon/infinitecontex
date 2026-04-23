from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from infinitecontex.service import InfiniteContextService


def test_service_restore_no_snapshots(tmp_path: Path) -> None:
    svc = InfiniteContextService(tmp_path)
    svc.init()
    # Delete snapshots to simulate no snapshots
    svc.db.execute("DELETE FROM snapshots")
    with pytest.raises(ValueError, match="no snapshots found"):
        svc.restore()


def test_service_prompt_no_snapshots(tmp_path: Path) -> None:
    svc = InfiniteContextService(tmp_path)
    svc.init()
    svc.db.execute("DELETE FROM snapshots")
    from infinitecontex.core.models import PromptMode

    with pytest.raises(ValueError, match="no snapshots found"):
        svc.prompt(PromptMode.GENERIC_AGENT_RESTORE, 1000)


def test_service_list_pins_no_db(tmp_path: Path) -> None:
    svc = InfiniteContextService(tmp_path)
    # Don't init, so no DB exists
    assert svc.list_pins() == []


def test_service_load_snapshot_fallback(tmp_path: Path) -> None:
    svc = InfiniteContextService(tmp_path)
    svc.init()
    with pytest.raises(ValueError, match="snapshot not found: unknown"):
        svc._load_snapshot("unknown")


def test_service_latest_snapshot_id_no_db(tmp_path: Path) -> None:
    svc = InfiniteContextService(tmp_path)
    assert svc._latest_snapshot_id() is None
    with pytest.raises(ValueError, match="no snapshots found"):
        svc._latest_snapshot_id(required=True)


def test_service_latest_snapshot_id_empty_db(tmp_path: Path) -> None:
    svc = InfiniteContextService(tmp_path)
    svc.init()
    assert svc._latest_snapshot_id() is None
    with pytest.raises(ValueError, match="no snapshots found"):
        svc._latest_snapshot_id(required=True)


def test_service_load_intent_state_empty(tmp_path: Path) -> None:
    svc = InfiniteContextService(tmp_path)
    svc.init()
    # File doesn't exist
    assert svc._load_intent_state() == {}


def test_service_branch_exception(tmp_path: Path) -> None:
    svc = InfiniteContextService(tmp_path)
    with patch("infinitecontex.capture.git_state.current_branch", side_effect=Exception("git failed")):
        assert svc._branch() == "unknown"


def test_service_write_handoff_empty_fields(tmp_path: Path) -> None:
    svc = InfiniteContextService(tmp_path)
    svc.init()

    # Create fake snapshot
    import datetime

    from infinitecontex.core.models import (
        BehavioralContext,
        IntentContext,
        Snapshot,
        StructuralContext,
        WorkingSetContext,
    )

    struct = StructuralContext(
        repo_tree_top=[],
        key_files=[],
        modules={},
        entry_points=[],
        config_files=[],
        env_files=[],
        directory_summaries={"mod_a": "Summary A"},  # noqa: E501
    )
    behav = BehavioralContext(call_hints={}, scripts={}, routes_or_commands=[], test_surfaces=[])
    # Empty decisions, empty issues to trigger lines 330, 340
    intent = IntentContext(
        developer_goal="",
        decisions=[],
        assumptions=[],
        active_tasks=[],
        unresolved_issues=[],
        inferred_change_purpose="",  # noqa: E501
    )
    # Empty recent diffs, last_failed commands to trigger lines 355, 360-361
    working = WorkingSetContext(
        branch="main",
        last_successful_commands=[],
        last_failed_commands=[],
        stack_traces=[],
        failing_tests=[],
        active_files=[],
        recent_diffs=[],
        next_likely_action="",  # noqa: E501
    )

    snapshot = Snapshot(
        id="snap-test",
        project_root=str(tmp_path),
        created_at=datetime.datetime.now(datetime.UTC),
        structural=struct,
        behavioral=behav,
        intent=intent,
        working_set=working,
        fingerprints=[],
        metrics={},
    )

    # Just run it to ensure those else branches execute
    svc._write_project_handoff(snapshot, "prompt text")

    assert (svc.layout.agents / "decisions.md").exists()
    assert (svc.layout.agents / "recent_changes.md").exists()

    decisions_text = (svc.layout.agents / "decisions.md").read_text()
    assert "*No recent decisions recorded.*" in decisions_text
    assert "*None*" in decisions_text

    changes_text = (svc.layout.agents / "recent_changes.md").read_text()
    assert "*Workspace is clean.*" in changes_text


def test_service_status_includes_intent_summary(tmp_path: Path) -> None:
    svc = InfiniteContextService(tmp_path)
    svc.init()
    svc._finalize_ingest(
        {
            "developer_goal": "overhaul the cli",
            "decisions": ["Use structured sessions"],
            "assumptions": [],
            "active_tasks": ["Update docs"],
            "unresolved_issues": ["Watch mode is confusing"],
            "open_questions": [],
            "signal_sources": {"developer_goal": ["manual"]},
        }
    )

    status = svc.status()

    assert status["developer_goal"] == "overhaul the cli"
    assert status["active_tasks"] == ["Update docs"]
    assert status["unresolved_issues"] == ["Watch mode is confusing"]
    assert status["snapshot_count"] == 0


def test_service_status_falls_back_to_latest_snapshot_intent(tmp_repo: Path) -> None:
    svc = InfiniteContextService(tmp_repo)
    svc.init()
    svc.snapshot(goal="ship release")

    status = svc.status()

    assert status["developer_goal"] == "ship release"
    assert status["snapshot_count"] == 1
    assert status["latest_snapshot_created_at"] is not None


def test_service_snapshot_history_and_compare(tmp_repo: Path) -> None:
    svc = InfiniteContextService(tmp_repo)
    svc.init()
    first = svc.snapshot(goal="baseline")

    svc._finalize_ingest(
        {
            "developer_goal": "baseline",
            "decisions": [],
            "assumptions": [],
            "active_tasks": ["Refine output"],
            "unresolved_issues": ["Search is noisy"],
            "open_questions": [],
            "signal_sources": {"developer_goal": ["manual"]},
        }
    )
    target = tmp_repo / "app.py"
    target.write_text("def run():\n    return 2\n", encoding="utf-8")
    second = svc.snapshot(goal="upgrade snapshot tooling")

    history = svc.snapshots_recent(limit=5)
    comparison = svc.compare_snapshots(from_snapshot_id=first.id, to_snapshot_id=second.id)
    details = svc.snapshot_details(second.id)

    assert history[0].id == second.id
    assert history[0].developer_goal == "upgrade snapshot tooling"
    assert "app.py" in comparison.changed_tracked_files
    assert comparison.added_tasks == ["Refine output"]
    assert comparison.added_issues == ["Search is noisy"]
    assert details["id"] == second.id
    assert str(details["prompt_path"]).endswith(f"{second.id}.prompt.md")


def test_service_pin_records_and_unpin(tmp_repo: Path) -> None:
    svc = InfiniteContextService(tmp_repo)
    svc.init()
    svc.pin("app.py", "entrypoint")

    pins = svc.pin_records()
    assert len(pins) == 1
    assert pins[0].path == "app.py"
    assert pins[0].note == "entrypoint"

    assert svc.unpin("app.py") is True
    assert svc.unpin("app.py") is False
    assert svc.pin_records() == []


def test_service_snapshot_preserves_full_changed_file_name(tmp_path: Path) -> None:
    svc = InfiniteContextService(tmp_path)
    svc.init()

    tracked = tmp_path / "CHANGELOG.md"
    tracked.write_text("initial\n", encoding="utf-8")

    import subprocess

    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "dev@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Dev"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "CHANGELOG.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)

    tracked.write_text("changed\n", encoding="utf-8")

    snap = svc.snapshot(goal="test changed paths")

    assert "CHANGELOG.md" in snap.working_set.active_files
    assert "CHANGELOG.md" in (svc.layout.agents / "overview.md").read_text(encoding="utf-8")
