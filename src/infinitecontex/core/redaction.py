"""Sensitive data redaction helpers."""

from __future__ import annotations

import re


def redact_text(text: str, patterns: list[str]) -> str:
    redacted = text
    for pattern in patterns:
        redacted = re.sub(pattern, "[REDACTED]", redacted)
    return redacted


def redact_list(values: list[str], patterns: list[str]) -> list[str]:
    return [redact_text(v, patterns) for v in values]
