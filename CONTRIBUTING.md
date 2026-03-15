# Contributing

## Development

```bash
uv sync --extra dev
uv run ruff check .
uv run mypy src
uv run pytest -q
uv run python -m build
```

## Workflow

1. Update code and tests together.
2. Keep `.infctx` schema-compatible unless a storage change is documented.
3. Update docs when CLI, schema, storage, or restore behavior changes.
4. Use `infctx note` for important architectural decisions.

## Pull Requests

- Keep changes focused.
- Include validation results.
- Document rollout or migration risk when behavior changes.
