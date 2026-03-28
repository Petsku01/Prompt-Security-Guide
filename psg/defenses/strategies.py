from __future__ import annotations

from enum import Enum


class InstructionLevel(str, Enum):
    SYSTEM = "system"
    DEVELOPER = "developer"
    USER = "user"
    EXTERNAL = "external"


PRIORITY_ORDER: dict[InstructionLevel, int] = {
    InstructionLevel.SYSTEM: 0,
    InstructionLevel.DEVELOPER: 1,
    InstructionLevel.USER: 2,
    InstructionLevel.EXTERNAL: 3,
}


def recommend_defense_strategy(
    *,
    high_risk_actions: bool = False,
    external_content: bool = False,
    needs_tool_use: bool = False,
) -> list[str]:
    """
    Returns pragmatic defense recommendations.

    These are risk mitigations only; no strategy fully eliminates prompt injection.
    """
    recommendations = [
        "Apply layered input and output validation.",
        "Log prompts/responses and monitor for adaptive attacks.",
    ]
    if external_content:
        recommendations.append("Treat external content as untrusted and isolate it from privileged instructions.")
    if needs_tool_use:
        recommendations.append("Use least-privilege tool permissions with explicit allowlists.")
    if high_risk_actions:
        recommendations.append("Require human approval for high-impact actions.")
    return recommendations


def sort_by_instruction_hierarchy(
    instructions: list[tuple[InstructionLevel, str]],
) -> list[tuple[InstructionLevel, str]]:
    """Sorts instructions so higher-trust levels are handled first."""
    return sorted(instructions, key=lambda item: PRIORITY_ORDER[item[0]])


def conflict_with_higher_priority(
    trusted_instruction: str,
    untrusted_instruction: str,
) -> bool:
    """
    Heuristic helper for hierarchy checks.

    This does not prove semantic conflict; it catches common override wording.
    """
    trusted = trusted_instruction.lower()
    untrusted = untrusted_instruction.lower()

    asks_to_override = any(token in untrusted for token in ("ignore", "override", "forget previous"))
    references_policy = any(token in trusted for token in ("must", "never", "policy", "do not"))
    return asks_to_override and references_policy
