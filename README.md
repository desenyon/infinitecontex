# Infinite Context

`infinitecontex` is a local-first project memory CLI for coding workflows. It captures a balanced view of the repo, current git state, runtime failures, and developer intent, then turns that into snapshots, handoff files, restore prompts, and inspectable memory history.

Version: `0.3.0`

## What Changed In 0.3.0

- Added snapshot history, snapshot inspection, and snapshot-to-snapshot diff workflows.
- Added first-class pin management with `pins` and `unpin`.
- Expanded `status` to report memory volume and latest capture timestamps.
- Hardened restore and import integrity checks.
- Updated the Python API and docs to match the larger memory-management surface.

## Install

Requirements:

- Python `3.11+`
- [uv](https://docs.astral.sh/uv/) recommended

### Install the CLI with `uv`

Use `uv tool install` for a global CLI install:

```bash
uv tool install infinitecontex
infctx --version
```

Upgrade later with:

```bash
uv tool upgrade infinitecontex
```

If the executable already exists locally, reinstall with:

```bash
uv tool install --force infinitecontex
```

### Run from source during development

From the repository root:

```bash
uv sync --extra dev
uv run infctx --version
uv run infctx --help
```

### One-off run without installing globally

```bash
uv tool run --from infinitecontex infctx --version
```

## Quick Start

Run these commands from the repository root you want to snapshot.

```bash
# Initialize once per repo
uv run infctx init

# Optional: apply the included Python-oriented preset
uv run infctx config --set-file config/default.json

# Capture a one-off snapshot
uv run infctx snapshot --goal "overhaul the CLI workflow"

# Review snapshot history and inspect the latest capture
uv run infctx snapshots
uv run infctx show-snapshot

# Compare the latest two captures
uv run infctx compare-snapshots

# Start a structured live session with an immediate snapshot
uv run infctx session --goal "overhaul the CLI workflow"

# Inspect current state
uv run infctx status

# Generate a handoff prompt
uv run infctx prompt --mode generic-agent-restore --token-budget 1200
```

If you are operating from outside the repo, pass `--project-root` explicitly:

```bash
uv run infctx config \
  --project-root /path/to/repo \
  --set-file config/default.json
```

## Primary Workflow

`infctx init`

- Creates `.infctx/` and its local metadata store.
- Safe to rerun.

`infctx session`

- Takes an immediate initial snapshot.
- Watches filtered project changes.
- Excludes noisy paths like `.infctx/`.
- Shows recent changed files, last trigger, and skipped cooldown batches.

`infctx snapshot`

- Runs the same capture pipeline without entering live mode.

`infctx snapshots`

- Lists recent snapshots with their goal, branch, tracked file count, and active task count.
- Useful for memory audits and selecting snapshots for inspection or restore.

`infctx show-snapshot`

- Displays the latest snapshot, or a specific one via `--snapshot-id`.
- Includes snapshot metrics, tracked work state, and the generated prompt artifact path.

`infctx compare-snapshots`

- Diffs two snapshots across tracked files, active files, tasks, issues, and metrics.
- Defaults to the latest snapshot compared against the immediately previous one.

`infctx status`

- Shows the latest snapshot, memory count, latest capture time, current goal, active tasks, open issues, pins, and recent commits.

`infctx ingest-chat`

- Ingests an exported transcript or auto-discovers local chat sources.
- Stores inferred goals, decisions, tasks, issues, questions, and signal provenance.
- `--file` is currently more reliable than `--auto`.

`infctx watch`

- Compatibility alias for `infctx session`.

`infctx pins` and `infctx unpin`

- Let you inspect pinned context with notes and remove stale pins without touching the database manually.

## Generated State

Snapshots and outputs are stored in `.infctx/`, including:

- `.infctx/metadata/state.db`
- `.infctx/snapshots/`
- `.infctx/prompts/`
- `.infctx/agents/`
- `.infctx/working_set/`

Every snapshot regenerates:

- `.infctx/agents/overview.md`
- `.infctx/agents/architecture.md`
- `.infctx/agents/behavioral.md`
- `.infctx/agents/decisions.md`
- `.infctx/agents/recent_changes.md`
- `.infctx/agents/instructions.md`

## Recommended Usage

For the best results:

1. Start with an explicit goal.
2. Ingest a real transcript with `ingest-chat --file` when available.
3. Use `session` for live work and `snapshot` for one-off refreshes.
4. Read the generated files in `.infctx/agents/` before trusting the restore prompt.

Recommended order:

```bash
uv run infctx init
uv run infctx ingest-chat --file /path/to/session.txt
uv run infctx snapshot --goal "continue current work"
uv run infctx snapshots
uv run infctx compare-snapshots
uv run infctx status
uv run infctx prompt --mode generic-agent-restore --token-budget 1200
```

## Snapshot Management

New in `0.3.0`, the app can now manage its captured memory directly:

- `uv run infctx snapshots --limit 10` to browse recent memory states.
- `uv run infctx show-snapshot --snapshot-id snap-...` to inspect one snapshot deeply.
- `uv run infctx compare-snapshots --from-snapshot snap-a --to-snapshot snap-b` to understand what changed between captures.
- `uv run infctx pins` and `uv run infctx unpin --path path/to/file.py` to keep pinned context clean.

## Development

```bash
uv sync --extra dev
uv run ruff check .
uv run mypy src
uv run pytest
```

## Documentation

- `docs/overview.md`
- `docs/architecture.md`
- `docs/cli-reference.md`
- `docs/config-reference.md`
- `docs/troubleshooting.md`
