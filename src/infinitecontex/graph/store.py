"""Graph abstraction backed by NetworkX."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import networkx as nx
from networkx.readwrite import json_graph

from infinitecontex.core.serde import dump_json, load_json


class ContextGraphStore:
    def __init__(self, graph_path: Path) -> None:
        self.graph_path = graph_path
        self.graph: nx.DiGraph[str] = nx.DiGraph()

    def add_file_nodes(self, file_paths: Iterable[str]) -> None:
        for file_path in file_paths:
            self.graph.add_node(file_path, kind="file")

    def add_calls(self, call_hints: dict[str, list[str]]) -> None:
        for source, calls in call_hints.items():
            self.graph.add_node(source, kind="function")
            for target in calls:
                self.graph.add_node(target, kind="symbol")
                self.graph.add_edge(source, target, relation="calls")

    def central_nodes(self, limit: int = 10) -> list[str]:
        if self.graph.number_of_nodes() == 0:
            return []
        centrality = nx.degree_centrality(self.graph)
        ranked = sorted(centrality.items(), key=lambda item: item[1], reverse=True)
        return [node for node, _ in ranked[:limit]]

    def save(self) -> None:
        payload = json_graph.node_link_data(self.graph)
        dump_json(self.graph_path, payload)

    def load(self) -> None:
        if not self.graph_path.exists():
            return
        payload = load_json(self.graph_path)
        self.graph = json_graph.node_link_graph(payload)
