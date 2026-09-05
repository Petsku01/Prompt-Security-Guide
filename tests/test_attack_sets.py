from __future__ import annotations

import pytest

from psg.attack_sets import get_attack_type, select_attack_set
from psg.models import Attack


def test_get_attack_type_normalizes_policy_bypass_alias() -> None:
    attack = Attack(id="a1", prompt="p", metadata={"attack_type": "policy_bypass"})
    assert get_attack_type(attack) == "policy-bypass"


def test_select_attack_set_core_14() -> None:
    attacks = [Attack(id=str(i), prompt="p") for i in range(20)]
    selected = select_attack_set(attacks, "core-14")
    assert len(selected) == 14
    assert selected[0].id == "0"


def test_select_attack_set_rejects_too_small_catalog() -> None:
    attacks = [Attack(id=str(i), prompt="p") for i in range(3)]
    with pytest.raises(ValueError, match="requires at least"):
        select_attack_set(attacks, "core-14")
