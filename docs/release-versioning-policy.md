# Release And Versioning Policy

Versioning follows SemVer.

- PATCH: bug fixes and documentation corrections without meaningful interface change
- MINOR: backward-compatible command additions, workflow improvements, and capture enhancements
- MAJOR: breaking CLI, JSON, or storage changes

`0.2.0` establishes the structured workflow release line:

- `session` becomes the primary live command
- `watch` becomes a compatibility alias
- snapshot capture becomes explicitly layered
- intent ingestion and status output become richer and more transparent

Release notes should call out:

- command-surface changes
- JSON payload additions
- storage schema or migration implications
- docs updated for the release
