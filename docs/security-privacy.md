# Security And Privacy Model

Trust model:

- All data remains local unless user explicitly exports archives.
- No automatic network exfiltration.

Sensitive data controls:

- Policy flags for shell and chat persistence.
- Redaction pattern support in privacy policy.
- Explicit ingestion commands for chat/terminal-derived state.

Operational guidance:

- Do not ingest secrets-heavy logs by default.
- Use repo-local config to tighten persistence boundaries for sensitive projects.
