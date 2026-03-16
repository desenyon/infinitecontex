# Overview

Infinite Context is a structured workflow CLI for preserving project state across agent sessions, branch switches, and interrupted work.

Core outcomes:

- Capture repository structure, behavior, working-set state, runtime failures, and developer intent.
- Keep everything local under `.infctx/`.
- Generate compact prompts and handoff files from the same snapshot source of truth.
- Make live context refresh understandable through `session`, not hidden watcher behavior.

Primary interfaces:

- CLI: `infctx`
- Python API: `InfiniteContextClient`
- Agent artifacts: `.infctx/agents/*.md`

Product stance:

- Local-first by default
- Deterministic outputs over opaque heuristics
- Structured summaries over noisy raw dumps
- Human-readable UX without losing scriptable `--json` output
