# CLI Behavior Contract

Contract principles:

- Commands are local-first and deterministic.
- `--json` mode returns machine-readable payloads.
- Human mode stays concise and action-oriented.
- Commands must fail loudly on invalid snapshot/config references.

Compatibility expectations:

- Backward-compatible command names and flags within minor versions.
- Changes to output schema require release note and version bump.
