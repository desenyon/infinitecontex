"""CLI for Infinite Context."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Annotated

import orjson
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
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


def _format_dict(d: dict[str, object], title: str) -> Panel:
    table = Table(show_header=False, box=None)
    table.add_column("Key", style="bold cyan")
    table.add_column("Value", style="none")
    for k, v in d.items():
        if isinstance(v, list) and not v:
            table.add_row(str(k), "[dim]None[/dim]")
        elif isinstance(v, list):
            table.add_row(str(k), "\n".join(f"- {item}" for item in v))
        else:
            table.add_row(str(k), str(v))
    return Panel(table, title=f"[bold]{title}[/bold]", border_style="blue", expand=False)


def _emit(payload: object, as_json: bool, format_type: str = "generic") -> None:
    if as_json:
        console.print(orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode())
        return

    if isinstance(payload, str):
        console.print(payload)
    elif isinstance(payload, dict):
        if format_type == "doctor":
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Check")
            table.add_column("Status")
            for k, v in payload.items():
                color = "green" if v == "ok" else "red"
                val_text = f"[{color}]{v}[/{color}]" if isinstance(v, str) else str(v)
                table.add_row(str(k).capitalize(), val_text)
            console.print(
                Panel(
                    table,
                    title="[bold]Doctor Diagnostics[/bold]",
                    title_align="left",
                    border_style="cyan",
                    expand=False,
                )
            )
        elif format_type == "status":
            console.print(_format_dict(payload, "Project Status"))
        elif format_type == "init":
            console.print(_format_dict(payload, "Initialization Status"))
        elif format_type == "snapshot":
            console.print(
                Panel(
                    f"[green]Snapshot created:[/green] {payload.get('id', 'unknown')}",
                    title="[bold]Snapshot[/bold]",
                    border_style="green",
                    expand=False,
                )
            )
        elif format_type == "config":
            console.print(_format_dict(payload, "Configuration"))
        elif format_type == "ingest_chat":
            console.print(_format_dict(payload, "Chat Ingestion Result"))
        elif format_type == "restore":
            console.print(_format_dict(payload, "Restore Report"))
        elif format_type == "diff_summary":
            diffs = payload.get("diff_summary", [])
            if not diffs:
                console.print("[dim]No recent diffs found.[/dim]")
            else:
                text = "\n".join(f"- {d}" for d in diffs)
                console.print(
                    Panel(text, title="[bold]Recent Diff Summary[/bold]", border_style="yellow", expand=False)
                )
        else:
            console.print(_format_dict(payload, "Result"))
    elif isinstance(payload, list):
        if format_type == "decisions":
            if not payload:
                console.print("[dim]No decisions found.[/dim]")
            else:
                table = Table(show_header=True, header_style="bold blue")
                table.add_column("ID", style="cyan")
                table.add_column("Summary")
                table.add_column("Date")
                for item in payload:
                    created_str = (
                        item.get("created_at", "")[:10]
                        if isinstance(item, dict) and "created_at" in item
                        else ""
                    )
                    table.add_row(item.get("id", ""), item.get("summary", ""), created_str)
                console.print(Panel(table, title="[bold]Recent Decisions[/bold]", expand=False, border_style="blue"))
        elif format_type == "search":
            if not payload:
                console.print("[dim]No results found.[/dim]")
            else:
                for idx, item in enumerate(payload):
                    title_str = (
                        f"[bold cyan]Result {idx+1}[/bold cyan] | "
                        f"{item.get('source_type', '')} - {item.get('source_id', '')}"
                    )
                    p = Panel(
                        item.get("content", ""),
                        title=title_str,
                        border_style="magenta",
                    )
                    console.print(p)
        else:
            for item in payload:
                console.print(item)
    else:
        console.print(payload)


@app.command()
def init(
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    out = _service(project_root).init()
    _emit(out, json, "init")


@app.command()
def snapshot(
    goal: Annotated[str, typer.Option("--goal", help="Current developer goal")] = "",
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    snap = _service(project_root).snapshot(goal=goal)
    _emit(snap.model_dump(mode="json"), json, "snapshot")


@app.command()
def restore(
    snapshot_id: Annotated[str | None, typer.Option("--snapshot-id")] = None,
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    out = _service(project_root).restore(snapshot_id=snapshot_id)
    _emit(out, json, "restore")


@app.command()
def status(
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    out = _service(project_root).status()
    _emit(out, json, "status")


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
    _emit(out, json, "ingest_chat")


@app.command("diff-summary")
def diff_summary(
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    out = _service(project_root).diff_summary()
    _emit({"diff_summary": out}, json, "diff_summary")


@app.command()
def decisions(
    limit: Annotated[int, typer.Option("--limit")] = 20,
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    out = _service(project_root).decisions_recent(limit)
    _emit(out, json, "decisions")


@app.command()
def search(
    query: Annotated[str, typer.Option("--query")],
    limit: Annotated[int, typer.Option("--limit")] = 10,
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    out = _service(project_root).search(query, limit)
    _emit(out, json, "search")


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
    _emit(out, json, "doctor")


@app.command()
def config(
    set_file: Annotated[Path | None, typer.Option("--set-file")] = None,
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    svc = _service(project_root)
    if set_file:
        try:
            cfg = AppConfig.model_validate(orjson.loads(set_file.read_bytes()))
            svc.config_set(cfg)
            console.print(
                Panel("[green]Configuration updated successfully[/green]", border_style="green", expand=False)
            )
        except FileNotFoundError:
            console.print(
                Panel(
                    f"[red]Error:[/red] The configuration file '{set_file}' was not found.",
                    title="Error",
                    border_style="red",
                    expand=False,
                )
            )
            raise typer.Exit(1)
        except Exception as e:
            console.print(
                Panel(
                    f"[red]Error:[/red] Failed to load configuration: {e}",
                    title="Error",
                    border_style="red",
                    expand=False,
                )
            )
            raise typer.Exit(1)
        return

    out = svc.config_get()
    _emit(out, json, "config")


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
