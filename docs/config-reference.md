# Config Reference

Merge precedence, highest first:

1. Environment overrides
2. Repo-local `.infctx/config.json`
3. Global `~/.config/infinitecontex/config.json`
4. Built-in defaults

Environment overrides currently supported:

- `INFCTX_TOKEN_BUDGET`

Key config fields:

- `project_name`
- `capture_max_files`
- `include_patterns`
- `exclude_patterns`
- `modes`
- `policies.token`
- `policies.summarization`
- `policies.privacy`

Important defaults in 0.2.0:

- `.infctx/**` is excluded by default
- `config/default.json` is tuned for Python repos
- `session` filtering uses the same exclude patterns as snapshot capture, plus `.infctx/**`

CLI note:

- `infctx config --set-file config/default.json` works from the repo root.
- If you also pass `--project-root`, the preset path is resolved relative to that project root when possible.

Example:

```json
{
  "project_name": "infinitecontex",
  "capture_max_files": 600,
  "include_patterns": ["**/*.py", "**/*.md", "pyproject.toml", "README.md"],
  "exclude_patterns": [
    ".git/**",
    ".infctx/**",
    ".venv/**",
    "node_modules/**",
    ".pytest_cache/**",
    ".mypy_cache/**",
    ".ruff_cache/**",
    "**/*.pyc",
    "build/**",
    "dist/**"
  ]
}
```
