from __future__ import annotations

from infinitecontex.core.redaction import redact_text


def test_redact_text_masks_secret_patterns() -> None:
    text = "api_key=abc123 token=foo password=bar"
    patterns = [
        r"(?i)api[_-]?key\s*[:=]\s*\S+",
        r"(?i)token\s*[:=]\s*\S+",
        r"(?i)password\s*[:=]\s*\S+",
    ]
    out = redact_text(text, patterns)
    assert "abc123" not in out
    assert "foo" not in out
    assert "bar" not in out
    assert out.count("[REDACTED]") == 3
