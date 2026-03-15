# Lockfile Strategy

- Development: use `pip-tools` or `uv` to generate a fully pinned lock file per platform.
- CI: install from lock file for reproducible checks.
- Release: build from locked dependencies and validate with test matrix.

Recommended commands:

```bash
pip install pip-tools
pip-compile pyproject.toml -o requirements.lock
pip-sync requirements.lock
```
