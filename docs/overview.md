# Overview

Infinite Context compiles project state into portable, layered context packets optimized for low-token AI handoff.

Core outcomes:

- Capture structural, behavioral, intent, and working-set context.
- Persist state locally in `.infctx/`.
- Restore context fidelity across machines, IDEs, branches, and agents.
- Generate agent-specific restore prompts under strict token budgets.

Primary interfaces:

- CLI (`infctx`)
- Python API (`InfiniteContextClient`)
- Agent tool interface (`AgentToolInterface`)

Product stance:

- Local-first by default.
- No silent external upload.
- Structured context over raw dumps.
- Fast, repeatable snapshots during normal coding flow.
