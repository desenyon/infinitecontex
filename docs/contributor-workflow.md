# Contributor Workflow Guide

1. Create branch.
2. Implement change with tests.
3. Run `ruff check .`, `mypy src`, `pytest`.
4. Validate CLI behavior manually for affected commands.
5. Update docs for any behavior or schema changes.
6. Submit PR with decision notes when tradeoffs were made.

Decision memory hygiene:

- Use `infctx note` for key architectural decisions.
- Keep rationale and alternatives explicit.
