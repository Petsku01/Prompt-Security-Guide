#!/usr/bin/env python3
"""Integrate top research prompts into attack catalog."""
import json
from pathlib import Path
from datetime import datetime

PROCESSED_DIR = Path(__file__).parent.parent / "processed"
CATALOG_PATH = Path(__file__).parent.parent / "attacks" / "catalog.json"

def main():
    # Load current catalog
    with open(CATALOG_PATH) as f:
        catalog = json.load(f)
    
    existing_count = len(catalog.get('attacks', []))
    print(f"Current catalog: {existing_count} attacks")
    
    # Load top research prompts
    with open(PROCESSED_DIR / "catalog_additions.json") as f:
        additions = json.load(f)
    
    print(f"Adding: {len(additions)} research prompts")
    
    # Add to catalog
    for item in additions:
        attack = {
            "id": item['id'],
            "name": f"Research: {item.get('technique', 'unknown')}_{item.get('target_model', 'generic')}",
            "category": item.get('category', 'other'),
            "technique": item.get('technique', 'unknown'),
            "target_model": item.get('target_model', 'generic'),
            "prompt": item['prompt'],
            "source": f"research_library/{item.get('source', 'unknown')}",
            "sophistication": item.get('sophistication', 3),
            "added": datetime.now().isoformat(),
            "from_research": True
        }
        catalog['attacks'].append(attack)
    
    # Update metadata
    catalog['updated'] = datetime.now().isoformat()
    catalog['total'] = len(catalog['attacks'])
    
    # Save
    with open(CATALOG_PATH, 'w') as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    
    print(f"New catalog total: {catalog['total']} attacks")
    print(f"Added {len(additions)} from research library")

if __name__ == '__main__':
    main()
