from __future__ import annotations

from pathlib import Path

from infinitecontex.api.client import InfiniteContextClient
from infinitecontex.core.config import AppConfig
from infinitecontex.core.models import PromptMode


def test_client_surface_end_to_end(tmp_repo: Path, tmp_path: Path) -> None:
    client = InfiniteContextClient(tmp_repo)
    client.init()

    chat = tmp_path / "chat.txt"
    chat.write_text("goal: stabilize\ndecision: keep local\n", encoding="utf-8")

    snap = client.snapshot(goal="stabilize")
    client.note("Use sqlite", "Portable", ["duckdb"], "low risk", ["storage"])
    client.pin("app.py", "entry surface")
    client.ingest_chat(chat)
    history = client.snapshots(limit=5)

    assert client.diff_summary() is not None
    assert client.decisions(limit=10) is not None
    assert isinstance(client.search("sqlite", limit=5), list)
    assert history[0].id == snap.id

    shown = client.show_snapshot(snap.id)
    assert shown["id"] == snap.id

    prompt = client.prompt(PromptMode.GENERIC_AGENT_RESTORE, token_budget=900, snapshot_id=snap.id)
    assert "Project Card" in prompt

    report = client.restore(snap.id)
    assert report["snapshot_id"] == snap.id

    archive = tmp_path / "state.tgz"
    assert client.export(archive).exists()

    repo2 = tmp_path / "repo2"
    repo2.mkdir()
    client2 = InfiniteContextClient(repo2)
    client2.import_archive(archive)
    assert (repo2 / ".infctx").exists()

    cfg = AppConfig(project_name="demo")
    client.set_config(cfg)
    loaded = client.get_config()
    assert loaded["project_name"] == "demo"
    assert client.pins()[0].path == "app.py"
    assert client.unpin("app.py") is True
    assert client.doctor()["sqlite"] == "ok"
