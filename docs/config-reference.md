# Config Reference

Merge precedence (highest first):

1. Environment overrides
2. Repo-local `.infctx/config.json`
3. Global `~/.config/infinitecontex/config.json`
4. Defaults

Environment overrides:

- `INFCTX_TOKEN_BUDGET`

Config model:

- `include_patterns`: glob includes
- `exclude_patterns`: glob excludes
- `modes`: enabled prompt modes
- `policies.token`: token budget limits
- `policies.summarization`: summary granularity controls
- `policies.privacy`: chat/shell persistence and redaction patterns
