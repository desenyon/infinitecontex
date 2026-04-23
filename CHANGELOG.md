# Changelog

All notable changes to this project are documented here.

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
