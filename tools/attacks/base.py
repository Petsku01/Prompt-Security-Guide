"""Base attack definition"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class Attack:
    """Standardized attack definition"""
    id: str
    name: str
    category: str
    prompt: str
    indicators: List[str] = field(default_factory=list)
    goal: str = ""  # Description of what the attack tries to achieve
    source: str = ""  # Where this attack came from (paper, repo, etc.)
