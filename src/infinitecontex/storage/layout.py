"""Filesystem layout for `.infctx` local state."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from infinitecontex.core.serde import dump_json


@dataclass(frozen=True)
class InfctxLayout:
    root: Path
    metadata: Path
    project: Path
    agents: Path
    snapshots: Path
    summaries: Path
    events: Path
    graph: Path
    retrieval: Path
    decisions: Path
    working_set: Path
    prompts: Path
    exports: Path


def build_layout(project_root: Path) -> InfctxLayout:
    base = project_root / ".infctx"
    return InfctxLayout(
        root=base,
        metadata=base / "metadata",
        project=base / "project",
        agents=base / "agents",
        snapshots=base / "snapshots",
        summaries=base / "summaries",
        events=base / "events",
        graph=base / "graph",
        retrieval=base / "retrieval",
        decisions=base / "decisions",
        working_set=base / "working_set",
        prompts=base / "prompts",
        exports=base / "exports",
    )


def initialize_layout(project_root: Path) -> InfctxLayout:
    layout = build_layout(project_root)
    for path in layout.__dict__.values():
        path.mkdir(parents=True, exist_ok=True)

    manifest = {
        "schema_version": 1,
        "name": "Infinite Context",
        "storage": {
            "db": "metadata/state.db",
            "events": "events/events.jsonl",
            "graph": "graph/context_graph.json",
        },
    }
    dump_json(layout.metadata / "manifest.json", manifest)
    return layout
