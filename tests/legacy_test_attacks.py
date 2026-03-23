"""Tests for attack definitions."""
from tools.attacks import ALL_ATTACKS, get_attacks, list_categories


class TestAttackIntegrity:
    """Validate attack definitions are well-formed."""

    def test_all_attacks_have_required_fields(self):
        """Every attack must have id, name, category, prompt."""
        for attack in ALL_ATTACKS:
            assert attack.id, f"Attack missing id: {attack}"
            assert attack.name, f"Attack {attack.id} missing name"
            assert attack.category, f"Attack {attack.id} missing category"
            assert attack.prompt, f"Attack {attack.id} missing prompt"

    def test_attack_ids_are_unique(self):
        """No duplicate attack IDs."""
        ids = [a.id for a in ALL_ATTACKS]
        assert len(ids) == len(set(ids)), "Duplicate attack IDs found"

    def test_get_attacks_filters_by_category(self):
        """get_attacks respects category filter."""
        categories = list_categories()
        if categories:
            cat = categories[0]
            filtered = get_attacks(categories=[cat])
            assert all(a.category == cat for a in filtered)

    def test_all_categories_have_attacks(self):
        """Every listed category has at least one attack."""
        for cat in list_categories():
            attacks = get_attacks(categories=[cat])
            assert len(attacks) > 0, f"Category {cat} has no attacks"
