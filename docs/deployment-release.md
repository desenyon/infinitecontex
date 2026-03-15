# Deployment And Release Guide

## Build

```bash
uv sync --extra dev
uv run python -m build
```

## CI

Pipeline validates:

- lint (`ruff`)
- typing (`mypy`)
- tests (`pytest`)
- packaging (`python -m build`)

UV is the primary workflow for local development, CI, and release publication.

## Release policy

- Semantic versioning.
- Tag format: `vX.Y.Z`.
- Automated release artifact publishing via GitHub Actions.
- Optional PyPI publication via `uv publish` and trusted publishing.
- Changelog entries required for every release.
