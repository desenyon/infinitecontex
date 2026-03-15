"""Canonical data models for Infinite Context."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PromptMode(str, Enum):
    COPILOT_RESTORE = "copilot-restore"
    CLAUDE_CODE_RESTORE = "claude-code-restore"
    GENERIC_AGENT_RESTORE = "generic-agent-restore"
    HUMAN_HANDOFF = "human-handoff"


class LayerName(str, Enum):
    STRUCTURAL = "structural"
    BEHAVIORAL = "behavioral"
    INTENT = "intent"
    WORKING_SET = "working_set"


class FileFingerprint(BaseModel):
    path: str
    size: int
    mtime: float
    sha1: str


class StructuralContext(BaseModel):
    repo_tree_top: list[str] = Field(default_factory=list)
    key_files: list[str] = Field(default_factory=list)
    modules: dict[str, list[str]] = Field(default_factory=dict)
    entry_points: list[str] = Field(default_factory=list)
    config_files: list[str] = Field(default_factory=list)
    env_files: list[str] = Field(default_factory=list)
    directory_summaries: dict[str, str] = Field(default_factory=dict)


class BehavioralContext(BaseModel):
    call_hints: dict[str, list[str]] = Field(default_factory=dict)
    scripts: dict[str, str] = Field(default_factory=dict)
    routes_or_commands: list[str] = Field(default_factory=list)
    test_surfaces: list[str] = Field(default_factory=list)


class IntentContext(BaseModel):
    developer_goal: str = ""
    decisions: list[str] = Field(default_factory=list)
    rejected_options: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    active_tasks: list[str] = Field(default_factory=list)
    unresolved_issues: list[str] = Field(default_factory=list)
    inferred_change_purpose: str = ""


class WorkingSetContext(BaseModel):
    branch: str = ""
    recent_diffs: list[str] = Field(default_factory=list)
    active_files: list[str] = Field(default_factory=list)
    last_successful_commands: list[str] = Field(default_factory=list)
    last_failed_commands: list[str] = Field(default_factory=list)
    stack_traces: list[str] = Field(default_factory=list)
    failing_tests: list[str] = Field(default_factory=list)
    next_likely_action: str = ""
    pins: list[str] = Field(default_factory=list)


class Snapshot(BaseModel):
    id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    project_root: str
    structural: StructuralContext
    behavioral: BehavioralContext
    intent: IntentContext
    working_set: WorkingSetContext
    fingerprints: list[FileFingerprint] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class DecisionRecord(BaseModel):
    id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    summary: str
    rationale: str
    alternatives: list[str] = Field(default_factory=list)
    impact: str = ""
    tags: list[str] = Field(default_factory=list)


class ContextPacket(BaseModel):
    project_card: str
    subsystem_packets: dict[str, str] = Field(default_factory=dict)
    working_set_packet: str
    decisions_packet: str
    restore_brief: str


class RestoreReport(BaseModel):
    snapshot_id: str
    stale_items: list[str] = Field(default_factory=list)
    missing_items: list[str] = Field(default_factory=list)
    changed_items: list[str] = Field(default_factory=list)
    still_valid_items: list[str] = Field(default_factory=list)
    summary: str


class SearchResult(BaseModel):
    source: str
    key: str
    score: float
    snippet: str
