"""Decision memory persistence layer."""

from __future__ import annotations

from datetime import UTC, datetime

import orjson

from infinitecontex.core.models import DecisionRecord
from infinitecontex.storage.db import Database


class DecisionStore:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, record: DecisionRecord) -> None:
        self.db.execute(
            """
            INSERT INTO decisions(id, created_at, summary, rationale, alternatives_json, impact, tags_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.id,
                record.timestamp.isoformat(),
                record.summary,
                record.rationale,
                orjson.dumps(record.alternatives).decode(),
                record.impact,
                orjson.dumps(record.tags).decode(),
            ),
        )

    def list_recent(self, limit: int = 30) -> list[DecisionRecord]:
        rows = self.db.query(
            (
                "SELECT id, created_at, summary, rationale, alternatives_json, impact, tags_json "
                "FROM decisions ORDER BY created_at DESC LIMIT ?"
            ),
            (limit,),
        )
        records: list[DecisionRecord] = []
        for row in rows:
            records.append(
                DecisionRecord(
                    id=str(row["id"]),
                    timestamp=datetime.fromisoformat(str(row["created_at"])).astimezone(UTC),
                    summary=str(row["summary"]),
                    rationale=str(row["rationale"]),
                    alternatives=orjson.loads(str(row["alternatives_json"])),
                    impact=str(row["impact"]),
                    tags=orjson.loads(str(row["tags_json"])),
                )
            )
        return records
