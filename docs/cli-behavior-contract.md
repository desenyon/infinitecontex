# CLI Behavior Contract

Contract principles:

- Commands are local-first and deterministic.
- Human-readable output should explain what happened, not just dump raw values.
- `--json` output should remain machine-readable and stable within the minor version.
- Invalid input and missing prerequisites must fail loudly with actionable errors.

Workflow expectations:

- `session` is the preferred live command.
- `watch` remains available as a compatibility alias.
- `session --once --json` returns a one-shot session payload suitable for automation.
- Long-running commands should show progress or live state when possible.

Compatibility expectations:

- Existing top-level command names remain available through the 0.4.x line.
- New fields may be added to JSON payloads in backward-compatible ways.
- Removing commands, breaking flags, or changing storage schema requires a documented version bump.

The 0.4.0 migration adds `repair` and an ingest `persisted` field, preserves public names/models/paths, and fixes ignored privacy defaults. See the README for the additive schema-2 migration. JSON is emitted without Rich markup or terminal wrapping. Empty state doctor reads do not initialize storage.
