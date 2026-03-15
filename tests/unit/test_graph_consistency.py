from __future__ import annotations

from pathlib import Path

from infinitecontex.graph.store import ContextGraphStore
from infinitecontex.storage.layout import initialize_layout


def test_graph_roundtrip(tmp_repo: Path) -> None:
    layout = initialize_layout(tmp_repo)
    graph = ContextGraphStore(layout.graph / "context_graph.json")
    graph.add_file_nodes(["app.py"])
    graph.add_calls({"app.py:run": ["helper"]})
    graph.save()

    other = ContextGraphStore(layout.graph / "context_graph.json")
    other.load()
    assert "app.py" in other.graph.nodes
    assert ("app.py:run", "helper") in other.graph.edges
