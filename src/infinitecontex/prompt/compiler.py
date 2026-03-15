"""Mode-aware prompt compiler."""

from __future__ import annotations

from infinitecontex.core.models import ContextPacket, PromptMode


class PromptCompiler:
    def compile(self, packet: ContextPacket, mode: PromptMode) -> str:
        prefix = {
            PromptMode.COPILOT_RESTORE: "You are GitHub Copilot restoring repository context.",
            PromptMode.CLAUDE_CODE_RESTORE: "You are Claude Code restoring task context.",
            PromptMode.GENERIC_AGENT_RESTORE: "You are a coding agent restoring context.",
            PromptMode.HUMAN_HANDOFF: "You are a developer receiving handoff context.",
        }[mode]

        return "\n\n".join(
            [
                prefix,
                "## Project Card\n" + packet.project_card,
                "## Structural Packet\n" + packet.subsystem_packets.get("structure", ""),
                "## Behavioral Packet\n" + packet.subsystem_packets.get("behavior", ""),
                "## Working Set\n" + packet.working_set_packet,
                "## Decisions\n" + packet.decisions_packet,
                "## Restore Brief\n" + packet.restore_brief,
            ]
        ).strip()
