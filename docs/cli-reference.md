# CLI Reference

Global:

- `infctx --version`
- `infctx --help`
- `infctx --project-root PATH COMMAND ...`

Structured workflow:

- `infctx init [--project-root PATH] [--json]`
- `infctx session [--goal TEXT] [--project-root PATH] [--debounce-ms INT] [--min-interval-sec INT] [--once] [--json]`
- `infctx watch [--goal TEXT] [--project-root PATH] [--debounce-ms INT] [--min-interval-sec INT]`
- `infctx status [--project-root PATH] [--json]`
- `infctx snapshot [--goal TEXT] [--project-root PATH] [--json]`
- `infctx snapshots [--limit INT] [--project-root PATH] [--json]`
- `infctx show-snapshot [--snapshot-id ID] [--project-root PATH] [--json]`
- `infctx compare-snapshots [--from-snapshot ID] [--to-snapshot ID] [--project-root PATH] [--json]`
- `infctx restore [--snapshot-id ID] [--project-root PATH] [--json]`
- `infctx prompt [--mode MODE] [--token-budget INT] [--snapshot-id ID] [--project-root PATH]`

Context curation:

- `infctx note --summary TEXT --rationale TEXT [--alternative TEXT] [--impact TEXT] [--tag TEXT] [--project-root PATH]`
- `infctx pin --path TEXT [--note TEXT] [--project-root PATH]`
- `infctx pins [--project-root PATH] [--json]`
- `infctx unpin --path TEXT [--project-root PATH]`
- `infctx ingest-chat [--file PATH | --auto] [--project-root PATH] [--json]`
- `infctx decisions [--limit INT] [--project-root PATH] [--json]`
- `infctx search --query TEXT [--limit INT] [--project-root PATH] [--json]`
- `infctx diff-summary [--project-root PATH] [--json]`

Project maintenance:

- `infctx doctor [--project-root PATH] [--json]`
- `infctx config [--set-file PATH] [--project-root PATH] [--json]`
- `infctx export --output PATH [--project-root PATH]`
- `infctx import --archive PATH [--project-root PATH]`
- `infctx cleanup [--keep INT] [--project-root PATH] [--yes]`
- `infctx setup-agent AGENT [--project-root PATH]`

Notes:

- `session` is the preferred live workflow command.
- `watch` is a compatibility alias for `session`.
- `session --json` is supported only together with `--once`.
- `compare-snapshots` defaults to the latest snapshot compared against the immediately previous one.
- `cleanup` requires `--yes` when it will delete old snapshots.
- `config --set-file` resolves relative preset paths against `--project-root` when provided.
- For reliable intent capture, prefer `ingest-chat --file` over `ingest-chat --auto`.

## Recovery and retention (0.4.0)

```bash
infctx doctor --json
infctx repair --json
infctx cleanup --keep 20 --yes
```

Doctor is diagnostic and does not initialize a missing database. Repair migrates legacy state and rebuilds derived snapshot files, canonical prompts, snapshot search, and latest graph/handoff. Cleanup also removes derived artifacts and snapshot search rows; zero clears the latest handoff, and negative counts are rejected. CLI/client names and file paths remain compatible.

`ingest-chat` now reports `persisted` in JSON. With the default privacy flags it returns a redacted preview without saving chat state. Enable `policies.privacy.persist_chat_ingest` explicitly to save intent and search content. `setup-agent` updates a managed block, retaining existing instructions outside it.
