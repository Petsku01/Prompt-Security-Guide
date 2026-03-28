"""
Defense templates loader and manager.

Loads defense prompt templates from defense_templates/ directory
and provides utilities for combining and applying them.
"""
from __future__ import annotations

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
        except Exception:
            continue
    
    return templates


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
    name_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    name = name_match.group(1).strip() if name_match else filename.replace(".md", "")
    
    # Extract content from code block
    code_match = re.search(r'```\n?(.*?)```', content, re.DOTALL)
    if code_match:
        prompt_content = code_match.group(1).strip()
    else:
        # Fallback: use content after first heading
        lines = content.split('\n')
        prompt_lines = []
        past_heading = False
        for line in lines:
            if line.startswith('#'):
                past_heading = True
                continue
            if past_heading:
                prompt_lines.append(line)
        prompt_content = '\n'.join(prompt_lines).strip()
    
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
        combined = combined[:max_length].rsplit(" ", 1)[0] + "..."
    
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


def get_all_templates(templates_dir: str | Path = "defense_templates") -> list[DefenseTemplate]:
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
