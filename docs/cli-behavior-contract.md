# CLI Behavior Contract

Contract principles:

- Commands are local-first and deterministic.
- Human-readable output should explain what happened, not just dump raw values.
- `--json` output should remain machine-readable and stable within the minor version.
- Invalid input and missing prerequisites must fail loudly with actionable errors.

Workflow expectations in 0.2.0:

- `session` is the preferred live command.
- `watch` remains available as a compatibility alias.
- `session --once --json` returns a one-shot session payload suitable for automation.
- Long-running commands should show progress or live state when possible.

Compatibility expectations:

- Existing top-level command names remain available within the 0.2.x line.
- New fields may be added to JSON payloads in backward-compatible ways.
- Removing commands, breaking flags, or changing storage schema requires a documented version bump.
