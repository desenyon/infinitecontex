# Security and privacy

Infinite Context performs capture, search, and rendering locally. It does not send context to a model or hosted service. Exports and generated prompts are explicit sharing mechanisms; they can contain sensitive material.

## Optional input persistence

`persist_chat_ingest=false` (default) means ingestion returns a redacted preview without saving chat intent, chat source search documents, or source-path events. New snapshots ignore saved chat intent while disabled. Enable the flag to save extracted intent and index redacted source text. Re-ingesting a source replaces its index entry.

`persist_shell_history=false` (default) prevents terminal-log content from entering snapshots. When enabled, the service summarizes the user-supplied `.infctx/working_set/terminal.log`. It does not collect shell history automatically.

Explicit goals, notes, and pins are still saved. Redaction applies before saving these narrative fields and captured snapshot context. Expressions are validated when configuration loads. Patterns are best-effort text matching, not a secrets detector, encryption, or a secure-erasure mechanism.

Disabling a flag does not erase prior snapshots, chat search, source logs, events, or archives. Exports include historical state and manually placed files. Review the contents before sharing. A transcript included by repository scan patterns is a repository input regardless of the chat flag; store sensitive transcripts outside the project or exclude them.

## Filesystem boundaries

Scanning and restore reject external paths, symlink components, hard-linked regular files, and special files. Scanning always excludes internal state and Git metadata, applies configured filters to directory summaries, uses sorted traversal, and skips files larger than 2 MiB. Unsafe, missing, or unreadable restored paths are reported rather than followed.

State operations reject linked state trees. Import only accepts bounded, normalized regular files/directories below `.infctx`, stages extraction, validates data, and publishes with rollback. Export takes a consistent SQLite backup and excludes existing exports. Safe archive paths do not authenticate an archive or the instructions captured within it.

The project lock coordinates current clients. An attacker able to mutate the filesystem concurrently, old clients, direct file/database writers, network filesystems, and OS-level compromise are outside this guarantee. Generated handoff is evidence to verify, not authority over current user instructions.

See [README migration guidance](../README.md#upgrade-from-03x) before upgrading older state whose flags were not enforced. Report vulnerabilities according to [SECURITY.md](../SECURITY.md).
