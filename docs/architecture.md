# Architecture

The CLI, `InfiniteContextClient`, and `AgentToolInterface` call `InfiniteContextService`. Capture and rendering stay local; no inference service is required.

## Capture and policy

- `capture/repo_scan.py`: sorted, filtered, size-bounded scanning and Python AST hints. Directory summaries respect the admitted file set.
- `capture/git_state.py`: NUL-delimited porcelain status for staged, unstaged, renamed, and untracked paths; branch and recent commits.
- `capture/working_set.py`: combines Git, pins, and permitted runtime signals.
- `capture/chat_ingest.py` and `chat_auto_discover.py`: explicit transcript extraction/discovery. The service enforces chat persistence before indexing or saving intent.
- `core/config.py`, `policies.py`, and `redaction.py`: effective settings, optional capture gates, validated redaction expressions, and redaction before persistence.
- `storage/paths.py`: shared containment checks for stored state, scanner inputs, and restore validation.

## Commit and materialization

`storage/snapshots.py` is the snapshot repository. A single SQLite transaction inserts the snapshot payload, its canonical prompt search document, and an artifact job. SQLite is authoritative after the version-2 migration; JSON copies are derived.

Materialization atomically replaces individual JSON/Markdown files, updates the latest graph and legacy handoff, and clears completed jobs. An interrupted job remains retryable. Read APIs serve committed database records even if a JSON copy is missing or corrupt. `repair` schedules a full rebuild and synchronizes snapshot search entries. `cleanup` commits snapshot/search deletion together and queues artifact deletion.

`storage/locking.py` serializes cooperating service operations across threads and processes using a project lock outside `.infctx`. Reentrant service calls share the lock. SQLite transactions provide rollback on database failures. `core/serde.py` uses temporary files, fsync, and replacement for complete-file publication. Shared handoff files are individually replaced, not published as a single atomic tree.

## Portability

`storage/export_import.py` exports a staged copy using SQLite backup, excluding nested exports. Imports preflight bounded, normalized `.infctx` entries, extract into a staging tree, validate the staged database/configuration/snapshots, then publish with a backup and rollback. A subsequent locked operation recovers an interrupted rename gap.

An archive database replaces destination database state; it does not merge histories. Files without archive replacements retain legacy overlay behavior. Derived snapshot artifacts are reconciled afterward.

## Boundaries

The local filesystem and cooperating processes are the consistency boundary. The lock does not control old clients, direct SQLite edits, or hostile concurrent filesystem mutation. Repository capture is a best-effort view of a changing worktree. Restore validates state and never checks out source code. See [storage-format.md](storage-format.md) and [security-privacy.md](security-privacy.md).
