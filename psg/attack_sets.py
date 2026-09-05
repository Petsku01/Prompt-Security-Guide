from __future__ import annotations

from .models import Attack

ATTACK_TYPE_OBEDIENCE = "obedience"
ATTACK_TYPE_POLICY_BYPASS = "policy-bypass"
_ATTACK_SET_SIZES: dict[str, int | None] = {
    "all": None,
    "core-14": 14,
    "full-61": 61,
}


class AttackSetSizeError(ValueError):
    def __init__(self, attack_set: str, required: int, actual: int) -> None:
        self.attack_set = attack_set
        self.required = required
        self.actual = actual
        super().__init__(
            f"attack set '{attack_set}' requires at least {required} attacks, got {actual}"
        )


def normalize_attack_type(value: object) -> str:
    if not isinstance(value, str):
        return ATTACK_TYPE_POLICY_BYPASS
    normalized = value.strip().lower().replace("_", "-")
    if normalized == ATTACK_TYPE_OBEDIENCE:
        return ATTACK_TYPE_OBEDIENCE
    if normalized == ATTACK_TYPE_POLICY_BYPASS:
        return ATTACK_TYPE_POLICY_BYPASS
    return ATTACK_TYPE_POLICY_BYPASS


def get_attack_type(attack: Attack) -> str:
    return normalize_attack_type(attack.metadata.get("attack_type"))


def select_attack_set(attacks: list[Attack], attack_set: str) -> list[Attack]:
    if attack_set not in _ATTACK_SET_SIZES:
        valid = ", ".join(sorted(_ATTACK_SET_SIZES))
        raise ValueError(f"unknown attack set: {attack_set} (valid: {valid})")
    size = _ATTACK_SET_SIZES[attack_set]
    if size is None:
        return attacks
    if len(attacks) < size:
        raise AttackSetSizeError(attack_set, size, len(attacks))
    return attacks[:size]
