"""
Defense templates loader and manager.

Loads defense prompt templates from defense_templates/ directory
and provides utilities for combining and applying them.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass
class DefenseTemplate:
    """A defense prompt template."""

    name: str
    content: str
    filename: str
    category: str = "general"

    def __str__(self) -> str:
        return self.content


def load_templates(
    templates_dir: str | Path = "defense_templates",
) -> list[DefenseTemplate]:
    """
    Load all defense templates from directory.

    Args:
        templates_dir: Path to defense_templates directory

    Returns:
        List of DefenseTemplate objects
    """
    templates_path = Path(templates_dir)
    if not templates_path.exists():
        return []

    templates = []
    for md_file in sorted(templates_path.glob("*.md")):
        try:
            content = md_file.read_text(encoding="utf-8")
            template = parse_template(content, md_file.name)
            if template:
                templates.append(template)
        except Exception as exc:
            logging.debug("Skipping template %s: %s", md_file.name, exc)
            continue

    return templates


def _extract_code_block(content: str) -> str | None:
    """Extract the first code block from markdown content.

    Follows CommonMark spec for code fences:
    - Opening fence: 3+ backticks or tildes, optional info string (first
      word = language, rest = metadata), max 3 spaces indentation.
    - Closing fence: same fence character, >= opening fence length, no info string.
    - Nested fences inside code block handled by matching fence length.

    Returns:
        The stripped content inside the code block, or None if not found.
    """
    # Normalize CRLF to LF to avoid \r contamination in parsed content
    content = content.replace("\r\n", "\n").replace("\r", "")
    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        # CommonMark: only 0-3 spaces indentation allowed before a fence
        leading_spaces = len(line) - len(line.lstrip(" "))
        if leading_spaces > 3:
            i += 1
            continue

        stripped = line.lstrip(" ")

        # Detect opening fence: 3+ backticks or 3+ tildes
        fence_char = None
        fence_len = 0
        if stripped.startswith("```"):
            fence_char = "`"
            fence_len = len(stripped) - len(stripped.lstrip("`"))
            if fence_len < 3:
                i += 1
                continue
        elif stripped.startswith("~~~"):
            fence_char = "~"
            fence_len = len(stripped) - len(stripped.lstrip("~"))
            if fence_len < 3:
                i += 1
                continue
        else:
            i += 1
            continue

        # Info string: everything after the fence characters on the opening line.
        # CommonMark allows any text here (first word is the language, rest is
        # metadata). Previous code rejected spaces in the info string — that
        # incorrectly rejected valid fences like ```python extra.
        after_fence = stripped[fence_len:].rstrip("\n\r")
        # Info string must not contain backticks (for backtick fences) — per
        # CommonMark spec, the info string cannot contain the fence character.
        if fence_char == "`" and "`" in after_fence:
            i += 1
            continue

        # Collect lines until matching closing fence
        block_lines: list[str] = []
        j = i + 1
        found_close = False
        while j < len(lines):
            close_line = lines[j]
            close_leading = len(close_line) - len(close_line.lstrip(" "))
            close_stripped = close_line.lstrip(" ")
            # Closing fence: max 3 spaces indent, same char, >= fence_len, no info string
            if (
                close_leading <= 3
                and close_stripped.startswith(fence_char * fence_len)
            ):
                close_len = len(close_stripped) - len(close_stripped.lstrip(fence_char))
                close_rest = close_stripped[close_len:].strip()
                if close_len >= fence_len and close_rest == "":
                    found_close = True
                    break
            block_lines.append(lines[j])
            j += 1

        if found_close:
            return "\n".join(block_lines).strip()
        # If no closing fence found, skip this opening and continue
        i += 1

    return None


def parse_template(content: str, filename: str) -> DefenseTemplate | None:
    """
    Parse a defense template markdown file.

    Expected format:
        # Template Name

        ```
        The actual defense prompt text
        ```
    """
    # Extract name from first heading
    name_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    name = name_match.group(1).strip() if name_match else filename.replace(".md", "")

    # Extract content from code block (robust: handles nested backticks/tildes)
    prompt_content = _extract_code_block(content)
    if prompt_content is None:
        # Fallback: use content after first heading
        lines = content.split("\n")
        prompt_lines = []
        past_heading = False
        for line in lines:
            if line.startswith("#"):
                past_heading = True
                continue
            if past_heading:
                prompt_lines.append(line)
        prompt_content = "\n".join(prompt_lines).strip()

    if not prompt_content:
        return None

    # Categorize based on keywords
    category = categorize_template(name, prompt_content)

    return DefenseTemplate(
        name=name,
        content=prompt_content,
        filename=filename,
        category=category,
    )


def categorize_template(name: str, content: str) -> str:
    """Categorize a template based on its content."""
    text = (name + " " + content).lower()

    if any(kw in text for kw in ["jailbreak", "dan mode", "bypass"]):
        return "anti-jailbreak"
    if any(kw in text for kw in ["prompt", "instruction", "ignore previous"]):
        return "anti-injection"
    if any(kw in text for kw in ["data", "privacy", "leak", "secret"]):
        return "data-protection"
    if any(kw in text for kw in ["role", "identity", "pretend"]):
        return "identity-protection"
    if any(kw in text for kw in ["abuse", "harmful", "safety"]):
        return "safety"

    return "general"


def combine_templates(
    templates: list[DefenseTemplate],
    *,
    separator: str = "\n\n",
    max_length: int | None = None,
) -> str:
    """
    Combine multiple templates into a single defense prompt.

    Args:
        templates: Templates to combine
        separator: String to use between templates
        max_length: Maximum combined length (truncates if exceeded)

    Returns:
        Combined defense prompt string
    """
    parts = [t.content for t in templates]
    combined = separator.join(parts)

    if max_length and len(combined) > max_length:
        # Safe truncation: handle case where no space exists (e.g., long URL)
        truncated = combined[:max_length]
        last_space = truncated.rfind(" ")
        if last_space > max_length // 2:  # Only split if space is in latter half
            combined = truncated[:last_space] + "..."
        else:
            combined = truncated[: max_length - 3] + "..."

    return combined


def get_templates_by_category(
    templates: list[DefenseTemplate],
    categories: list[str],
) -> list[DefenseTemplate]:
    """Filter templates by category."""
    return [t for t in templates if t.category in categories]


def build_defense_prompt(
    base_prompt: str,
    templates: list[DefenseTemplate],
    *,
    position: str = "prepend",
    separator: str = "\n\n",
) -> str:
    """
    Build a complete prompt with defense templates.

    Args:
        base_prompt: The original system/user prompt
        templates: Defense templates to add
        position: "prepend", "append", or "wrap"
        separator: String between parts

    Returns:
        Combined prompt with defenses
    """
    defense_text = combine_templates(templates, separator=separator)

    if not defense_text:
        return base_prompt

    if position == "prepend":
        return f"{defense_text}{separator}{base_prompt}"
    elif position == "append":
        return f"{base_prompt}{separator}{defense_text}"
    elif position == "wrap":
        return f"{defense_text}{separator}{base_prompt}{separator}{defense_text}"
    else:
        return base_prompt


def list_templates(templates_dir: str | Path = "defense_templates") -> Iterator[str]:
    """List available template names."""
    for t in load_templates(templates_dir):
        yield f"[{t.category}] {t.name}"


# Pre-load templates on import for convenience
_cached_templates: list[DefenseTemplate] | None = None


def get_all_templates(
    templates_dir: str | Path = "defense_templates",
) -> list[DefenseTemplate]:
    """Get all templates (cached)."""
    global _cached_templates
    if _cached_templates is None:
        _cached_templates = load_templates(templates_dir)
    return _cached_templates


def get_recommended_templates(
    scenario: str = "general",
    templates_dir: str | Path = "defense_templates",
) -> list[DefenseTemplate]:
    """
    Get recommended templates for a scenario.

    Args:
        scenario: One of "chatbot", "agent", "rag", "api", "general"

    Returns:
        Recommended templates for the scenario
    """
    all_templates = get_all_templates(templates_dir)

    # Scenario-specific recommendations
    recommendations = {
        "chatbot": ["anti-injection", "identity-protection", "safety"],
        "agent": ["anti-injection", "anti-jailbreak", "data-protection", "safety"],
        "rag": ["anti-injection", "data-protection"],
        "api": ["anti-injection", "data-protection"],
        "general": ["anti-injection", "safety"],
    }

    categories = recommendations.get(scenario, recommendations["general"])
    return get_templates_by_category(all_templates, categories)
