# Infinite Context

Infinite Context is a local-first project memory engine for AI-assisted software development. It captures repository state, developer intent, architecture decisions, and working context into compact, structured handoff artifacts that can be consumed instantly by any coding agent or passed to a new developer joining the project.

The problem it solves: AI coding sessions are stateless by default. Every new conversation starts from zero. Chat history is noisy and expensive to re-feed. Context files like CLAUDE.md degrade into markdown graveyards. Infinite Context replaces all of that with a single, always-current source of truth that is generated from your actual repository state rather than manually maintained.


## How It Works

Running `infctx snapshot` scans the repository, compresses the structural and behavioral signal, and writes a canonical handoff file to `.infctx/project/inside.infinite_context.md`. The same data is available as `.infctx/project/inside.infinite_context.json` for programmatic consumption.

Any coding agent (GitHub Copilot, Claude Code, Cursor, generic LLM) can open that file and immediately understand:

- what the project does and how it is structured
- what changed recently and what the developer was working on
- which architectural decisions were made and why
- which files are most relevant right now
- what the next action should be

The handoff file is regenerated on every snapshot and can be kept live with `infctx watch`.


## Installation

### From PyPI (once published)

```bash
pip install infinitecontex
# or with uv
uv add infinitecontex
```

### From source (recommended for development)

Requires Python 3.12 or later and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/desenyon/infinitecontex
cd infinitecontex
uv sync --extra dev
```

Verify the install:

```bash
uv run infctx --version
uv run infctx --help
```

### Without uv

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
infctx --version
```


## Setup

Initialize a project by running this from the repository root you want to track:

```bash
uv run infctx init
```

This creates the `.infctx/` directory with its database, layout, and config. It is safe to re-run. The `.infctx/` directory should be committed to source control so that context state persists across machines and branches.

Apply the included default configuration to constrain scanning to source files only:

```bash
uv run infctx config --set-file config/default.json
```

Take the first snapshot:

```bash
uv run infctx snapshot --goal "initial project setup"
```

Verify everything is healthy:

```bash
uv run infctx doctor
```


## Quick Start Workflow

```bash
# Initialize once per repository
uv run infctx init
uv run infctx config --set-file config/default.json

# Before starting a work session
uv run infctx snapshot --goal "implement the authentication flow"

# During work — let context update automatically on every file save
uv run infctx watch --goal "implement the authentication flow"

# When handing off to an agent or a colleague
uv run infctx prompt --mode generic-agent-restore --token-budget 1200

# When resuming after a break
uv run infctx restore
uv run infctx status --json
```


## Command Reference

All commands support `--project-root PATH` to run against a repository other than the current directory. Most commands support `--json` to produce machine-readable output.

---

### init

Initialize the `.infctx/` directory structure for a repository.

```
infctx init [--project-root PATH] [--json]
```

Creates the SQLite database, directory layout, and default configuration. Safe to re-run on an already-initialized repository. Run this once per repository before any other command.

---

### snapshot

Capture a full project snapshot and regenerate the handoff files.

```
infctx snapshot [--goal TEXT] [--project-root PATH] [--json]
```

This is the primary write operation. It scans the repository according to the active configuration, computes file relevance scores and structural context, writes the snapshot to the database, and regenerates `.infctx/project/inside.infinite_context.md` and `.infctx/project/inside.infinite_context.json`.

The `--goal` option records what the developer is currently working on. Setting a descriptive goal significantly improves the quality of generated restore prompts.

```bash
uv run infctx snapshot --goal "refactor the database connection pool"
uv run infctx snapshot --goal "fix edge case in token budget trimming"
```

---

### restore

Print a restore report showing what has changed since the last snapshot.

```
infctx restore [--snapshot-id TEXT] [--project-root PATH] [--json]
```

Compares the current repository state against the specified snapshot (or the latest one if no ID is given). Reports files that are stale, changed, missing, or valid. Use this to understand drift after a branch switch, machine hop, or time away from the project.

```bash
uv run infctx restore
uv run infctx restore --snapshot-id snap_20240314_142301
```

---

### status

Display current project status and snapshot metadata.

```
infctx status [--project-root PATH] [--json]
```

Shows the active snapshot ID, when it was taken, the developer goal recorded at that time, and a summary of captured file counts and token estimates.

```bash
uv run infctx status
uv run infctx status --json | jq .snapshot_id
```

---

### prompt

Compile a restore prompt from the latest snapshot and print it to stdout.

```
infctx prompt [--mode MODE] [--token-budget INT] [--snapshot-id TEXT] [--project-root PATH]
```

Modes:

- `generic-agent-restore` (default) — a structured prompt suitable for any LLM or coding agent
- `copilot-restore` — formatted for GitHub Copilot agent mode
- `claude-code-restore` — formatted for Claude Code sessions
- `human-handoff` — a readable summary formatted for a developer picking up the work

The `--token-budget` option controls approximately how many tokens the compiled output will use. The default is 1200. Higher budgets produce more detail; lower budgets force trimming to the most critical signal.

```bash
# Print to stdout and copy to clipboard
uv run infctx prompt --mode generic-agent-restore --token-budget 1200

# Use a tight budget for a quick paste into a chat session
uv run infctx prompt --mode human-handoff --token-budget 500

# Use a large budget for a comprehensive agent briefing
uv run infctx prompt --mode claude-code-restore --token-budget 4000
```

The compiled prompt is also saved to `.infctx/prompts/` with a timestamped filename.

---

### watch

Monitor the repository for file changes and trigger automatic snapshots.

```
infctx watch [--goal TEXT] [--project-root PATH] [--debounce-ms INT] [--min-interval-sec INT]
```

Watches for file-system changes and runs a snapshot automatically after each quiet period. Keeps `.infctx/project/inside.infinite_context.md` continuously current while you work.

- `--debounce-ms` — wait this long after the last change before triggering a snapshot (default: 1200)
- `--min-interval-sec` — minimum seconds between consecutive snapshots (default: 3)

```bash
# Run in a separate terminal while working
uv run infctx watch --goal "build the search ranking feature"

# More aggressive refresh for fast iteration
uv run infctx watch --goal "debugging" --debounce-ms 500 --min-interval-sec 1
```

Stop with Ctrl+C.

---

### note

Record a decision or architectural choice in project memory.

```
infctx note --summary TEXT --rationale TEXT [--alternative TEXT] [--impact TEXT] [--tag TEXT]
```

Decisions recorded with `note` are included in restore prompts and the handoff file. They persist across snapshots and serve as a running log of why the codebase looks the way it does.

```bash
uv run infctx note \
  --summary "switched from asyncpg to psycopg3" \
  --rationale "better typing support and active maintenance" \
  --alternative "stay on asyncpg" \
  --impact "connection pool behavior changes, update all query wrappers" \
  --tag database
```

---

### decisions

List recorded decisions.

```
infctx decisions [--limit INT] [--project-root PATH] [--json]
```

```bash
uv run infctx decisions
uv run infctx decisions --limit 5 --json
```

---

### pin

Mark a file as high-priority so it is always included in restore prompts and the handoff file.

```
infctx pin --path TEXT [--note TEXT] [--project-root PATH]
```

```bash
uv run infctx pin --path src/infinitecontex/service.py --note "main orchestration layer"
uv run infctx pin --path pyproject.toml
```

---

### search

Search across snapshot content and recorded decisions using keyword matching.

```
infctx search --query TEXT [--limit INT] [--project-root PATH] [--json]
```

```bash
uv run infctx search --query "database connection"
uv run infctx search --query "token budget" --limit 5
```

---

### diff-summary

Print a summary of what has changed between the current state and the last snapshot.

```
infctx diff-summary [--project-root PATH] [--json]
```

Useful for quickly understanding what happened during a coding session before taking a new snapshot.

---

### ingest-chat

Import a saved chat session and extract decisions, goals, and relevant context from it.

```
infctx ingest-chat --file PATH [--project-root PATH] [--json]
```

Accepts a plain text or JSON export of a conversation. Parsed decisions are stored in the decision log. Useful for capturing the reasoning from a chat session after the fact.

```bash
uv run infctx ingest-chat --file ~/Downloads/session_export.txt
```

---

### export

Export the entire `.infctx/` state directory as a portable `.tar.gz` archive.

```
infctx export --output PATH [--project-root PATH]
```

```bash
uv run infctx export --output /tmp/myproject_context.tar.gz
```

---

### import

Restore a previously exported `.infctx/` state archive.

```
infctx import --archive PATH [--project-root PATH]
```

```bash
uv run infctx import --archive /tmp/myproject_context.tar.gz
```

The import overwrites the existing `.infctx/` directory. Use this to migrate context state to a new machine or restore from a backup.

---

### doctor

Run health checks on the project state and report any issues.

```
infctx doctor [--project-root PATH] [--json]
```

Checks that the database is accessible, the directory layout is intact, the latest snapshot is not excessively stale, and that required tool dependencies are available. Outputs pass/fail for each check with a brief description.

```bash
uv run infctx doctor
uv run infctx doctor --json | jq '.checks[] | select(.status != "ok")'
```

---

### config

View or update the project configuration.

```
infctx config [--set-file PATH] [--project-root PATH] [--json]
```

Without `--set-file`, prints the currently active configuration (merged from repo-local, global, and default sources).

With `--set-file`, merges the provided JSON file into the repo-local configuration at `.infctx/config.json`.

```bash
# View active config
uv run infctx config --json

# Apply a config preset
uv run infctx config --set-file config/default.json
```


## Configuration Reference

The active configuration is built by merging four sources in priority order:

1. Environment variables (`INFCTX_` prefix)
2. Repo-local config at `.infctx/config.json`
3. Global user config at `~/.config/infctx/config.json`
4. Built-in defaults

Key settings:

| Setting | Type | Default | Description |
|---|---|---|---|
| `project_name` | string | directory name | Human-readable project name included in handoff files |
| `capture_max_files` | int | 1500 | Maximum number of files to include in a snapshot |
| `include_patterns` | list | `["**"]` | Glob patterns for files to include |
| `exclude_patterns` | list | see below | Glob patterns for files to exclude |
| `policies.token.default_budget` | int | 1200 | Default token budget for `prompt` |
| `policies.token.min_budget` | int | 300 | Minimum token budget enforced |
| `policies.token.max_budget` | int | 16000 | Maximum token budget enforced |
| `policies.summarization.max_key_files` | int | 30 | Max key files to surface in prompts |
| `policies.summarization.max_active_files` | int | 25 | Max active files to surface in prompts |
| `policies.privacy.persist_shell_history` | bool | false | Whether to store shell history in the state db |
| `policies.privacy.redact_patterns` | list | API key patterns | Regex patterns for secrets to redact from captured content |

### Recommended config for a Python project

```json
{
  "project_name": "myproject",
  "capture_max_files": 600,
  "include_patterns": ["**/*.py", "**/*.md", "pyproject.toml", "README.md"],
  "exclude_patterns": [
    ".git/**",
    ".venv/**",
    "node_modules/**",
    ".infctx/**",
    ".pytest_cache/**",
    ".mypy_cache/**",
    ".ruff_cache/**",
    "**/*.pyc",
    "build/**",
    "dist/**"
  ]
}
```

Save this to a file and apply it with:

```bash
uv run infctx config --set-file myconfig.json
```

The `config/default.json` in this repository contains a working preset for Python projects.


## The Handoff Files

Every snapshot regenerates two canonical files:

**`.infctx/project/inside.infinite_context.md`**

A Markdown document structured for direct consumption by a coding agent or human. Contains project summary, recent changes, architectural decisions, pinned files, active context, and recommended next action.

**`.infctx/project/inside.infinite_context.json`**

The same data in JSON format for programmatic consumption, scripting, or integration with other tools.

These files are the primary output of Infinite Context. They are designed to be committed to source control so that they are always available alongside the code.

### Using the handoff file with an agent

Open a new agent session and paste or reference `.infctx/project/inside.infinite_context.md` as the first message. The agent will have enough context to continue work without any additional explanation.

For a formatted restore prompt with more detail:

```bash
uv run infctx prompt --mode claude-code-restore --token-budget 4000
```

Pipe the output directly into a new session, or save it to a file for reuse.


## Development Setup

Requirements: Python 3.12+, [uv](https://docs.astral.sh/uv/) 0.5+.

```bash
git clone https://github.com/desenyon/infinitecontex
cd infinitecontex
uv sync --extra dev
```

Run the full validation suite:

```bash
uv run ruff check .
uv run mypy src
uv run pytest -q
uv run python -m build
```

Run just the tests with coverage:

```bash
uv run pytest --cov=src --cov-report=term-missing
```

Run a specific test file:

```bash
uv run pytest tests/unit/test_summarizer.py -v
```

The test suite covers the summarizer, config loading, repo scanning, export/import, restore engine, doctor checks, snapshot pipeline, and CLI version flag. Integration tests run a full snapshot cycle in a temporary directory.


## Publishing to PyPI

The repository includes a `publish.yml` GitHub Actions workflow that publishes to PyPI using [uv publish](https://docs.astral.sh/uv/guides/publish/). It uses OIDC trusted publishing, which means no API token needs to be stored in GitHub secrets.

### One-time setup

1. Create a PyPI account and a new project named `infinitecontex` at https://pypi.org.

2. In the PyPI project settings, go to "Publishing" and add a trusted publisher:
   - Publisher: GitHub Actions
   - Repository owner: `desenyon`
   - Repository name: `infinitecontex`
   - Workflow name: `publish.yml`
   - Environment name: `pypi`

3. In the GitHub repository settings, go to Environments and create an environment named `pypi`. Optionally add a required reviewer to gate production deploys.

### Triggering a release

Bump the version in two places:

```bash
# src/infinitecontex/version.py
__version__ = "0.2.0"

# pyproject.toml
version = "0.2.0"
```

Commit, tag, and push:

```bash
git add src/infinitecontex/version.py pyproject.toml
git commit -m "release: bump to 0.2.0"
git tag v0.2.0
git push origin main --tags
```

Then create a GitHub release from the tag. Publishing to PyPI triggers automatically when the release is marked as published.

You can also trigger a manual publish from the Actions tab using the `workflow_dispatch` event on the Publish workflow.

### Installing a published release

```bash
# With uv
uv add infinitecontex

# With pip
pip install infinitecontex

# With uvx for one-off use without installing
uvx infinitecontex --help
```


## Storage Layout

All state is stored under `.infctx/` in the project root:

```
.infctx/
  config.json          repo-local configuration overrides
  db/
    context.db         SQLite database (snapshots, decisions, pins, events)
  project/
    inside.infinite_context.md    canonical agent handoff file
    inside.infinite_context.json  same data as JSON
  prompts/             timestamped generated prompt files
  exports/             temporary export archives
```

The SQLite database contains tables for snapshots, file metadata, decision log, pin registry, event log, and retrieval index. See `docs/storage-format.md` and `docs/data-model-reference.md` for the full schema.


## Documentation

The `docs/` directory contains detailed reference material:

| Document | Contents |
|---|---|
| `architecture.md` | Component diagram and design decisions |
| `cli-behavior-contract.md` | Stability guarantees for CLI flags and output |
| `cli-reference.md` | Full CLI reference with all flags |
| `coding-standards.md` | Style guide and conventions for contributors |
| `config-reference.md` | Complete configuration schema with all defaults |
| `data-model-reference.md` | Database schema and entity relationships |
| `deployment-release.md` | Release checklist and uv-based publish workflow |
| `mental-model.md` | How to think about context compilation |
| `observability-diagnostics.md` | Event log structure and doctor check details |
| `restore-pipeline.md` | How restore divergence detection works |
| `security-privacy.md` | Local-first trust model, redaction behavior |
| `storage-format.md` | File layout and SQLite schema |
| `testing-strategy.md` | Test organization and coverage goals |
| `token-optimization.md` | How token budgets affect output |
| `troubleshooting.md` | Common issues and fixes |


## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development workflow, commit conventions, and how to run the test suite. All contributions require passing ruff, mypy, and pytest before review.


## Security

Sensitive values matching the configured `redact_patterns` are stripped from captured content before being written to the database. No data is sent to any external service. See [SECURITY.md](SECURITY.md) for the full trust model and how to report vulnerabilities.


## License

MIT. See [LICENSE](LICENSE).
