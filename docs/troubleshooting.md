# Troubleshooting

## No snapshots found

Run `infctx snapshot --goal "describe current work"` or `infctx session`. Select the correct root with `--project-root`. A snapshot records context, not a backup of source code.

## Chat or terminal context is empty

Persistence defaults to disabled. `ingest-chat` returns `persisted: false` in JSON and a preview notice in human output. Enable `policies.privacy.persist_chat_ingest` to save intent/search. Enable `persist_shell_history` to capture the manually supplied `.infctx/working_set/terminal.log`. Explicit snapshot goals do not require either flag. See the [configuration example](../README.md#privacy-and-capture-boundaries).

## Snapshot committed but files are missing or stale

Run `infctx doctor --json`, then `infctx repair --json`. Snapshot APIs read the committed SQLite payload even when derived JSON is missing or corrupt. Pending artifact work is also retried by the next mutating operation. Repair needs working filesystem permissions and enough disk space.

A malformed legacy JSON file stops its one-time migration. Preserve a backup, inspect the named file, and move the invalid file aside only after deciding it is not needed. Do not delete the database as a routine repair step.

## Archive rejected

Only normalized regular files and directories under `.infctx/` are accepted. Links, duplicate paths, special files, collisions, oversized bundles, invalid configuration, or invalid database/snapshot state are rejected before publication. Export again with a current client. Never bypass checks by extracting an untrusted archive into a repository.

Stop writers before inspecting leftover `.infctx-import-*` staging/backup directories. A subsequent locked operation restores the backup if a process died in the publication gap.

## Search is empty or reports an expression error

Snapshots index their canonical prompt. Chat source text is indexed only with persistence enabled. Search uses SQLite FTS5 syntax; malformed expressions are errors. Rebuild snapshot search with `infctx repair`. Explicit notes appear in search after inclusion in a snapshot, not immediately as independent documents.

## State or project files are skipped

Linked state paths are errors. Capture skips project symlinks, hard-linked files, special/unreadable files, internal metadata, excluded paths, and files larger than 2 MiB. Include patterns and `capture_max_files` can further restrict capture. The scanner does not apply `.gitignore` automatically.

## Session refresh frequency

Tune `--debounce-ms` and `--min-interval-sec`. Internal `.infctx` paths are always filtered. `session --once --json` is the automation-friendly one-shot form; `watch` remains an alias.

## Configuration path

Repo settings live at `.infctx/config.json`; global settings at `~/.config/infinitecontex/config.json`. Use `infctx config --json` to inspect the effective merge. `--set-file` validates a file and saves a full config, so omitted settings take defaults. See [config-reference.md](config-reference.md).
