"""CLI for Infinite Context."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Annotated

import orjson
import typer
from rich.console import Console
from watchfiles import watch

from infinitecontex.core.config import AppConfig
from infinitecontex.core.models import PromptMode
from infinitecontex.service import InfiniteContextService
from infinitecontex.version import __version__

app = typer.Typer(help="Infinite Context: local-first project memory engine", invoke_without_command=True)
console = Console()


@app.callback()
def main(
    ctx: typer.Context,
    version: Annotated[bool, typer.Option("--version", help="Show version and exit")] = False,
) -> None:
    if version:
        console.print(f"infinitecontex {__version__}")
        raise typer.Exit(0)
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)


def _service(project_root: Path | None) -> InfiniteContextService:
    return InfiniteContextService((project_root or Path.cwd()).resolve())


def _emit(payload: object, as_json: bool) -> None:
    if as_json:
        console.print(orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode())
    else:
        if isinstance(payload, str):
            console.print(payload)
        else:
            console.print(payload)


@app.command()
def init(
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    out = _service(project_root).init()
    _emit(out, json)


@app.command()
def snapshot(
    goal: Annotated[str, typer.Option("--goal", help="Current developer goal")] = "",
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    snap = _service(project_root).snapshot(goal=goal)
    _emit(snap.model_dump(mode="json"), json)


@app.command()
def restore(
    snapshot_id: Annotated[str | None, typer.Option("--snapshot-id")] = None,
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    out = _service(project_root).restore(snapshot_id=snapshot_id)
    _emit(out, json)


@app.command()
def status(
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    out = _service(project_root).status()
    _emit(out, json)


@app.command()
def note(
    summary: Annotated[str, typer.Option("--summary")],
    rationale: Annotated[str, typer.Option("--rationale")],
    alternatives: Annotated[list[str] | None, typer.Option("--alternative")] = None,
    impact: Annotated[str, typer.Option("--impact")] = "",
    tags: Annotated[list[str] | None, typer.Option("--tag")] = None,
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
) -> None:
    decision_id = _service(project_root).note(summary, rationale, alternatives or [], impact, tags or [])
    console.print(f"saved decision: {decision_id}")


@app.command()
def pin(
    path: Annotated[str, typer.Option("--path")],
    note: Annotated[str, typer.Option("--note")] = "",
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
) -> None:
    _service(project_root).pin(path, note)
    console.print(f"pinned: {path}")


@app.command("ingest-chat")
def ingest_chat(
    chat_file: Annotated[Path, typer.Option("--file")],
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    out = _service(project_root).ingest_chat(chat_file)
    _emit(out, json)


@app.command("diff-summary")
def diff_summary(
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    out = _service(project_root).diff_summary()
    _emit({"diff_summary": out}, json)


@app.command()
def decisions(
    limit: Annotated[int, typer.Option("--limit")] = 20,
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    out = _service(project_root).decisions_recent(limit)
    _emit(out, json)


@app.command()
def search(
    query: Annotated[str, typer.Option("--query")],
    limit: Annotated[int, typer.Option("--limit")] = 10,
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    out = _service(project_root).search(query, limit)
    _emit(out, json)


@app.command()
def prompt(
    mode: Annotated[PromptMode, typer.Option("--mode")] = PromptMode.GENERIC_AGENT_RESTORE,
    token_budget: Annotated[int, typer.Option("--token-budget")] = 1200,
    snapshot_id: Annotated[str | None, typer.Option("--snapshot-id")] = None,
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
) -> None:
    out = _service(project_root).prompt(mode, token_budget, snapshot_id)
    console.print(out)


@app.command()
def export(
    output: Annotated[Path, typer.Option("--output")],
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
) -> None:
    out = _service(project_root).export(output)
    console.print(str(out))


@app.command("import")
def import_cmd(
    archive: Annotated[Path, typer.Option("--archive")],
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
) -> None:
    _service(project_root).import_archive(archive)
    console.print("import complete")


@app.command()
def doctor(
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    out = _service(project_root).doctor()
    _emit(out, json)


@app.command()
def config(
    set_file: Annotated[Path | None, typer.Option("--set-file")] = None,
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    svc = _service(project_root)
    if set_file:
        cfg = AppConfig.model_validate(orjson.loads(set_file.read_bytes()))
        svc.config_set(cfg)
        console.print("config updated")
        return

    out = svc.config_get()
    _emit(out, json)


@app.command("watch")
def watch_loop(
    goal: Annotated[str, typer.Option("--goal", help="Goal used for auto snapshots")] = "",
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    debounce_ms: Annotated[int, typer.Option("--debounce-ms")] = 1200,
    min_interval_sec: Annotated[int, typer.Option("--min-interval-sec")] = 3,
) -> None:
    svc = _service(project_root)
    root = (project_root or Path.cwd()).resolve()
    svc.init()
    console.print(f"watching {root} for changes...")
    last_snapshot_ts = 0.0
    for _changes in watch(root, debounce=debounce_ms):
        now = time.time()
        if now - last_snapshot_ts < min_interval_sec:
            continue
        snap = svc.snapshot(goal=goal)
        last_snapshot_ts = now
        console.print(f"snapshot updated: {snap.id}")
