from __future__ import annotations

from pathlib import Path

from infinitecontex.capture.chat_ingest import ingest_chat_text
from infinitecontex.capture.terminal import summarize_terminal_log


def test_ingest_chat_extracts_signals(tmp_path: Path) -> None:
    chat = tmp_path / "chat.txt"
    chat.write_text(
        "\n".join(
            [
                "goal: ship release",
                "decision: use sqlite",
                "assumption: local-first only",
                "task: add tests",
                "Build failed in CI",
            ]
        ),
        encoding="utf-8",
    )
    out = ingest_chat_text(chat)
    assert out["developer_goal"] == "ship release"
    assert out["decisions"]
    assert out["active_tasks"]
    assert out["unresolved_issues"]


def test_terminal_summary_extracts_failures(tmp_path: Path) -> None:
    log = tmp_path / "term.log"
    log.write_text(
        "\n".join(
            [
                "pytest success exit 0",
                "Traceback (most recent call last)",
                "tests::test_x failed",
                "command failed exit 1",
            ]
        ),
        encoding="utf-8",
    )
    out = summarize_terminal_log(log)
    assert out["successful"]
    assert out["failed"]
    assert out["stack_traces"]
    assert out["failing_tests"]
