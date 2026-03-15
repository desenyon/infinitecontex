# Security Policy

## Reporting

Please report security issues privately through GitHub Security Advisories or direct maintainer contact.

## Product Trust Model

- Infinite Context is local-first by default.
- It does not silently upload repository state.
- Chat and terminal ingestion remain explicit operations.
- Exported archives should be treated as sensitive project metadata.

## Hardening Expectations

- Validate changes with `uv run ruff check .`, `uv run mypy src`, `uv run pytest -q`, and `uv run python -m build`.
- Preserve redaction behavior and archive import safety checks.
