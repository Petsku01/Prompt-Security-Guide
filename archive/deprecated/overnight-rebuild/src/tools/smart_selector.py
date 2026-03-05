#!/usr/bin/env python3
"""
Smart Selector - Intelligent Attack Selection
==============================================

ASSUMPTIONS:
1. processed/top_quality.json exists with categorized prompts
2. processed/llm_classified.json may exist with ML classifications
3. Model fingerprinting uses simple name matching
4. Higher sophistication = better attack

POTENTIAL CONCERNS:
1. Model family detection is heuristic-based
2. May miss model-specific attacks if categories don't match
3. Large prompt file could use significant memory

Author: Kuu (SE methodology)
Date: 2026-03-04
"""

import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Dict
import logging
import random

logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

PROCESSED_DIR = Path(__file__).parent.parent / "processed"
TOP_QUALITY_FILE = PROCESSED_DIR / "top_quality.json"
ML_CLASSIFIED_FILE = PROCESSED_DIR / "llm_classified.json"

# Model family mappings
MODEL_FAMILIES = {
    'llama': ['llama', 'llama2', 'llama3', 'codellama'],
    'mistral': ['mistral', 'mixtral'],
    'qwen': ['qwen', 'qwen2', 'qwen2.5'],
    'gemma': ['gemma', 'gemma2'],
    'phi': ['phi', 'phi2', 'phi3'],
    'gpt': ['gpt', 'chatgpt', 'openai'],
    'claude': ['claude', 'anthropic', 'sonnet', 'opus'],
    'deepseek': ['deepseek'],
    'stablelm': ['stablelm', 'stable-lm'],
}


# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class Attack:
    """Represents a single attack to run."""
    id: str
    prompt: str
    technique: str
    category: str
    target_model: str
    sophistication: int
    novelty: int
    source: str


# ============================================================
# MODEL FINGERPRINTING
# ============================================================

def detect_model_family(model_name: str) -> str:
    """
    Detect model family from model name.
    Returns family name or 'generic'.
    """
    model_lower = model_name.lower()
    
    for family, patterns in MODEL_FAMILIES.items():
        if any(p in model_lower for p in patterns):
            return family
    
    return 'generic'


# ============================================================
# PROMPT LOADING
# ============================================================

def load_prompts() -> List[Dict]:
    """Load prompts from processed files."""
    prompts = []
    
    # Try ML-classified first (better quality)
    if ML_CLASSIFIED_FILE.exists():
        try:
            with open(ML_CLASSIFIED_FILE) as f:
                data = json.load(f)
            
            for item in data.get('classifications', []):
                classification = item.get('classification', {})
                prompts.append({
                    'id': item.get('id', ''),
                    'text': item.get('text_preview', ''),  # Note: truncated
                    'technique': classification.get('technique', 'unknown'),
                    'category': classification.get('category', 'other'),
                    'target_model': classification.get('target_model', 'generic'),
                    'sophistication': classification.get('sophistication', 3),
                    'novelty': classification.get('novelty', 3),
                    'source': 'ml_classified',
                })
            
            logger.info(f"Loaded {len(prompts)} ML-classified prompts")
        except Exception as e:
            logger.warning(f"Could not load ML-classified: {e}")
    
    # Fall back to top_quality.json
    if not prompts and TOP_QUALITY_FILE.exists():
        try:
            with open(TOP_QUALITY_FILE) as f:
                data = json.load(f)
            
            for item in data.get('prompts', []):
                prompts.append({
                    'id': item.get('id', ''),
                    'text': item.get('text', ''),
                    'technique': item.get('technique', 'unknown'),
                    'category': item.get('category', 'other'),
                    'target_model': item.get('target_model', 'generic'),
                    'sophistication': item.get('sophistication_score', 3),
                    'novelty': item.get('novelty_score', 3),
                    'source': 'top_quality',
                })
            
            logger.info(f"Loaded {len(prompts)} top_quality prompts")
        except Exception as e:
            logger.warning(f"Could not load top_quality: {e}")
    
    return prompts


# ============================================================
# SELECTION LOGIC
# ============================================================

def select_attacks(
    model_name: str,
    technique: Optional[str] = None,
    max_count: int = 50,
    min_sophistication: int = 3,
    thorough: bool = False
) -> List[Attack]:
    """
    Select attacks for a target model.
    
    Args:
        model_name: Name of model to test (e.g., "llama3:8b")
        technique: Filter by specific technique (optional)
        max_count: Maximum number of attacks to return
        min_sophistication: Minimum sophistication score (1-5)
        thorough: If True, include more attacks and vary selection
        
    Returns:
        List of Attack objects to run
    """
    # Detect model family
    model_family = detect_model_family(model_name)
    logger.info(f"Detected model family: {model_family} for {model_name}")
    
    # Load all prompts
    all_prompts = load_prompts()
    if not all_prompts:
        logger.error("No prompts available!")
        return []
    
    # Filter prompts
    filtered = []
    for p in all_prompts:
        # Sophistication filter
        if p['sophistication'] < min_sophistication:
            continue
        
        # Technique filter
        if technique and p['technique'] != technique:
            continue
        
        # Model matching (prefer model-specific, include generic)
        prompt_target = p.get('target_model', 'generic')
        if prompt_target not in [model_family, 'generic']:
            # Lower priority for non-matching models
            if not thorough:
                continue
        
        filtered.append(p)
    
    logger.info(f"Filtered to {len(filtered)} prompts")
    
    # Sort by priority
    def priority_score(p):
        score = p['sophistication'] * 2 + p['novelty']
        # Bonus for model-specific
        if p.get('target_model') == model_family:
            score += 5
        return score
    
    filtered.sort(key=priority_score, reverse=True)
    
    # Select top N
    if thorough:
        # In thorough mode, select more and randomize slightly
        selected = filtered[:max_count * 2]
        random.shuffle(selected)
        selected = selected[:max_count]
    else:
        selected = filtered[:max_count]
    
    # Convert to Attack objects
    attacks = []
    for p in selected:
        attacks.append(Attack(
            id=p['id'],
            prompt=p['text'],
            technique=p['technique'],
            category=p['category'],
            target_model=p.get('target_model', 'generic'),
            sophistication=p['sophistication'],
            novelty=p.get('novelty', 3),
            source=p.get('source', 'unknown'),
        ))
    
    logger.info(f"Selected {len(attacks)} attacks for {model_name}")
    return attacks


# ============================================================
# TESTING
# ============================================================

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    print("=== Smart Selector Test ===\n")
    
    # Test selection
    attacks = select_attacks("llama3:8b", max_count=10)
    
    print(f"Selected {len(attacks)} attacks for llama3:8b:\n")
    for i, attack in enumerate(attacks[:5], 1):
        print(f"{i}. [{attack.technique}] soph={attack.sophistication}")
        print(f"   {attack.prompt[:80]}...")
        print()
