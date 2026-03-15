"""Structured event logging for diagnostics and auditability."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import orjson


class EventLogger:
    def __init__(self, event_log_path: Path) -> None:
        self.event_log_path = event_log_path
        self.event_log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event_type: str, payload: dict[str, Any], level: str = "info") -> None:
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": level,
            "event_type": event_type,
            "payload": payload,
        }
        with self.event_log_path.open("ab") as fh:
            fh.write(orjson.dumps(record))
            fh.write(b"\n")
