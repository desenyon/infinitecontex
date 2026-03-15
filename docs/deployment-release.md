# Deployment And Release Guide

## Build

```bash
python -m pip install -e .[dev]
python -m build
```

## CI

Pipeline validates:

- lint (`ruff`)
- typing (`mypy`)
- tests (`pytest`)
- packaging (`python -m build`)

## Release policy

- Semantic versioning.
- Tag format: `vX.Y.Z`.
- Automated release artifact publishing via GitHub Actions.
- Changelog entries required for every release.
