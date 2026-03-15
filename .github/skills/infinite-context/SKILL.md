---
name: "infinite-context"
description: "Repository-specific implementation skill for Infinite Context architecture, coding standards, CLI contracts, storage schema, and release workflow."
---

# Infinite Context Skill

Use this skill when implementing or reviewing functionality in this repository.

## Engineering Rules

- Keep local-first behavior as default.
- Do not add silent network upload paths.
- Preserve `.infctx/` schema compatibility unless a migration is documented.
- Keep prompt output token-aware and layered.
- Keep CLI machine-readable output stable with `--json`.

## Required Validation Before Merge

1. `ruff check .`
2. `mypy src`
3. `pytest`
4. `python -m build`

## Key Components

- `src/infinitecontex/service.py`: orchestration
- `src/infinitecontex/cli.py`: command contract
- `src/infinitecontex/storage/db.py`: metadata schema and retrieval index
- `src/infinitecontex/distill/summarizer.py`: token-aware packets
- `src/infinitecontex/restore/engine.py`: divergence detection

## Documentation Alignment

Any architecture or schema change must update:

- `docs/architecture.md`
- `docs/storage-format.md`
- `docs/data-model-reference.md`
- `docs/cli-behavior-contract.md`
