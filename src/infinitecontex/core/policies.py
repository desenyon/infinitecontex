"""Token and summarization policy models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TokenPolicy(BaseModel):
    default_budget: int = 1200
    min_budget: int = 300
    max_budget: int = 16_000


class SummarizationPolicy(BaseModel):
    file_snippet_max_lines: int = 40
    max_recent_diffs: int = 20
    max_key_files: int = 30
    max_active_files: int = 25


class PrivacyPolicy(BaseModel):
    persist_shell_history: bool = False
    persist_chat_ingest: bool = False
    redact_patterns: list[str] = Field(
        default_factory=lambda: [
            r"(?i)api[_-]?key\s*[:=]\s*\S+",
            r"(?i)token\s*[:=]\s*\S+",
            r"(?i)password\s*[:=]\s*\S+",
        ]
    )


class RuntimePolicies(BaseModel):
    token: TokenPolicy = Field(default_factory=TokenPolicy)
    summarization: SummarizationPolicy = Field(default_factory=SummarizationPolicy)
    privacy: PrivacyPolicy = Field(default_factory=PrivacyPolicy)
