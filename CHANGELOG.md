# Changelog

All notable changes to this project are documented here.

## [0.4.0] - Unreleased

### Added

- Transactional snapshot repository, durable artifact recovery queue, and `repair` command/client method.
- Read-only doctor diagnostics for SQLite integrity, snapshot artifacts, search orphans, and pending recovery.
- Offline CLI smoke coverage and Python 3.11/3.13 CI validation.

### Fixed

- Archive imports are bounded, confined to `.infctx`, staged, validated, and rolled back on publication failure.
- Exports use SQLite backup for committed WAL data and exclude nested exports.
- Chat and terminal persistence flags are enforced; chat defaults to preview-only. Redaction precedes persistence.
- Capture/restore reject links and unsafe paths; excluded files cannot supply directory summaries.
- Staged Git changes, rename paths, spaces, Unicode, and embedded newlines are captured using porcelain NUL records.
- Cleanup removes snapshot search documents, prompts, restore reports, and obsolete latest handoffs.
- `setup-agent` preserves existing user instructions through an idempotent managed block.
- JSON CLI output is emitted without terminal line wrapping.

### Migration

- Additive storage schema 2 keeps public models and paths. SQLite records become authoritative; legacy JSON-only snapshots are adopted once.
- Existing state is retained. Previously ignored privacy flags now change future capture; enable them explicitly to persist optional inputs.
- See the README for backup, migration, archive overlay semantics, and recovery limitations.

## [0.3.1] - 2026-05-26

### Changed

- Added a global `--project-root` option for CLI commands.
- Removed the stale external package-manager formula.
- Simplified CI to use the default Python runtime instead of a version matrix.
- Expanded CLI test coverage.

## [0.3.0] - 2026-04-22

### Added

- Added `snapshots` to browse memory history with created-at, branch, goal, and workload counts.
- Added `show-snapshot` to inspect a stored snapshot, its metrics, and generated prompt artifact path.
- Added `compare-snapshots` to diff tracked files, tasks, issues, and metric deltas between captures.
- Added `pins` and `unpin` so pinned context is fully manageable from both the CLI and Python API.

### Changed

- Expanded `status` with snapshot counts and latest capture timestamps.
- Bumped the release to `0.3.0` and updated the API surface for snapshot history and pin management.

### Fixed

- Snapshot comparisons now catch real content drift instead of relying only on mtimes.
- Import validation now rejects unsafe archive escapes and link entries.
- Default include patterns now correctly capture root-level files like `app.py`.

## [0.2.0] - 2026-03-15

### Changed

- Reframed the CLI around a structured `session` workflow with an immediate initial snapshot.
- Turned `watch` into a compatibility alias for the new session flow.
- Reworked snapshot assembly into explicit repo, runtime, working-set, and intent capture layers.
- Enriched repo scans with file insights for more useful handoff context.
- Expanded `status` to surface goals, tasks, and open issues.

### Fixed

- Human-readable search output now renders actual search result fields.
- Chat ingestion no longer depends only on rigid `goal:` and `decision:` prefixes.
- Auto-discovery now reports the selected source and checked source list instead of silently failing.
- Default filtering now excludes `.infctx/**` from live session refreshes.

### Docs

- Rewrote README and core docs to match the 0.2.0 workflow and storage layout.
- Updated config, CLI, troubleshooting, and release policy references.

## [0.1.0] - 2026-03-14

### Added

- Initial local-first context engine architecture
- Core CLI command surface
- SQLite metadata, retrieval, graph, and event logging
- Prompt compilation and restore support
