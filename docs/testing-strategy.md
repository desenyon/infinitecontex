# Testing strategy

```bash
uv sync --locked --extra dev --python 3.13
uv run ruff check .
uv run mypy src
uv run pytest
uv run python scripts/smoke.py
uv build
```

The original pre-upgrade baseline contains 78 tests. The expanded suite adds regressions for archive containment, symlinks/hardlinks/special files, resource bounds, import rollback, WAL-aware export, persistence flags and redaction, staged/renamed Git paths, snapshot transaction rollback, artifact repair, migration, cleanup, and process concurrency. Use the actual pytest output for current counts and coverage; neither is a fixed product guarantee.

The CLI smoke script uses disposable Git repositories and synthetic content. It exercises real subprocess output, JSON parsing, opt-in persistence, two captures, staged changes, comparison, drift validation, prompt generation, retention, missing-file repair, archive roundtrip, and doctor. It can also be run against an installed wheel to check packaging.

CI tests Python 3.11 and 3.13 on Linux and runs the smoke script and package build. Development checks also run on macOS. Tests do not require credentials or external services. Dependency installation may require network access. The structural-scan timing test is a small regression guardrail, not a published performance benchmark.
