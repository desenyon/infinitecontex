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


def test_ingest_chat_infers_plain_transcript_signals(tmp_path: Path) -> None:
    chat = tmp_path / "chat.txt"
    chat.write_text(
        "\n".join(
            [
                "User: The original project context is mostly empty and the watch mode is confusing.",
                "Assistant: Let's replace watch with a structured live session that shows changed files.",
                "User: We need to overhaul the CLI UX and update all docs for 0.2.0.",
                (
                    "Assistant: We should keep the repo scan, git state, terminal logs, "
                    "and chat intent as balanced inputs."
                ),
                "User: Can we also fix the broken search output?",
            ]
        ),
        encoding="utf-8",
    )

    out = ingest_chat_text(chat)

    assert "overhaul the cli ux" in out["developer_goal"].lower()
    assert any("structured live session" in item.lower() for item in out["decisions"])
    assert any("update all docs" in item.lower() for item in out["active_tasks"])
    assert any("watch mode is confusing" in item.lower() for item in out["unresolved_issues"])
    assert any("fix the broken search output" in item.lower() for item in out["open_questions"])
    assert "developer_goal" in out["signal_sources"]
    assert out["signal_sources"]["decisions"]


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
