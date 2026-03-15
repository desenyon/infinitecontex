# Architecture

## System Components

1. Capture Engine
- Repository scanner (`capture/repo_scan.py`)
- Git state collector (`capture/git_state.py`)
- Working-set collector (`capture/working_set.py`)
- Terminal/chat ingest (`capture/terminal.py`, `capture/chat_ingest.py`)

2. Distillation Engine
- Hierarchical summarizer (`distill/summarizer.py`)
- Budget-aware packet builder

3. Storage Layer
- `.infctx/` portable filesystem layout (`storage/layout.py`)
- SQLite metadata/index store (`storage/db.py`)
- JSON snapshot artifacts

4. Retrieval + Graph
- FTS5 search index (`retrieval/search.py`)
- NetworkX context graph (`graph/store.py`)

5. Restore Engine
- Snapshot divergence analysis (`restore/engine.py`)

6. Prompt Compiler
- Target-mode prompt output (`prompt/compiler.py`)

7. Interfaces
- Typer CLI (`cli.py`)
- Python API (`api/client.py`)
- Agent tools (`agent/interface.py`)

## Storage Decision

SQLite was selected over DuckDB for deterministic local metadata workflows, mature transactional guarantees, simple portability, and built-in FTS5 support for retrieval. DuckDB remains a viable extension path for heavier analytical workloads.
