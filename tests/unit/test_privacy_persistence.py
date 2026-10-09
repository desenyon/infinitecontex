from __future__ import annotations

from pathlib import Path

import pytest

from infinitecontex.core.config import AppConfig
from infinitecontex.service import InfiniteContextService


def test_privacy_defaults_preview_without_persistence(tmp_repo: Path) -> None:
    svc = InfiniteContextService(tmp_repo)
    result = svc.ingest_chat_payload({"source_text": "secret sentinel", "developer_goal": "sentinel"})
    assert result["persisted"] is False
    assert not (svc.layout.working_set / "intent_state.json").exists()
    assert svc.search("sentinel") == []
    (svc.layout.working_set / "terminal.log").write_text("failed shell-sentinel exit 1")
    snapshot = svc.snapshot()
    assert snapshot.intent.developer_goal == ""
    assert snapshot.working_set.last_failed_commands == []
    assert "sentinel" not in (svc.layout.events / "events.jsonl").read_text()
    assert "sentinel" not in (svc.layout.snapshots / f"{snapshot.id}.json").read_text()


def test_enabled_persistence_redacts_and_replaces_chat_index(tmp_repo: Path) -> None:
    svc = InfiniteContextService(tmp_repo)
    config = AppConfig()
    config.policies.privacy.persist_chat_ingest = True
    config.policies.privacy.persist_shell_history = True
    svc.config_set(config)
    payload = {
        "selected_path": "chat.txt",
        "source_text": "oldmarker token=synthetic-secret",
        "developer_goal": "goal token=synthetic-secret",
    }
    assert svc.ingest_chat_payload(payload)["persisted"] is True
    payload["source_text"] = "newmarker token=synthetic-secret"
    svc.ingest_chat_payload(payload)
    assert svc.search("oldmarker") == []
    assert len(svc.search("newmarker")) == 1
    (svc.layout.working_set / "terminal.log").write_text("failed password=synthetic-shell exit 1")
    snapshot = svc.snapshot(goal="ship api_key=synthetic-goal")
    assert snapshot.working_set.last_failed_commands
    for row in svc.db.query("SELECT payload_json FROM snapshots"):
        assert "synthetic-" not in row[0]
    for path in [*svc.layout.agents.glob("*.md"), *svc.layout.prompts.glob("*.md")]:
        assert "synthetic-" not in path.read_text()
    assert "synthetic-" not in (svc.layout.working_set / "intent_state.json").read_text()
    config.policies.privacy.persist_chat_ingest = False
    config.policies.privacy.persist_shell_history = False
    svc.config_set(config)
    snapshot = svc.snapshot()
    assert snapshot.intent.developer_goal == ""
    assert snapshot.working_set.last_failed_commands == []


def test_notes_and_repo_insights_redacted_before_storage(tmp_repo: Path) -> None:
    svc = InfiniteContextService(tmp_repo)
    svc.note("token=synthetic-note", "password=synthetic-rationale", [], "", [])
    (tmp_repo / "README.md").write_text("api_key=synthetic-doc")
    snapshot = svc.snapshot()
    assert "synthetic-" not in snapshot.model_dump_json()
    assert "synthetic-" not in (svc.layout.events / "events.jsonl").read_text()


def test_invalid_redaction_regex_is_rejected() -> None:
    with pytest.raises(ValueError, match="invalid redaction"):
        AppConfig.model_validate({"policies": {"privacy": {"redact_patterns": ["["]}}})
