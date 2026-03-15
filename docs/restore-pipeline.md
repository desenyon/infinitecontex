# Restore Pipeline Guide

1. Load target snapshot (`snapshots/*.json` or SQLite fallback).
2. Compare saved branch against current branch.
3. Validate file existence and mutation state via fingerprint mtimes.
4. Classify each element as stale, missing, changed, or still valid.
5. Emit restore report and persist summary artifact.
6. Compile mode-specific prompt to continue work quickly.

Restore output explicitly explains divergence so agents do not over-trust stale memory.
