# Storage And File Format Guide

Primary state root: `.infctx/`

- `metadata/manifest.json`: schema and storage metadata.
- `metadata/state.db`: SQLite metadata, decisions, events, pins, retrieval FTS index.
- `project/`: project identity metadata.
- `snapshots/*.json`: canonical snapshot records.
- `summaries/`: restore summaries and derived artifacts.
- `events/events.jsonl`: structured event log.
- `graph/context_graph.json`: node-link graph data.
- `retrieval/`: retrieval-related assets.
- `decisions/`: decision artifacts (extensible).
- `working_set/`: terminal and intent state.
- `prompts/*.md`: compiled prompt outputs.
- `exports/*.tgz`: portable exports.

Export format: gzip tarball containing only `.infctx/`, allowing direct import on another machine.
