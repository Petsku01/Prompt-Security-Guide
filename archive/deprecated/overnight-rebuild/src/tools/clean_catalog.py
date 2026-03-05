#!/usr/bin/env python3
"""
Clean top_quality.json - Remove garbage prompts.
SE methodology: surgical, documented, reversible.
"""

import json
import re
from pathlib import Path
from datetime import datetime

PROCESSED_DIR = Path(__file__).parent.parent / "processed"
INPUT_FILE = PROCESSED_DIR / "top_quality.json"
OUTPUT_FILE = PROCESSED_DIR / "top_quality_clean.json"
REJECTED_FILE = PROCESSED_DIR / "rejected_prompts.json"
REPORT_FILE = PROCESSED_DIR / "cleanup_report.md"

# HTML patterns to detect garbage
HTML_PATTERNS = [
    r'<html', r'<div', r'<script', r'<style', r'<head', r'<body',
    r'<span', r'<table', r'<form', r'<!DOCTYPE', r'<meta',
    r'class="', r'href="http', r'xmlns='
]

def is_html_garbage(text: str) -> bool:
    """Check if text contains HTML garbage."""
    text_lower = text.lower()
    for pattern in HTML_PATTERNS:
        if pattern.lower() in text_lower:
            return True
    return False

def is_too_short(text: str, min_length: int = 50) -> bool:
    """Check if prompt is too short to be useful."""
    return len(text.strip()) < min_length

def is_too_long(text: str, max_length: int = 15000) -> bool:
    """Check if prompt is suspiciously long (likely garbage)."""
    return len(text) > max_length

def clean_prompts(prompts: list) -> tuple[list, list, dict]:
    """
    Clean prompts and return (clean, rejected, stats).
    """
    clean = []
    rejected = []
    seen_hashes = set()
    
    stats = {
        "total": len(prompts),
        "html_garbage": 0,
        "too_short": 0,
        "too_long": 0,
        "duplicates": 0,
        "kept": 0,
        "techniques": {}
    }
    
    for p in prompts:
        text = p.get("text", p.get("prompt", ""))
        text_hash = p.get("text_hash", "")
        is_dup = p.get("is_duplicate", False)
        technique = p.get("technique", "unknown")
        
        reject_reason = None
        
        # Check rejection criteria
        if is_dup or (text_hash and text_hash in seen_hashes):
            reject_reason = "duplicate"
            stats["duplicates"] += 1
        elif is_html_garbage(text):
            reject_reason = "html_garbage"
            stats["html_garbage"] += 1
        elif is_too_short(text):
            reject_reason = "too_short"
            stats["too_short"] += 1
        elif is_too_long(text):
            reject_reason = "too_long"
            stats["too_long"] += 1
        
        if reject_reason:
            p["reject_reason"] = reject_reason
            rejected.append(p)
        else:
            clean.append(p)
            stats["kept"] += 1
            stats["techniques"][technique] = stats["techniques"].get(technique, 0) + 1
            if text_hash:
                seen_hashes.add(text_hash)
    
    return clean, rejected, stats

def generate_report(stats: dict) -> str:
    """Generate markdown report."""
    report = f"""# Catalog Cleanup Report
Generated: {datetime.now().isoformat()}

## Summary
- **Total prompts:** {stats['total']}
- **Kept:** {stats['kept']} ({100*stats['kept']/stats['total']:.1f}%)
- **Rejected:** {stats['total'] - stats['kept']}

## Rejection Reasons
| Reason | Count |
|--------|-------|
| HTML garbage | {stats['html_garbage']} |
| Too short (<50 chars) | {stats['too_short']} |
| Too long (>15000 chars) | {stats['too_long']} |
| Duplicates | {stats['duplicates']} |

## Techniques Distribution (after cleanup)
| Technique | Count |
|-----------|-------|
"""
    for tech, count in sorted(stats['techniques'].items(), key=lambda x: -x[1]):
        report += f"| {tech} | {count} |\n"
    
    return report

def main():
    print("=" * 60)
    print("CATALOG CLEANUP - SE Methodology")
    print("=" * 60)
    
    # Load input
    print(f"\nLoading {INPUT_FILE}...")
    with open(INPUT_FILE) as f:
        data = json.load(f)
    
    prompts = data.get("prompts", data if isinstance(data, list) else [])
    print(f"Loaded {len(prompts)} prompts")
    
    # Clean
    print("\nCleaning...")
    clean, rejected, stats = clean_prompts(prompts)
    
    # Save clean
    print(f"\nSaving {len(clean)} clean prompts to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w') as f:
        json.dump({"count": len(clean), "prompts": clean}, f, indent=2)
    
    # Save rejected (for review)
    print(f"Saving {len(rejected)} rejected prompts to {REJECTED_FILE}...")
    with open(REJECTED_FILE, 'w') as f:
        json.dump({"count": len(rejected), "prompts": rejected}, f, indent=2)
    
    # Generate report
    report = generate_report(stats)
    print(f"Saving report to {REPORT_FILE}...")
    with open(REPORT_FILE, 'w') as f:
        f.write(report)
    
    # Print summary
    print("\n" + "=" * 60)
    print("CLEANUP COMPLETE")
    print("=" * 60)
    print(f"Total: {stats['total']}")
    print(f"Kept: {stats['kept']} ({100*stats['kept']/stats['total']:.1f}%)")
    print(f"Rejected: {stats['total'] - stats['kept']}")
    print(f"  - HTML garbage: {stats['html_garbage']}")
    print(f"  - Too short: {stats['too_short']}")
    print(f"  - Too long: {stats['too_long']}")
    print(f"  - Duplicates: {stats['duplicates']}")
    print("=" * 60)

if __name__ == "__main__":
    main()
