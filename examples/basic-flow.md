# Basic Workflow

```bash
infctx init
infctx snapshot --goal "finish restore engine"
infctx note --summary "Use SQLite for metadata" --rationale "portable and reliable"
infctx pin --path src/infinitecontex/service.py --note "active orchestration surface"
infctx prompt --mode copilot-restore --token-budget 1200
infctx export --output .infctx/exports/context.tgz
```
