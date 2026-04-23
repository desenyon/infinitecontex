"""Restore validation and divergence reporting."""

from __future__ import annotations

import hashlib
from pathlib import Path

from infinitecontex.capture.git_state import current_branch
from infinitecontex.core.models import RestoreReport, Snapshot


def _file_sha1(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def validate_restore(snapshot: Snapshot, project_root: Path) -> RestoreReport:
    stale_items: list[str] = []
    missing_items: list[str] = []
    changed_items: list[str] = []
    valid_items: list[str] = []

    now_branch = current_branch(project_root)
    if snapshot.working_set.branch != now_branch:
        stale_items.append(f"branch changed: {snapshot.working_set.branch} -> {now_branch}")

    tracked = {fp.path: fp for fp in snapshot.fingerprints}

    for rel, fp in tracked.items():
        path = project_root / rel
        if not path.exists():
            missing_items.append(rel)
            continue
        stat = path.stat()
        if stat.st_size != fp.size or _file_sha1(path) != fp.sha1:
            changed_items.append(rel)
        else:
            valid_items.append(rel)

    summary = (
        f"stale={len(stale_items)} missing={len(missing_items)} changed={len(changed_items)} valid={len(valid_items)}"
    )

    return RestoreReport(
        snapshot_id=snapshot.id,
        stale_items=stale_items,
        missing_items=missing_items,
        changed_items=changed_items[:100],
        still_valid_items=valid_items[:100],
        summary=summary,
    )
