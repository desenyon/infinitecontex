# Storage and migration

Storage schema **2** retains the `.infctx/` layout and snapshot JSON model. The package version on this development branch is **0.4.0**.

| Location | Role |
| --- | --- |
| `metadata/state.db` | Authoritative snapshot payloads, decisions, pins, FTS documents, recovery queue |
| `metadata/manifest.json` | Layout metadata with schema version |
| `snapshots/ID.json` | Rebuildable snapshot copy |
| `prompts/ID.prompt.md` | Canonical generic prompt; mode-specific variants are generated on request |
| `agents/*.md` | Latest snapshot's generated context briefs |
| `project/inside.infinite_context.{json,md}` | Legacy handoff paths |
| `graph/context_graph.json` | Latest snapshot graph |
| `summaries/restore-ID.json` | On-demand restore report |
| `working_set/intent_state.json` | Opted-in, redacted chat intent |
| `working_set/terminal.log` | User-supplied terminal input |
| `events/events.jsonl` | Operational events |
| `exports/` | User-generated archives; contents excluded from exports |

The advisory lock is `.infctx.lock` in the project root. Do not remove it while a client is active. Add it and `.infctx/` to the project's ignore file.

## Database migration

Existing snapshot/decision/pin/search tables remain. Schema 2 adds `artifact_jobs(snapshot_id, action)` and `repository_state(key, value)` and sets SQLite `user_version` to 2. Migration runs on initialization or a mutating operation, including `repair`.

During the first migration, valid JSON-only snapshots are adopted. If both database and JSON copies exist, the database wins. Invalid legacy JSON stops migration without deleting the file. Snapshot search entries are reconstructed, removing stale entries from older cleanup behavior. Future schema versions are rejected by writers.

Once migrated, JSON-only files are not published snapshots and cannot override committed data. A full repair removes orphan generated snapshot copies. Stop older clients before migration; mixed-version writers are unsupported. Back up the state directory before upgrade.

## Failure semantics

A snapshot transaction commits its payload, search document, and repair job together. Failed transactions publish nothing. File materialization follows the commit. On I/O failure, APIs can still read committed data; a warning and doctor output report pending repair. The next mutating operation retries, or run `infctx repair --json` explicitly.

Repair rebuilds JSON, canonical prompts, snapshot search documents, and the latest graph/handoff. It does not regenerate arbitrary custom prompt budgets or past restore reports. Cleanup deletes snapshot/search rows atomically and removes corresponding JSON, known prompt variants, and restore reports. Keeping zero snapshots also removes generated latest handoff/graph files. Cleanup is not secure erasure and does not delete chat, events, or decisions.

Individual files are atomically replaced. Multi-file handoff updates and archive publication are recoverable, not instantaneous for external readers. The next locked operation restores `.infctx-import-backup` if import was interrupted after moving the old tree but before publishing the staged tree. A completed publication may leave a backup or staging directory after a process kill; inspect these with writers stopped.

## Archives

Gzip tar archives contain normalized `.infctx/` entries only. Links, special/sparse files, traversal, duplicate/case-alias names, and file/directory collisions are rejected. Limits: 20,000 entries, 256 MiB per entry, 1 GiB total declared content. Existing state links are rejected too.

Exports use SQLite backup, including committed WAL contents, and exclude nested exports. Imports stage a copy of existing state and overlay archive files. An included database replaces destination metadata/history. State outside `.infctx` is never extracted. Database/configuration/snapshot validation occurs before publication; malformed archives leave prior state in place.

For database loss, use a backup copy of the tree and stop writers before recovery. A missing database can be initialized from surviving JSON during migration, but database-only records require a database backup. A corrupt database is not silently replaced from derived files.
