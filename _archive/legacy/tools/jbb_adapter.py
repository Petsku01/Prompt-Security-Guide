#!/usr/bin/env python3
"""
JailbreakBench Adapter - Convert JBB behaviors to attack_catalog format.

This adapter allows unified_tester_v2.py to use JailbreakBench behaviors
as attack prompts, providing academic-grade testing.
"""

import json
from pathlib import Path
from typing import Dict, List, Any

# Severity mapping based on JBB categories
CATEGORY_SEVERITY = {
    "Harassment/Discrimination": "HIGH",
    "Malware/Hacking": "CRITICAL", 
    "Physical harm": "CRITICAL",
    "Economic harm": "HIGH",
    "Disinformation": "HIGH",
    "Fraud/Deception": "HIGH",
    "Illegal Activity": "CRITICAL",
    "Drug-related": "CRITICAL",
    "CSAM": "CRITICAL",
}

def convert_jbb_to_catalog(jbb_path: Path) -> Dict[str, Any]:
    """Convert JBB behaviors JSON to attack_catalog format."""
    
    with open(jbb_path) as f:
        jbb_data = json.load(f)
    
    attacks = []
    for behavior in jbb_data.get("attacks", []):
        category = behavior.get("category", "Unknown")
        
        attack = {
            "id": behavior.get("id", "JBB-XX"),
            "category": category.lower().replace("/", "_").replace(" ", "_"),
            "severity": CATEGORY_SEVERITY.get(category, "HIGH"),
            "tags": [
                "jailbreakbench",
                behavior.get("source", "unknown").lower(),
                category.lower().replace("/", "_").replace(" ", "_")
            ],
            "prompt": behavior.get("prompt", ""),
            "goal": behavior.get("goal", "Bypass safety and generate harmful content"),
            "success_criteria": behavior.get("success_criteria", "Model produces harmful content")
        }
        attacks.append(attack)
    
    return {
        "version": "JBB-adapted-1.0",
        "source": jbb_data.get("source", "JailbreakBench"),
        "description": "JailbreakBench behaviors converted to attack_catalog format",
        "attacks": attacks
    }


def create_combined_catalog(
    original_catalog_path: Path,
    jbb_path: Path,
    output_path: Path
) -> Dict[str, Any]:
    """Combine original catalog with JBB behaviors."""
    
    # Load original
    with open(original_catalog_path) as f:
        original = json.load(f)
    
    # Convert JBB
    jbb_catalog = convert_jbb_to_catalog(jbb_path)
    
    # Combine
    combined = {
        "version": "combined-2.0",
        "sources": [
            original.get("source", "original"),
            jbb_catalog.get("source", "JailbreakBench")
        ],
        "description": "Combined attack catalog with JailbreakBench behaviors",
        "attacks": original.get("attacks", []) + jbb_catalog.get("attacks", [])
    }
    
    # Deduplicate by similar prompts (simple check)
    seen_prompts = set()
    unique_attacks = []
    for attack in combined["attacks"]:
        prompt_key = attack["prompt"][:100].lower()
        if prompt_key not in seen_prompts:
            seen_prompts.add(prompt_key)
            unique_attacks.append(attack)
    
    combined["attacks"] = unique_attacks
    
    # Save
    with open(output_path, "w") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)
    
    return combined


if __name__ == "__main__":
    import sys
    
    base_dir = Path(__file__).parent.parent
    
    if len(sys.argv) > 1 and sys.argv[1] == "convert":
        # Just convert JBB to catalog format
        jbb_path = base_dir / "jbb_behaviors.json"
        output_path = base_dir / "attack_catalog_jbb.json"
        
        catalog = convert_jbb_to_catalog(jbb_path)
        with open(output_path, "w") as f:
            json.dump(catalog, f, indent=2, ensure_ascii=False)
        
        print(f"Converted {len(catalog['attacks'])} JBB behaviors to {output_path}")
    
    elif len(sys.argv) > 1 and sys.argv[1] == "combine":
        # Combine original + JBB
        original_path = base_dir / "attack_catalog.json"
        jbb_path = base_dir / "jbb_behaviors.json"
        output_path = base_dir / "attack_catalog_combined.json"
        
        combined = create_combined_catalog(original_path, jbb_path, output_path)
        
        print(f"Combined catalog created with {len(combined['attacks'])} attacks")
        print(f"Output: {output_path}")
    
    else:
        print("Usage:")
        print("  python jbb_adapter.py convert  - Convert JBB to catalog format")
        print("  python jbb_adapter.py combine  - Combine original + JBB catalogs")
