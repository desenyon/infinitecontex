from unittest.mock import patch

import pytest

from infinitecontex.service import InfiniteContextService


def test_service_restore_no_snapshots(tmp_path):
    svc = InfiniteContextService(tmp_path)
    svc.init()
    # Delete snapshots to simulate no snapshots
    svc.db.execute("DELETE FROM snapshots")
    with pytest.raises(ValueError, match="no snapshots found"):
        svc.restore()


def test_service_prompt_no_snapshots(tmp_path):
    svc = InfiniteContextService(tmp_path)
    svc.init()
    svc.db.execute("DELETE FROM snapshots")
    from infinitecontex.core.models import PromptMode

    with pytest.raises(ValueError, match="no snapshots found"):
        svc.prompt(PromptMode.GENERIC_AGENT_RESTORE, 1000)


def test_service_list_pins_no_db(tmp_path):
    svc = InfiniteContextService(tmp_path)
    # Don't init, so no DB exists
    assert svc.list_pins() == []


def test_service_load_snapshot_fallback(tmp_path):
    svc = InfiniteContextService(tmp_path)
    svc.init()
    with pytest.raises(ValueError, match="snapshot not found: unknown"):
        svc._load_snapshot("unknown")


def test_service_latest_snapshot_id_no_db(tmp_path):
    svc = InfiniteContextService(tmp_path)
    assert svc._latest_snapshot_id() is None
    with pytest.raises(ValueError, match="no snapshots found"):
        svc._latest_snapshot_id(required=True)


def test_service_latest_snapshot_id_empty_db(tmp_path):
    svc = InfiniteContextService(tmp_path)
    svc.init()
    assert svc._latest_snapshot_id() is None
    with pytest.raises(ValueError, match="no snapshots found"):
        svc._latest_snapshot_id(required=True)


def test_service_load_intent_state_empty(tmp_path):
    svc = InfiniteContextService(tmp_path)
    svc.init()
    # File doesn't exist
    assert svc._load_intent_state() == {}


def test_service_branch_exception(tmp_path):
    svc = InfiniteContextService(tmp_path)
    with patch("infinitecontex.capture.git_state.current_branch", side_effect=Exception("git failed")):
        assert svc._branch() == "unknown"


def test_service_write_handoff_empty_fields(tmp_path):
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
