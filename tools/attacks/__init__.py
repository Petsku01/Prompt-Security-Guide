"""Attack modules"""
from .base import Attack
from . import aggressive, classic, emotional, plinius, novel

# Collect all attacks from all modules
ALL_ATTACKS = []
ALL_ATTACKS.extend(aggressive.ATTACKS)
ALL_ATTACKS.extend(classic.ATTACKS)
ALL_ATTACKS.extend(emotional.ATTACKS)
ALL_ATTACKS.extend(plinius.ATTACKS)
ALL_ATTACKS.extend(novel.ATTACKS)

# Category-based access
ATTACKS_BY_CATEGORY = {}
for attack in ALL_ATTACKS:
    if attack.category not in ATTACKS_BY_CATEGORY:
        ATTACKS_BY_CATEGORY[attack.category] = []
    ATTACKS_BY_CATEGORY[attack.category].append(attack)


def get_attacks(categories: list = None, sources: list = None) -> list:
    """Get attacks filtered by category and/or source"""
    result = ALL_ATTACKS
    
    if categories:
        result = [a for a in result if a.category in categories]
    
    if sources:
        result = [a for a in result if a.source in sources]
    
    return result


def list_categories() -> list:
    """List all available attack categories"""
    return sorted(ATTACKS_BY_CATEGORY.keys())


def count_attacks() -> dict:
    """Return attack counts by category"""
    return {cat: len(attacks) for cat, attacks in ATTACKS_BY_CATEGORY.items()}


__all__ = ["Attack", "ALL_ATTACKS", "ATTACKS_BY_CATEGORY", "get_attacks", "list_categories", "count_attacks"]
