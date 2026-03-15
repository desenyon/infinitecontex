# Troubleshooting

`infctx doctor` reports:

- `git: missing` -> install git and retry.
- `layout: missing` -> run `infctx init`.
- `manifest: missing` -> run `infctx init` to regenerate.
- `sqlite: error` -> remove corrupt DB and re-run `infctx init`.
- `graph: missing` -> run `infctx snapshot`.

Common issues:

- No snapshots found: run `infctx snapshot` before `restore` or `prompt`.
- Empty search results: generate snapshot and ingest chat/notes first.
