You are building a production-grade software product called Infinite Context.

Core product definition:
Infinite Context is a local-first, model-agnostic, IDE-agnostic project memory engine for developers. It captures the minimum sufficient state needed to restore full AI coding context across machines, IDEs, branches, and tools with very low token usage and very high fidelity.

This is not a note-taking app, not a chat logger, and not a generic documentation tool. It is a context compiler and restore engine for real software projects.

Build the complete product from zero to deployment. Do not frame the work as an MVP. Design and implement the full system with production-grade architecture, code quality, tests, packaging, docs, security, observability, and deployment support. Make strong decisions and execute them. Do not give me milestone plans. Build the actual product structure.

Primary outcome:
A developer should be able to run Infinite Context inside a repo, generate compressed portable project context, move to a new machine or IDE, restore high-value context instantly, and feed optimized context into any AI coding agent with minimal token overhead.

Non-negotiable product goals:

1. Local-first by default.
2. Fast enough to run frequently during normal coding workflows.
3. Token-efficient by design.
4. Structured context, not raw dumps.
5. Portable across machines and IDEs.
6. Model-agnostic and agent-friendly.
7. Robust on real repos, especially Python-first codebases.
8. Extensible to other languages later.

Core capabilities:

1. Repo scan and structural analysis.
2. Git-aware change and branch analysis.
3. Working-set capture.
4. Decision memory and intent distillation.
5. Terminal and error summarization.
6. AI chat distillation through structured ingestion.
7. Context packet generation with layered summaries.
8. Restore engine that rebuilds relevant context on another machine.
9. Search and retrieval over saved context.
10. CLI-first UX, with a clean path to editor integration and agent tools.

The product must implement the following conceptual layers:

Layer A: Structural Context

- repo tree
- key files
- module and package map
- imports and exports
- entry points
- config files
- build and test definitions
- environment definitions

Layer B: Behavioral Context

- call relationships where feasible
- routes, commands, scripts, services
- test surfaces
- workflows inferred from code and config
- dataflow hints where practical

Layer C: Intent Context

- developer goal
- decisions made
- rejected options
- assumptions
- active tasks
- unresolved issues
- inferred purpose of recent changes

Layer D: Working-Set Context

- recent diffs
- active files
- current branch
- last successful and failed commands
- stack traces
- failing tests
- next likely action
- pinned files and notes

The system must generate layered outputs:

1. ultra-compact project card
2. subsystem packets
3. working-set packet
4. decisions packet
5. restore brief
6. AI-ready prompt outputs optimized for low token use

The system must store context in a portable on-disk format under a hidden project folder. Use:

- `.infctx/` as the primary local project state folder

Inside `.infctx/`, design a production-grade internal file layout that includes:

- manifest and metadata
- project identity
- snapshot records
- structured summaries
- event log
- graph data
- retrieval index
- decisions store
- working-set state
- exported prompt artifacts

Design a compact export/import format for moving project context between environments.

Required interfaces:

1. CLI
2. Python library API
3. agent/tool interface layer for future MCP-style integrations
4. optional local web dashboard only if it materially improves usability without compromising the CLI-first approach

Implement a polished CLI with commands such as, or better than:

- init
- snapshot
- restore
- status
- note
- pin
- ingest-chat
- diff-summary
- decisions
- search
- prompt
- export
- import
- doctor
- config

Do not just stub these. Implement them.

Architecture requirements:

- Use Python 3.12+
- Use a clean modular architecture with strong boundaries
- Use typed code everywhere
- Use Pydantic models for structured schemas
- Use Typer for CLI
- Use SQLite or DuckDB for local metadata storage, and justify the final choice in docs
- Use NetworkX or another pragmatic local graph layer initially, but structure the graph abstraction cleanly
- Use tree-sitter and/or language-native parsing where appropriate
- Use Git integration robustly
- Use fast serialization
- Use a file watcher or event capture mechanism where helpful
- Keep external dependencies disciplined

Design the repo carefully. Include production-ready directories for:

- src
- tests
- docs
- config
- scripts
- examples
- benchmarks
- packaging
- deployment
- CI
- generated artifacts
- editor integration scaffolding if needed

Use `.github/skills` as a first-class project asset.
Use the skills in there.

- architecture and system overview
- coding standards
- CLI behavior contract
- context model schema guide
- restore pipeline guide
- storage and file format guide
- testing strategy
- deployment and release guide
- observability and diagnostics guide
- contributor workflow guide

The implementation must include:

1. Context capture engine
2. Context distillation engine
3. Restore engine
4. Retrieval engine
5. Event logging
6. Decision memory store
7. Prompt compiler
8. Integrity validation and doctor checks
9. Export/import system
10. Configurable policies for token budget and summary granularity

Important product behavior:

- Never dump entire files unless necessary
- Prefer summaries, fingerprints, relevance rankings, and retrieval packets
- Use hierarchical summarization
- Rank relevance by recency, centrality, git activity, active workspace, errors, and explicit pins
- Support token budgets for output generation
- Support different target modes such as “copilot restore”, “claude code restore”, “generic agent restore”, and “human handoff”
- Detect divergence between saved context and current repo state during restore
- Explain what is stale, missing, changed, or still valid

Implement robust config handling:

- global user config
- repo-local config
- environment overrides
- token policy config
- summarization policy config
- include/exclude rules
- privacy rules for what can be persisted

Security and privacy requirements:

- local-first by default
- no silent external upload
- explicit boundaries around chat ingestion and shell history ingestion
- redaction support for secrets and sensitive data
- clear trust model documentation
- secure handling of project metadata

Testing requirements:

- full unit test suite
- integration tests
- golden tests for prompt output
- restore correctness tests
- graph consistency tests
- storage migration tests
- CLI tests
- performance tests for large repos
- regression tests for token budget compliance

Developer experience requirements:

- elegant CLI help text
- concise human-readable status output
- machine-readable JSON output modes
- excellent docs
- examples using realistic repos
- benchmark scripts
- clear troubleshooting flows

Observability requirements:

- structured logs
- optional verbose/debug trace modes
- timing metrics for major pipeline stages
- diagnostics output
- doctor command to identify parser, git, config, storage, and indexing issues

Documentation requirements:
Create complete production-grade docs, including:

- overview
- architecture
- mental model
- storage format
- config reference
- CLI reference
- data model reference
- how restore works
- token optimization strategy
- security and privacy model
- troubleshooting
- contributor guide
- release and versioning policy

Packaging and release requirements:

- pyproject.toml
- production-ready dependency management
- lockfile strategy
- install instructions
- wheel/sdist support if appropriate
- versioning strategy
- release automation
- changelog approach
- CI pipeline
- linting, typing, testing, packaging checks

Deployment requirements:
This is primarily a local developer tool, but still prepare a deployment-ready distribution path:

- package distribution
- optional Homebrew or equivalent install path if appropriate
- GitHub Actions CI/CD
- release artifacts
- docs publishing
- optional local service mode if architecturally justified

Code quality requirements:

- strong separation of concerns
- no giant god modules
- clear interfaces
- comments only where they add real value
- high-quality docstrings
- thoughtful naming
- no placeholder architecture
- no fake implementations
- no pseudocode in final code
- no TODO litter unless tied to real extension points

Decision-making requirements:
When tradeoffs exist, choose for reliability, clarity, speed, and maintainability. Document key decisions in the repo. Keep the system elegant and practical.

Now execute the build by doing all of the following:

1. Design the full architecture.
2. Create the repo layout.
3. Implement the code.
4. Implement tests.
5. Implement docs.
6. Implement CI/CD.
7. Implement packaging and release setup.
8. use `.github/skills`.
9. Implement sample configs and examples.
10. Ensure the system is coherent end to end.

As you build:

- keep everything production-grade
- keep the CLI polished
- keep outputs low-token and highly useful
- keep the architecture extensible for future editor integrations and agent interfaces

The final result should feel like a serious developer infrastructure product, not a prototype.
