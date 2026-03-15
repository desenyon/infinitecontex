# Token Optimization Strategy

Principles:

- Never dump full file contents by default.
- Rank and summarize, then truncate to token budget.
- Keep layered context separate so irrelevant layers can be omitted.

Heuristics:

- Prioritize project card + working-set + restore brief.
- Include structural and behavioral summaries only if budget allows.
- Approximate tokens with low-cost text-length heuristics during compile.

Modes:

- `copilot-restore`
- `claude-code-restore`
- `generic-agent-restore`
- `human-handoff`
