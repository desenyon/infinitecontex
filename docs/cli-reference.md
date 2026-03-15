# CLI Reference

Core commands:

- `infctx init`
- `infctx snapshot --goal "..."`
- `infctx restore [--snapshot-id ID]`
- `infctx status`
- `infctx note --summary ... --rationale ...`
- `infctx pin --path ... --note ...`
- `infctx ingest-chat --file chat.txt`
- `infctx diff-summary`
- `infctx decisions --limit 20`
- `infctx search --query "..."`
- `infctx prompt --mode generic-agent-restore --token-budget 1200`
- `infctx export --output .infctx/exports/context.tgz`
- `infctx import --archive context.tgz`
- `infctx doctor`
- `infctx config [--set-file config.json]`

All primary commands support `--project-root` and most support `--json` for machine-readable output.
