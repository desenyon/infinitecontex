# Context Model Schema Guide

Primary models are in `core/models.py` and validated through Pydantic.

Key entities:

- `Snapshot`: immutable capture record and source of restore.
- `StructuralContext`: tree, modules, key files, entry points, config/env references.
- `BehavioralContext`: call hints, scripts, routes/commands, tests.
- `IntentContext`: goals, decisions, assumptions, tasks, unresolved issues.
- `WorkingSetContext`: branch, diffs, active files, errors, failures, pins.
- `DecisionRecord`: durable decision memory.
- `ContextPacket`: layered output used for prompt compilation.
- `RestoreReport`: stale/missing/changed/valid state reconciliation.
