# Infinite Context

Infinite Context is a local-first, agent-ready project memory engine for serious software repositories.

It turns repo structure, behavioral hints, developer intent, and active working state into compact, durable handoff artifacts that survive editor changes, branch switches, machine hops, and agent restarts.

## What You Get

Once initialized, the repository maintains a canonical handoff file that another coding agent can open and immediately understand:

- what the project is
- what changed recently
- what decisions were made
- what files matter now
- what to do next

Canonical handoff artifacts:

- `.infctx/project/inside.infinite_context.md`
- `.infctx/project/inside.infinite_context.json`

These are regenerated on snapshot and continuously refreshed in watch mode.

## Why It Matters

- AI coding sessions lose context too easily.
- Raw chat history is expensive, noisy, and brittle.
- Teams need low-token, deterministic, portable context restoration.

Infinite Context compiles context instead of dumping it.

## Install

UV-first workflow:

```bash
uv sync --extra dev
```

Run commands through UV:

```bash
uv run infctx --help
```

Fallback virtualenv workflow:

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

## Quick Start

```bash
uv run infctx init
uv run infctx snapshot --goal "stabilize parser performance"
uv run infctx status --json
uv run infctx prompt --mode generic-agent-restore --token-budget 1200
```

## Continuous Context Updates

Keep the project handoff current while you work:

```bash
uv run infctx watch --goal "active development" --debounce-ms 1200
```

This is the recommended default operational mode for active repositories.

## Agent Workflow

1. Open `.infctx/project/inside.infinite_context.md`.
2. Inspect the latest generated prompt in `.infctx/prompts/` if deeper restore context is needed.
3. Continue from the recorded next action and active files.

## Core Capabilities

- Local-first state storage under `.infctx/`
- Token-budgeted prompt compilation
- Config-aware scanning with include and exclude rules
- Decision memory and pinning
- Restore divergence checks for stale, changed, missing, and valid state
- SQLite-backed metadata and retrieval index
- Structured event logging and doctor diagnostics
- Background watch mode for iterative refresh on save

## Commands

- `uv run infctx init`
- `uv run infctx snapshot`
- `uv run infctx restore`
- `uv run infctx status`
- `uv run infctx prompt`
- `uv run infctx search`
- `uv run infctx decisions`
- `uv run infctx note`
- `uv run infctx pin`
- `uv run infctx ingest-chat`
- `uv run infctx export`
- `uv run infctx import`
- `uv run infctx doctor`
- `uv run infctx config`
- `uv run infctx watch`

## Configuration

Apply the repo-local default config:

```bash
uv run infctx config --set-file config/default.json
```

Most important controls:

- `capture_max_files`
- `include_patterns`
- `exclude_patterns`
- token, summarization, and privacy policy blocks

## Validation

```bash
uv sync --extra dev
uv run ruff check .
uv run mypy src
uv run pytest -q
uv run python -m build
```

## Documentation

See `docs/` for architecture, storage, restore semantics, CLI contract, testing strategy, observability, and release policy.
