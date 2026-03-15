# Observability And Diagnostics Guide

Observability primitives:

- Structured JSON event log (`events/events.jsonl`).
- Snapshot metrics in snapshot payload.
- `doctor` command for integrity and dependency checks.

Doctor checks:

- git availability
- `.infctx` layout presence
- manifest availability
- SQLite migration integrity
- graph and retrieval directory state

Future-ready extension points exist for richer timing metrics and trace exports.
