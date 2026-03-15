# Infinite Context

Infinite Context is a local-first project memory engine for software teams using AI coding agents.

It continuously compiles repo structure, behavior, intent, and active working state into compact context artifacts that can be restored quickly on any machine, branch, IDE, or agent.

## Why It Exists

- AI coding sessions lose critical context between machines and tools.
- Raw chat logs are noisy, expensive, and fragile.
- Developers need deterministic, low-token, portable context handoff.

## Core Outcome

After initialization, any agent can read one canonical file and know exactly:

- what this project is,
- where work stopped,
- what changed recently,
- what to do next.

Canonical handoff file:

- `.infctx/project/inside.infinite_context.md`
- `.infctx/project/inside.infinite_context.json`

These files are regenerated on each snapshot and are designed for direct agent consumption.

## Install (UV-first)

```bash
uv venv
uv sync --extra dev
```

Alternative:

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

## Quick Start

```bash
infctx init
infctx snapshot --goal "stabilize parser performance"
infctx status --json
infctx prompt --mode generic-agent-restore --token-budget 1200
```

## Continuous Updates

Run watch mode to update snapshots automatically while you work:

```bash
infctx watch --goal "active development" --debounce-ms 1200
```

This keeps handoff files current whenever files are saved.

## Recommended Agent Flow

1. Agent reads `.infctx/project/inside.infinite_context.md`
2. Agent reviews latest prompt in `.infctx/prompts/`
3. Agent executes next action from handoff file

## Production Features

- Local-first by default (no silent uploads)
- Token-budgeted prompt compilation
- Config-aware include/exclude scanning
- Decision and pin memory
- Restore divergence checks (stale/missing/changed/valid)
- FTS retrieval index over snapshots and ingested context
- Structured diagnostics via `infctx doctor`

## Configuration

Set repo config:

```bash
infctx config --set-file config/default.json
```

Key controls:

- `include_patterns`
- `exclude_patterns`
- token/summarization/privacy policy blocks

## Commands

- `infctx init`
- `infctx snapshot`
- `infctx restore`
- `infctx status`
- `infctx prompt`
- `infctx search`
- `infctx decisions`
- `infctx note`
- `infctx pin`
- `infctx ingest-chat`
- `infctx export`
- `infctx import`
- `infctx doctor`
- `infctx config`
- `infctx watch`

## Documentation

See `docs/` for architecture, data model, storage layout, restore behavior, security model, testing, and release policy.
