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

## 0.4.0 behavior

Persistence flags default to false and are enforced. Chat ingestion is a redacted preview unless `policies.privacy.persist_chat_ingest` is true. Terminal signals require `persist_shell_history`. Neither setting erases historical data. Invalid redaction expressions and nonpositive `capture_max_files` are rejected. Empty include patterns admit no files. Internal state exclusions cannot be disabled.

`config --set-file` writes a full validated configuration, filling omitted fields with defaults. `project_name`, `modes`, token min/max, and summarization knobs remain accepted for compatibility but are not all consulted by capture/rendering. See the [README field table](../README.md#configuration) for the precise active settings and limitations.
