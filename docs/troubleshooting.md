# Troubleshooting

## No snapshots found

Run:

```bash
uv run infctx snapshot --goal "describe current work"
```

or start a live workflow:

```bash
uv run infctx session --goal "describe current work"
```

## Context feels empty

Check the likely causes:

- no current goal has been captured yet
- no changed files or recent diffs exist
- no terminal failures were captured
- no chat transcript has been ingested

Helpful commands:

```bash
uv run infctx status
uv run infctx ingest-chat --auto
uv run infctx snapshot --goal "what you are doing now"
```

## `session` is refreshing too often or not enough

Tune:

- `--debounce-ms`
- `--min-interval-sec`

Remember:

- `.infctx/**` is filtered out
- `watch` is now just an alias for `session`

## Search results are empty

Make sure there is indexed content first:

```bash
uv run infctx snapshot --goal "index current repo state"
uv run infctx ingest-chat --file path/to/transcript.txt
uv run infctx search --query "your query"
```

## Config path confusion

The global config path is:

`~/.config/infinitecontex/config.json`

The repo-local config path is:

`.infctx/config.json`
