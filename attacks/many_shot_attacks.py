"""
Many-Shot Jailbreak Attack Generator

Based on Anthropic's research on many-shot jailbreaking (2024):
https://www.anthropic.com/research/many-shot-jailbreaking

This technique exploits long context windows by filling them with fictional
Q&A pairs where the "assistant" provides policy-violating answers. The model
learns from these in-context examples and follows the pattern.

Key findings from research:
- Effectiveness scales with number of shots (log-linear relationship)
- Works across multiple model families
- More effective with longer contexts
- Can be combined with other techniques

For security testing and red-teaming purposes only.
"""

import json
from typing import List, Dict, Any
from pathlib import Path


def generate_shot_pair(question: str, answer: str) -> str:
    """Generate a single Q&A shot in conversation format."""
    return f"""Human: {question}