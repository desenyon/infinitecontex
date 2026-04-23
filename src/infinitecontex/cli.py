"""CLI for Infinite Context."""

from __future__ import annotations

import fnmatch
import time
from pathlib import Path
from typing import Annotated, Callable

import orjson
import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table
from watchfiles import Change, watch

from infinitecontex.core.config import AppConfig, load_app_config
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


def _print_error(message: str) -> None:
    console.print(Panel(message, title="Error", border_style="red", expand=False))


def _run_action(
    callback: Callable[[], object],
    *,
    as_json: bool = False,
    format_type: str = "generic",
    progress_message: str | None = None,
    emit: bool = True,
) -> object:
    try:
        if progress_message:
            with console.status(progress_message):
                payload = callback()
        else:
            payload = callback()
    except Exception as exc:
        _print_error(str(exc))
        raise typer.Exit(1) from exc

    if emit:
        _emit(payload, as_json, format_type)
    return payload


def _matches_pattern(rel_path: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        if pattern.endswith("/**"):
            prefix = pattern[: -len("/**")].rstrip("/")
            if rel_path == prefix or rel_path.startswith(prefix + "/"):
                return True
        if pattern.startswith("**/") and fnmatch.fnmatch(rel_path, pattern[3:]):
            return True
        if fnmatch.fnmatch(rel_path, pattern):
            return True
    return False


def _filter_watch_changes(changes: set[tuple[Change, str]], root: Path, exclude_patterns: list[str]) -> list[str]:
    relevant: list[str] = []
    for _, changed_path in changes:
        try:
            rel_path = Path(changed_path).resolve().relative_to(root).as_posix()
        except Exception:
            continue
        if _matches_pattern(rel_path, exclude_patterns):
            continue
        if rel_path not in relevant:
            relevant.append(rel_path)
    return sorted(relevant)[:12]


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
            from rich.columns import Columns

            latest = payload.get("latest_snapshot") or "None"
            latest_created_at = payload.get("latest_snapshot_created_at") or "None"
            snapshot_count = payload.get("snapshot_count", 0)
            branch = payload.get("branch", "unknown")
            root_dir = payload.get("project_root", "")
            pins = payload.get("pins", [])
            commits = payload.get("recent_commits", [])
            developer_goal = payload.get("developer_goal") or "None"
            active_tasks = payload.get("active_tasks", [])
            unresolved = payload.get("unresolved_issues", [])

            dash_table = Table.grid(padding=1)
            dash_table.add_column(style="bold cyan", justify="right")
            dash_table.add_column(style="white")
            dash_table.add_row("Root:", str(root_dir))
            dash_table.add_row("Branch:", f"[green]{branch}[/green]")
            dash_table.add_row("Memory:", f"[magenta]{latest}[/magenta]")
            dash_table.add_row("Captured:", str(latest_created_at))
            dash_table.add_row("Snapshots:", str(snapshot_count))
            dash_table.add_row("Goal:", str(developer_goal))

            pin_text = "\n".join(f"• {p}" for p in pins) if pins else "[dim]No active pins.[/dim]"
            commit_text = "\n".join(f"• {c}" for c in commits) if commits else "[dim]No recent commits.[/dim]"
            task_text = (
                "\n".join(f"• {item}" for item in active_tasks)
                if active_tasks
                else "[dim]No active tasks.[/dim]"
            )
            issue_text = "\n".join(f"• {item}" for item in unresolved) if unresolved else "[dim]No open issues.[/dim]"

            cols = Columns(
                [
                    Panel(dash_table, title="[bold]Overview[/bold]", border_style="blue", padding=(1, 2)),
                    Panel(
                        pin_text,
                        title="[bold yellow]Pinned Context[/bold yellow]",
                        border_style="yellow",
                        padding=(1, 2),
                    ),
                    Panel(
                        task_text,
                        title="[bold green]Active Tasks[/bold green]",
                        border_style="green",
                        padding=(1, 2),
                    ),
                    Panel(
                        commit_text,
                        title="[bold magenta]Recent Commits[/bold magenta]",
                        border_style="magenta",
                        padding=(1, 2),
                    ),
                    Panel(
                        issue_text,
                        title="[bold red]Open Issues[/bold red]",
                        border_style="red",
                        padding=(1, 2),
                    ),
                ],
                expand=True,
                equal=True,
            )

            console.print(Panel(cols, title="[bold]Infinite Context Dashboard[/bold]", border_style="cyan", padding=1))

        elif format_type == "init":
            console.print(_format_dict(payload, "Initialization Status"))
        elif format_type == "snapshot":
            console.print(
                Panel(
                    f"[green]Snapshot created:[/green] {payload.get('id', 'unknown')}\n\n"
                    "[dim]Artifacts updated in .infctx/agents/[/dim]",
                    title="[bold]Snapshot[/bold]",
                    border_style="green",
                    expand=False,
                )
            )
        elif format_type == "config":
            console.print(_format_dict(payload, "Configuration"))
        elif format_type == "ingest_chat":
            summary = {
                "developer_goal": payload.get("developer_goal", ""),
                "active_tasks": payload.get("active_tasks", []),
                "decisions": payload.get("decisions", []),
                "unresolved_issues": payload.get("unresolved_issues", []),
                "selected_source": payload.get("selected_source"),
                "selected_path": payload.get("selected_path"),
            }
            console.print(_format_dict(summary, "Chat Ingestion Result"))
        elif format_type == "session":
            console.print(_format_dict(payload, "Session Capture"))
        elif format_type == "restore":
            console.print(_format_dict(payload, "Restore Report"))
        elif format_type == "snapshot_detail":
            from rich.columns import Columns

            overview = Table.grid(padding=1)
            overview.add_column(style="bold cyan", justify="right")
            overview.add_column(style="white")
            overview.add_row("Snapshot:", str(payload.get("id", "")))
            overview.add_row("Created:", str(payload.get("created_at", "")))
            overview.add_row("Branch:", str(payload.get("working_set", {}).get("branch", "")))
            overview.add_row("Goal:", str(payload.get("intent", {}).get("developer_goal", "") or "None"))
            overview.add_row("Prompt:", str(payload.get("prompt_path", "")))

            metrics = payload.get("metrics", {})
            metrics_text = "\n".join(f"• {key}: {value}" for key, value in metrics.items()) or "[dim]No metrics[/dim]"
            tasks = payload.get("intent", {}).get("active_tasks", [])
            issues = payload.get("intent", {}).get("unresolved_issues", [])
            active_files = payload.get("working_set", {}).get("active_files", [])

            cols = Columns(
                [
                    Panel(overview, title="[bold]Overview[/bold]", border_style="blue", padding=(1, 2)),
                    Panel(metrics_text, title="[bold green]Metrics[/bold green]", border_style="green", padding=(1, 2)),
                    Panel(
                        "\n".join(f"• {item}" for item in tasks) or "[dim]No active tasks.[/dim]",
                        title="[bold yellow]Tasks[/bold yellow]",
                        border_style="yellow",
                        padding=(1, 2),
                    ),
                    Panel(
                        "\n".join(f"• {item}" for item in issues) or "[dim]No unresolved issues.[/dim]",
                        title="[bold red]Issues[/bold red]",
                        border_style="red",
                        padding=(1, 2),
                    ),
                    Panel(
                        "\n".join(f"• {item}" for item in active_files) or "[dim]No active files.[/dim]",
                        title="[bold magenta]Active Files[/bold magenta]",
                        border_style="magenta",
                        padding=(1, 2),
                    ),
                ],
                expand=True,
                equal=True,
            )
            console.print(Panel(cols, title="[bold]Snapshot Details[/bold]", border_style="cyan", padding=1))
        elif format_type == "snapshot_compare":
            from rich.columns import Columns

            header = Table.grid(padding=1)
            header.add_column(style="bold cyan", justify="right")
            header.add_column(style="white")
            header.add_row("From:", str(payload.get("from_snapshot_id", "")))
            header.add_row("To:", str(payload.get("to_snapshot_id", "")))
            goals_text = f"{payload.get('from_goal', '') or 'None'} -> {payload.get('to_goal', '') or 'None'}"
            header.add_row("Goals:", goals_text)
            header.add_row(
                "Branches:",
                f"{payload.get('from_branch', '') or 'unknown'} -> {payload.get('to_branch', '') or 'unknown'}",
            )
            header.add_row("Summary:", str(payload.get("summary", "")))

            metric_deltas = payload.get("metric_deltas", {})
            metrics_text = "\n".join(f"• {key}: {value:+g}" for key, value in metric_deltas.items())
            if not metrics_text:
                metrics_text = "[dim]No metric deltas.[/dim]"

            def _bullet_block(key: str, empty_text: str) -> str:
                values = payload.get(key, [])
                return "\n".join(f"• {item}" for item in values) if values else f"[dim]{empty_text}[/dim]"

            cols = Columns(
                [
                    Panel(header, title="[bold]Overview[/bold]", border_style="blue", padding=(1, 2)),
                    Panel(
                        metrics_text,
                        title="[bold green]Metric Deltas[/bold green]",
                        border_style="green",
                        padding=(1, 2),
                    ),
                    Panel(
                        _bullet_block("changed_tracked_files", "No tracked file changes."),
                        title="[bold magenta]Changed Files[/bold magenta]",
                        border_style="magenta",
                        padding=(1, 2),
                    ),
                    Panel(
                        _bullet_block("added_tasks", "No new tasks.")
                        + "\n\n"
                        + _bullet_block("removed_tasks", "No removed tasks."),
                        title="[bold yellow]Task Changes[/bold yellow]",
                        border_style="yellow",
                        padding=(1, 2),
                    ),
                    Panel(
                        _bullet_block("added_issues", "No new issues.")
                        + "\n\n"
                        + _bullet_block("removed_issues", "No removed issues."),
                        title="[bold red]Issue Changes[/bold red]",
                        border_style="red",
                        padding=(1, 2),
                    ),
                ],
                expand=True,
                equal=True,
            )
            console.print(Panel(cols, title="[bold]Snapshot Comparison[/bold]", border_style="cyan", padding=1))
        elif format_type == "diff_summary":
            diffs = payload.get("diff_summary", [])
            if not diffs:
                console.print("[dim]No recent diffs. Workspace is clean.[/dim]")
            else:
                from rich.syntax import Syntax

                text = "\n".join(f"- {d}" for d in diffs)
                console.print(
                    Panel(
                        Syntax(text, "markdown"),
                        title="[bold]Workspace Uncommitted Changes[/bold]",
                        border_style="yellow",
                        padding=(1, 2),
                    )
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
                        item.get("created_at", "")[:10] if isinstance(item, dict) and "created_at" in item else ""
                    )
                    table.add_row(item.get("id", ""), item.get("summary", ""), created_str)
                console.print(Panel(table, title="[bold]Recent Decisions[/bold]", expand=False, border_style="blue"))
        elif format_type == "snapshots":
            if not payload:
                console.print("[dim]No snapshots found.[/dim]")
            else:
                table = Table(show_header=True, header_style="bold cyan")
                table.add_column("ID", style="magenta")
                table.add_column("Created")
                table.add_column("Goal")
                table.add_column("Branch")
                table.add_column("Files", justify="right")
                table.add_column("Tasks", justify="right")
                for item in payload:
                    table.add_row(
                        item.get("id", ""),
                        item.get("created_at", "")[:19],
                        item.get("developer_goal", "") or "None",
                        item.get("branch", ""),
                        str(item.get("file_count", 0)),
                        str(item.get("active_task_count", 0)),
                    )
                console.print(Panel(table, title="[bold]Snapshot History[/bold]", expand=False, border_style="cyan"))
        elif format_type == "pins":
            if not payload:
                console.print("[dim]No pins found.[/dim]")
            else:
                table = Table(show_header=True, header_style="bold yellow")
                table.add_column("Path", style="cyan")
                table.add_column("Note")
                table.add_column("Created")
                for item in payload:
                    table.add_row(
                        item.get("path", ""),
                        item.get("note", ""),
                        item.get("created_at", "")[:19],
                    )
                console.print(Panel(table, title="[bold]Pinned Context[/bold]", expand=False, border_style="yellow"))
        elif format_type == "search":
            if not payload:
                console.print("[dim]No results found.[/dim]")
            else:
                for idx, item in enumerate(payload):
                    title_str = (
                        f"[bold cyan]Result {idx + 1}[/bold cyan] | "
                        f"{item.get('source', '')} - {item.get('key', '')}"
                    )
                    p = Panel(
                        item.get("snippet", ""),
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
    _run_action(lambda: _service(project_root).init(), as_json=json, format_type="init")


@app.command()
def snapshot(
    goal: Annotated[str, typer.Option("--goal", help="Current developer goal")] = "",
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    _run_action(
        lambda: _service(project_root).snapshot(goal=goal).model_dump(mode="json"),
        as_json=json,
        format_type="snapshot",
        progress_message="Capturing project context...",
    )


@app.command("snapshots")
def snapshots_cmd(
    limit: Annotated[int, typer.Option("--limit")] = 20,
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    _run_action(
        lambda: [item.model_dump(mode="json") for item in _service(project_root).snapshots_recent(limit)],
        as_json=json,
        format_type="snapshots",
    )


@app.command("show-snapshot")
def show_snapshot(
    snapshot_id: Annotated[str | None, typer.Option("--snapshot-id")] = None,
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    _run_action(
        lambda: _service(project_root).snapshot_details(snapshot_id=snapshot_id),
        as_json=json,
        format_type="snapshot_detail",
    )


@app.command("compare-snapshots")
def compare_snapshots(
    from_snapshot: Annotated[str | None, typer.Option("--from-snapshot")] = None,
    to_snapshot: Annotated[str | None, typer.Option("--to-snapshot")] = None,
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    _run_action(
        lambda: _service(project_root).compare_snapshots(
            from_snapshot_id=from_snapshot,
            to_snapshot_id=to_snapshot,
        ).model_dump(mode="json"),
        as_json=json,
        format_type="snapshot_compare",
    )


@app.command()
def restore(
    snapshot_id: Annotated[str | None, typer.Option("--snapshot-id")] = None,
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    _run_action(
        lambda: _service(project_root).restore(snapshot_id=snapshot_id),
        as_json=json,
        format_type="restore",
        progress_message="Validating restore state...",
    )


@app.command("setup-agent")
def setup_agent(
    agent: Annotated[str, typer.Argument(help="choose from: cursor, claude, copilot, windsurf")],
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
) -> None:
    """Wire IDE AI agents directly to Infinite Context memory."""
    root = (project_root or Path.cwd()).resolve()
    content = (
        "You are operating in a project managed by Infinite Context.\n"
        "To reliably understand the state of this repository, you MUST ALWAYS start by reading:\n"
        "`.infctx/agents/instructions.md`\n"
        "Do not guess context. Rely on the intelligent snapshot memory in `.infctx/agents/`.\n"
    )

    agent = agent.lower()
    if agent == "cursor":
        target = root / ".cursorrules"
    elif agent == "claude":
        target = root / "CLAUDE.md"
    elif agent == "windsurf":
        target = root / ".windsurfrules"
    elif agent == "copilot":
        target = root / ".github" / "copilot-instructions.md"
        target.parent.mkdir(parents=True, exist_ok=True)
    else:
        console.print(f"[red]Error:[/red] Unsupported agent '{agent}'.")
        raise typer.Exit(1)

    target.write_text(content, encoding="utf-8")
    console.print(f"[green]Successfully wired[/green] {agent} to Infinite Context via {target.relative_to(root)}")


@app.command()
def status(
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    _run_action(lambda: _service(project_root).status(), as_json=json, format_type="status")


@app.command()
def note(
    summary: Annotated[str, typer.Option("--summary")],
    rationale: Annotated[str, typer.Option("--rationale")],
    alternatives: Annotated[list[str] | None, typer.Option("--alternative")] = None,
    impact: Annotated[str, typer.Option("--impact")] = "",
    tags: Annotated[list[str] | None, typer.Option("--tag")] = None,
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
) -> None:
    decision_id = _run_action(
        lambda: _service(project_root).note(summary, rationale, alternatives or [], impact, tags or [])
    )
    console.print(Panel(f"Saved decision `{decision_id}`", border_style="green", expand=False))


@app.command()
def pin(
    path: Annotated[str, typer.Option("--path")],
    note: Annotated[str, typer.Option("--note")] = "",
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
) -> None:
    _run_action(lambda: _service(project_root).pin(path, note))
    console.print(Panel(f"Pinned `{path}`", border_style="green", expand=False))


@app.command()
def pins(
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    _run_action(
        lambda: [item.model_dump(mode="json") for item in _service(project_root).pin_records()],
        as_json=json,
        format_type="pins",
    )


@app.command()
def unpin(
    path: Annotated[str, typer.Option("--path")],
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
) -> None:
    removed = _run_action(lambda: _service(project_root).unpin(path), emit=False)
    if removed:
        console.print(Panel(f"Removed pin `{path}`", border_style="green", expand=False))
        return
    _print_error(f"No pin exists for `{path}`.")
    raise typer.Exit(1)


@app.command("ingest-chat")
def ingest_chat(
    chat_file: Annotated[Path | None, typer.Option("--file")] = None,
    auto: Annotated[bool, typer.Option("--auto", help="Auto-discover from Cursor/Copilot/Claude")] = False,
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    if not chat_file and not auto:
        _print_error("Must provide either `--file` or `--auto`.")
        raise typer.Exit(1)

    svc = _service(project_root)
    if auto:
        from infinitecontex.capture.chat_auto_discover import auto_ingest_chat

        context = _run_action(
            auto_ingest_chat,
            progress_message="Scanning local AI chat sources...",
            emit=False,
        )
        if not isinstance(context, dict):
            _print_error("Auto-discovery did not return a usable payload.")
            raise typer.Exit(1)
        if context.get("selected_source") is None:
            console.print("[yellow]No local chat source could be discovered.[/yellow]")
            return

        persistable_keys = {
            "developer_goal",
            "decisions",
            "assumptions",
            "active_tasks",
            "unresolved_issues",
            "open_questions",
            "signal_sources",
            "selected_source",
            "selected_path",
            "checked_sources",
        }
        out = svc.ingest_chat_payload({key: context.get(key) for key in [*persistable_keys, "source_text"]})
        _emit(out, json, "ingest_chat")
    else:
        if chat_file is None:
            raise typer.Exit(1)
        _run_action(
            lambda: svc.ingest_chat(chat_file),
            as_json=json,
            format_type="ingest_chat",
            progress_message="Ingesting chat transcript...",
        )


@app.command("diff-summary")
def diff_summary(
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    _run_action(
        lambda: {"diff_summary": _service(project_root).diff_summary()},
        as_json=json,
        format_type="diff_summary",
    )


@app.command()
def decisions(
    limit: Annotated[int, typer.Option("--limit")] = 20,
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    _run_action(lambda: _service(project_root).decisions_recent(limit), as_json=json, format_type="decisions")


@app.command()
def search(
    query: Annotated[str, typer.Option("--query")],
    limit: Annotated[int, typer.Option("--limit")] = 10,
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    _run_action(lambda: _service(project_root).search(query, limit), as_json=json, format_type="search")


@app.command()
def prompt(
    mode: Annotated[PromptMode, typer.Option("--mode")] = PromptMode.GENERIC_AGENT_RESTORE,
    token_budget: Annotated[int, typer.Option("--token-budget")] = 1200,
    snapshot_id: Annotated[str | None, typer.Option("--snapshot-id")] = None,
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
) -> None:
    _run_action(
        lambda: _service(project_root).prompt(mode, token_budget, snapshot_id),
        progress_message="Compiling handoff prompt...",
    )


@app.command()
def export(
    output: Annotated[Path, typer.Option("--output")],
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
) -> None:
    out = _run_action(lambda: _service(project_root).export(output), progress_message="Exporting local state...")
    console.print(Panel(f"Exported archive to `{out}`", border_style="green", expand=False))


@app.command("import")
def import_cmd(
    archive: Annotated[Path, typer.Option("--archive")],
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
) -> None:
    _run_action(lambda: _service(project_root).import_archive(archive), progress_message="Importing local state...")
    console.print(Panel("Import complete", border_style="green", expand=False))


@app.command()
def doctor(
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    _run_action(lambda: _service(project_root).doctor(), as_json=json, format_type="doctor")


@app.command()
def config(
    set_file: Annotated[Path | None, typer.Option("--set-file")] = None,
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    svc = _service(project_root)
    if set_file:
        resolved_set_file = set_file
        if not resolved_set_file.is_absolute() and project_root is not None:
            candidate = (project_root / resolved_set_file).resolve()
            if candidate.exists():
                resolved_set_file = candidate
        try:
            cfg = AppConfig.model_validate(orjson.loads(resolved_set_file.read_bytes()))
        except FileNotFoundError as exc:
            _print_error(f"The configuration file `{resolved_set_file}` was not found.")
            raise typer.Exit(1) from exc
        except Exception as exc:
            _print_error(f"Failed to load configuration: {exc}")
            raise typer.Exit(1) from exc
        _run_action(lambda: svc.config_set(cfg))
        console.print(Panel("Configuration updated successfully", border_style="green", expand=False))
        return

    _run_action(lambda: svc.config_get(), as_json=json, format_type="config")


@app.command()
def session(
    goal: Annotated[str, typer.Option("--goal", help="Goal used for structured session captures")] = "",
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    debounce_ms: Annotated[int, typer.Option("--debounce-ms")] = 1200,
    min_interval_sec: Annotated[int, typer.Option("--min-interval-sec")] = 3,
    once: Annotated[bool, typer.Option("--once", help="Capture the initial session snapshot and exit")] = False,
    json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    svc = _service(project_root)
    root = (project_root or Path.cwd()).resolve()
    cfg = load_app_config(root)
    svc.init()

    initial_snapshot = _run_action(
        lambda: svc.snapshot(goal=goal),
        progress_message="Starting structured session...",
        emit=False,
    )
    if not hasattr(initial_snapshot, "id"):
        _print_error("Failed to create the initial session snapshot.")
        raise typer.Exit(1)

    session_payload = {
        "project_root": str(root),
        "goal": getattr(initial_snapshot, "intent").developer_goal or goal,
        "snapshot_id": getattr(initial_snapshot, "id"),
        "changed_paths": [],
        "mode": "once" if once else "live",
    }
    if once:
        _emit(session_payload, json, "session")
        return
    if json:
        _print_error("`session --json` is only supported together with `--once`.")
        raise typer.Exit(1)

    import datetime

    from rich.align import Align

    exclude_patterns = list(dict.fromkeys([*cfg.exclude_patterns, ".infctx/**"]))
    session_goal = getattr(initial_snapshot, "intent").developer_goal or goal or "None"
    last_snapshot_id = getattr(initial_snapshot, "id")
    last_snapshot_ts = time.time()
    last_trigger = "initial snapshot"
    last_changed_paths: list[str] = []
    skipped_batches = 0

    def generate_dashboard() -> Panel:
        table = Table.grid(padding=(0, 2))
        table.add_column(style="cyan", justify="right")
        table.add_column(style="white")
        table.add_row("Root:", str(root))
        table.add_row("Goal:", f"[bold green]{session_goal}[/bold green]")
        table.add_row("Last Snapshot:", f"[bold magenta]{last_snapshot_id}[/bold magenta]")
        table.add_row("Last Trigger:", last_trigger)
        table.add_row("Skipped:", str(skipped_batches))
        table.add_row("Recent Changes:", "\n".join(last_changed_paths) if last_changed_paths else "[dim]Waiting[/dim]")
        table.add_row("Status:", Spinner("dots", text="[yellow]Watching filtered project changes...[/yellow]"))
        return Panel(
            Align.center(table),
            title=f"[bold]Infinite Context Session[/bold] • {datetime.datetime.now().strftime('%H:%M:%S')}",
            border_style="cyan",
        )

    with Live(generate_dashboard(), refresh_per_second=4) as live:
        for changes in watch(root, debounce=debounce_ms):
            relevant_changes = _filter_watch_changes(changes, root, exclude_patterns)
            if not relevant_changes:
                continue
            now = time.time()
            if now - last_snapshot_ts < min_interval_sec:
                skipped_batches += 1
                last_trigger = "cooldown skip"
                last_changed_paths = relevant_changes
                live.update(generate_dashboard())
                continue

            try:
                snap = svc.snapshot(goal=goal)
            except Exception as exc:
                skipped_batches += 1
                last_trigger = f"snapshot failed: {exc}"
                last_changed_paths = relevant_changes
                live.update(generate_dashboard())
                continue
            last_snapshot_ts = now
            last_snapshot_id = snap.id
            last_trigger = "file changes"
            last_changed_paths = relevant_changes
            live.update(generate_dashboard())


@app.command("watch")
def watch_loop(
    goal: Annotated[str, typer.Option("--goal", help="Goal used for auto snapshots")] = "",
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    debounce_ms: Annotated[int, typer.Option("--debounce-ms")] = 1200,
    min_interval_sec: Annotated[int, typer.Option("--min-interval-sec")] = 3,
) -> None:
    session(
        goal=goal,
        project_root=project_root,
        debounce_ms=debounce_ms,
        min_interval_sec=min_interval_sec,
        once=False,
        json=False,
    )


@app.command("cleanup")
def cleanup(
    keep: Annotated[int, typer.Option("--keep", help="Number of recent snapshots to keep")] = 10,
    project_root: Annotated[Path | None, typer.Option("--project-root")] = None,
    yes: Annotated[bool, typer.Option("--yes", help="Confirm deletion of old snapshots")] = False,
) -> None:
    """Prune old snapshots and compact the local memory database."""
    svc = _service(project_root)
    rows = svc.db.query("SELECT id FROM snapshots ORDER BY created_at DESC")
    if len(rows) <= keep:
        console.print(Panel(f"Only {len(rows)} snapshots exist. Kept all.", border_style="green", expand=False))
        return

    to_delete = [str(r["id"]) for r in rows[keep:]]
    if not yes:
        _print_error(f"Cleanup would remove {len(to_delete)} snapshots. Re-run with `--yes` to confirm.")
        raise typer.Exit(1)
    for snap_id in to_delete:
        svc.db.execute("DELETE FROM snapshots WHERE id = ?", (snap_id,))
        snap_file = svc.layout.snapshots / f"{snap_id}.json"
        if snap_file.exists():
            snap_file.unlink()

    svc.db.execute("VACUUM")
    console.print(Panel(f"Removed {len(to_delete)} old snapshots and compacted the database.", border_style="green"))
