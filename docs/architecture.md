# Architecture

## Capture Layers

`infinitecontex` 0.2.0 builds snapshots from four explicit layers:

1. Repo context
- `capture/repo_scan.py`
- Scans files, key files, entry points, directory summaries, and file insights

2. Working-set context
- `capture/git_state.py`
- `capture/working_set.py`
- Captures branch, changed files, diffs, pins, and likely next action

3. Runtime context
- `capture/terminal.py`
- Captures failed commands, tracebacks, and failing tests from local terminal logs

4. Intent context
- `capture/chat_ingest.py`
- `capture/chat_auto_discover.py`
- Captures goals, decisions, tasks, issues, questions, and source provenance

## Assembly Flow

`service.py` orchestrates the capture stages:

1. Load effective config
2. Capture repo context
3. Capture runtime context
4. Capture working-set context
5. Capture intent context
6. Assemble a `Snapshot`
7. Save snapshot, prompt, search index, graph, and handoff files

## Storage

The storage layout remains `.infctx/`-based:

- `metadata/state.db`
- `snapshots/*.json`
- `prompts/*.md`
- `events/events.jsonl`
- `graph/context_graph.json`
- `working_set/intent_state.json`

## CLI Layer

`cli.py` exposes:

- one-off commands like `snapshot`, `prompt`, `status`
- a structured live workflow through `session`
- a compatibility alias via `watch`

The CLI now favors:

- immediate feedback
- filtered live updates
- consistent Rich output
- machine-readable `--json` where appropriate
