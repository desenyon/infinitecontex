# Testing Strategy

Test layers:

- Unit tests: config, storage, graph consistency, CLI behavior.
- Integration tests: snapshot/restore pipeline, export/import roundtrip.
- Golden tests: required prompt section invariants.
- Regression tests: token budget length behavior.
- Performance tests: structural scan wall-clock guardrail.

Run:

```bash
pytest
```

CI enforces lint, type checks, tests, and package build validation.
