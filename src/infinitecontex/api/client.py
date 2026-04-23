"""Python library API surface."""

from __future__ import annotations

from pathlib import Path

from infinitecontex.core.config import AppConfig
from infinitecontex.core.models import PinRecord, PromptMode, Snapshot, SnapshotComparison, SnapshotSummary
from infinitecontex.service import InfiniteContextService


class InfiniteContextClient:
    def __init__(self, project_root: str | Path = ".") -> None:
        self.service = InfiniteContextService(Path(project_root).resolve())

    def init(self) -> dict[str, str]:
        return self.service.init()

    def snapshot(self, goal: str = "") -> Snapshot:
        return self.service.snapshot(goal=goal)

    def restore(self, snapshot_id: str | None = None) -> dict[str, object]:
        return self.service.restore(snapshot_id)

    def status(self) -> dict[str, object]:
        return self.service.status()

    def note(
        self,
        summary: str,
        rationale: str,
        alternatives: list[str] | None = None,
        impact: str = "",
        tags: list[str] | None = None,
    ) -> str:
        return self.service.note(summary, rationale, alternatives or [], impact, tags or [])

    def pin(self, path: str, note: str) -> None:
        self.service.pin(path, note)

    def pins(self) -> list[PinRecord]:
        return self.service.pin_records()

    def unpin(self, path: str) -> bool:
        return self.service.unpin(path)

    def ingest_chat(self, chat_path: str | Path) -> dict[str, object]:
        return self.service.ingest_chat(Path(chat_path))

    def diff_summary(self) -> list[str]:
        return self.service.diff_summary()

    def snapshots(self, limit: int = 20) -> list[SnapshotSummary]:
        return self.service.snapshots_recent(limit)

    def show_snapshot(self, snapshot_id: str | None = None) -> dict[str, object]:
        return self.service.snapshot_details(snapshot_id)

    def compare_snapshots(
        self, from_snapshot_id: str | None = None, to_snapshot_id: str | None = None
    ) -> SnapshotComparison:
        return self.service.compare_snapshots(from_snapshot_id, to_snapshot_id)

    def decisions(self, limit: int = 20) -> list[dict[str, object]]:
        return self.service.decisions_recent(limit)

    def search(self, query: str, limit: int = 10) -> list[dict[str, object]]:
        return self.service.search(query, limit)

    def prompt(self, mode: PromptMode, token_budget: int = 1200, snapshot_id: str | None = None) -> str:
        return self.service.prompt(mode, token_budget, snapshot_id)

    def export(self, output: str | Path) -> Path:
        return self.service.export(Path(output))

    def import_archive(self, archive: str | Path) -> None:
        self.service.import_archive(Path(archive))

    def doctor(self) -> dict[str, str]:
        return self.service.doctor()

    def get_config(self) -> dict[str, object]:
        return self.service.config_get()

    def set_config(self, config: AppConfig) -> None:
        self.service.config_set(config)
