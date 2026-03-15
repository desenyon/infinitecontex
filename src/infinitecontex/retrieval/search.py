"""Retrieval index and query utilities."""

from __future__ import annotations

from infinitecontex.core.models import SearchResult
from infinitecontex.storage.db import Database


class RetrievalEngine:
    def __init__(self, db: Database) -> None:
        self.db = db

    def index_document(self, source: str, key: str, body: str) -> None:
        self.db.execute(
            "INSERT INTO search_docs(source, key, body) VALUES (?, ?, ?)",
            (source, key, body),
        )

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        rows = self.db.query(
            """
            SELECT source, key, body,
              bm25(search_docs) AS rank
            FROM search_docs
            WHERE search_docs MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (query, limit),
        )
        return [
            SearchResult(
                source=row["source"],
                key=row["key"],
                score=float(-row["rank"]),
                snippet=str(row["body"])[:280],
            )
            for row in rows
        ]
