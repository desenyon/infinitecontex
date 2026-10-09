"""Offline CLI smoke test using only a disposable repository and synthetic data."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="infctx-smoke-") as temporary:
        root = Path(temporary)
        repo = root / "repo"
        repo.mkdir()
        (repo / "app.py").write_text("def run():\n    return 1\n")
        (repo / ".gitignore").write_text(".infctx*\n")
        for args in [
            ["init"],
            ["config", "user.name", "Smoke Test"],
            ["config", "user.email", "smoke@example.invalid"],
            ["add", "."],
            ["commit", "-m", "baseline"],
        ]:
            subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)

        def cli(*args: str, project: Path = repo) -> str:
            result = subprocess.run(
                [sys.executable, "-m", "infinitecontex", "--project-root", str(project), *args],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout

        def payload(*args: str, project: Path = repo) -> Any:
            return json.loads(cli(*args, "--json", project=project))

        assert payload("init")["status"] == "initialized"
        transcript = root / "chat.txt"
        transcript.write_text("goal: smokemarker\ntask: verify storage\n")
        assert payload("ingest-chat", "--file", str(transcript))["persisted"] is False
        config = root / "config.json"
        config.write_text(json.dumps({"policies": {"privacy": {"persist_chat_ingest": True}}}))
        cli("config", "--set-file", str(config))
        assert payload("ingest-chat", "--file", str(transcript))["persisted"] is True
        first = payload("snapshot", "--goal", "baseline")
        (repo / "app.py").write_text("def run():\n    return 2\n")
        subprocess.run(["git", "add", "app.py"], cwd=repo, check=True)
        second = payload("snapshot", "--goal", "smokemarker")
        assert "app.py" in payload("compare-snapshots")["changed_tracked_files"]
        assert "app.py" in payload("restore", "--snapshot-id", first["id"])["changed_items"]
        assert "Restore Brief" in cli("prompt", "--mode", "human-handoff")
        assert payload("search", "--query", "smokemarker")
        cli("cleanup", "--keep", "1", "--yes")
        assert len(payload("snapshots")) == 1
        # Simulate lost derived data; canonical metadata must still serve reads.
        (repo / ".infctx" / "snapshots" / f"{second['id']}.json").unlink()
        assert payload("show-snapshot")["id"] == second["id"]
        assert payload("repair")["status"] == "repaired"
        archive = root / "state.tgz"
        cli("export", "--output", str(archive))
        imported = root / "imported"
        imported.mkdir()
        cli("import", "--archive", str(archive), project=imported)
        assert payload("show-snapshot", project=imported)["id"] == second["id"]
        health = payload("doctor", project=imported)
        assert all(health[key] == "ok" for key in ["sqlite", "snapshots", "artifacts", "recovery", "search"])
        print(
            "Offline CLI smoke passed: capture, privacy, staged Git, compare, restore, cleanup, repair, export/import."
        )


if __name__ == "__main__":
    main()
