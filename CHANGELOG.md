# Changelog

All notable changes to this project are documented here.

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
