"""Hierarchical summarization primitives for low-token packets."""

from __future__ import annotations

from infinitecontex.core.models import ContextPacket, Snapshot


def _truncate_lines(lines: list[str], max_items: int) -> list[str]:
    return lines[:max_items]


def _estimate_tokens(text: str) -> int:
    # Rough approximation: ~4 chars/token for English technical text.
    return max(1, int(len(text) / 4))


def _fit_budget(sections: list[str], budget: int) -> list[str]:
    kept: list[str] = []
    used = 0
    for section in sections:
        tokens = _estimate_tokens(section)
        if used + tokens > budget:
            break
        kept.append(section)
        used += tokens
    return kept


def compile_packet(snapshot: Snapshot, budget: int) -> ContextPacket:
    project_card = (
        f"Project root: {snapshot.project_root}\n"
        f"Branch: {snapshot.working_set.branch}\n"
        f"Goal: {snapshot.intent.developer_goal or 'n/a'}\n"
        f"Top dirs: {', '.join(snapshot.structural.repo_tree_top[:10])}"
    )

    subsystem_packets = {
        "structure": "\n".join(
            [
                "Key files:",
                *[f"- {p}" for p in _truncate_lines(snapshot.structural.key_files, 20)],
                "Entry points:",
                *[f"- {p}" for p in _truncate_lines(snapshot.structural.entry_points, 10)],
            ]
        ),
        "behavior": "\n".join(
            [
                "Test surfaces:",
                *[f"- {p}" for p in _truncate_lines(snapshot.behavioral.test_surfaces, 20)],
                "Routes/commands:",
                *[f"- {p}" for p in _truncate_lines(snapshot.behavioral.routes_or_commands, 20)],
            ]
        ),
    }

    working_set_packet = "\n".join(
        [
            "Active files:",
            *[f"- {p}" for p in _truncate_lines(snapshot.working_set.active_files, 20)],
            "Recent diffs:",
            *[f"- {d}" for d in _truncate_lines(snapshot.working_set.recent_diffs, 20)],
            "Next action:",
            snapshot.working_set.next_likely_action,
        ]
    )

    decisions_packet = "\n".join(
        ["Decisions:", *[f"- {d}" for d in _truncate_lines(snapshot.intent.decisions, 20)]]
    )

    restore_brief = "\n".join(
        [
            "Restore checklist:",
            "1) verify branch and changed files",
            "2) inspect failing tests and stack traces",
            "3) continue from next likely action",
            f"Pinned files: {', '.join(snapshot.working_set.pins[:10]) or 'none'}",
        ]
    )

    sections = [project_card, *subsystem_packets.values(), working_set_packet, decisions_packet, restore_brief]
    kept = _fit_budget(sections, budget)

    if not kept:
        # Always keep at least a compact project card.
        kept = [project_card[: max(120, budget * 4)]]

    # Build packet from kept sections while preserving shape.
    while len(kept) < 6:
        kept.append("")

    return ContextPacket(
        project_card=kept[0],
        subsystem_packets={"structure": kept[1], "behavior": kept[2]},
        working_set_packet=kept[3],
        decisions_packet=kept[4],
        restore_brief=kept[5],
    )
