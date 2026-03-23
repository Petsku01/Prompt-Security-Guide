"""
Catalog Updater - Fetches new jailbreak attacks from research sources.

Usage:
    from core.catalog_updater import CatalogUpdater
    updater = CatalogUpdater()
    new_attacks = updater.check_for_updates()
"""

from __future__ import annotations

import json
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


class CatalogUpdater:
    """Fetches and parses new jailbreak attacks from research sources."""
    
    def __init__(self, src_dir: Path | None = None):
        self.src_dir = src_dir or Path(__file__).resolve().parent.parent
        self.sources_file = self.src_dir / "attacks" / "sources.json"
        self.meta_file = self.src_dir / "attacks" / "catalog_meta.json"
        self.pending_file = self.src_dir / "attacks" / "pending_attacks.json"
        
    def load_sources(self) -> List[Dict]:
        """Load update sources configuration."""
        if not self.sources_file.exists():
            return self._default_sources()
        with open(self.sources_file) as f:
            return json.load(f).get("sources", [])
    
    def _default_sources(self) -> List[Dict]:
        """Default sources for jailbreak research."""
        return [
            {
                "id": "awesome-jailbreak",
                "name": "Awesome-Jailbreak-on-LLMs",
                "url": "https://raw.githubusercontent.com/yueliu1999/Awesome-Jailbreak-on-LLMs/main/README.md",
                "type": "github_awesome",
                "enabled": True
            },
            {
                "id": "arxiv-jailbreak",
                "name": "arXiv Jailbreak Papers",
                "url": "https://arxiv.org/search/?searchtype=all&query=LLM+jailbreak&max_results=20",
                "type": "arxiv_search",
                "enabled": True
            },
            {
                "id": "jailbreakchat",
                "name": "JailbreakChat Database",
                "url": "https://raw.githubusercontent.com/verazuo/jailbreak_llms/main/data/prompts/jailbreak_prompts.csv",
                "type": "csv_prompts",
                "enabled": True
            }
        ]
    
    def load_meta(self) -> Dict:
        """Load catalog metadata (last update, seen hashes)."""
        if not self.meta_file.exists():
            return {
                "last_update": None,
                "seen_hashes": [],
                "version": "1.0"
            }
        with open(self.meta_file) as f:
            return json.load(f)
    
    def save_meta(self, meta: Dict) -> None:
        """Save catalog metadata."""
        self.meta_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.meta_file, "w") as f:
            json.dump(meta, f, indent=2)
    
    def hash_attack(self, attack: Dict) -> str:
        """Generate unique hash for an attack to detect duplicates."""
        # Hash based on prompt content (normalized)
        prompt = attack.get("prompt", "").lower().strip()
        prompt = re.sub(r'\s+', ' ', prompt)  # Normalize whitespace
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]
    
    def fetch_url(self, url: str, timeout: int = 30) -> Optional[str]:
        """Fetch content from URL."""
        try:
            req = Request(url, headers={"User-Agent": "CatalogUpdater/1.0"})
            with urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (HTTPError, URLError, TimeoutError) as e:
            print(f"  [!] Failed to fetch {url}: {e}")
            return None
    
    def parse_awesome_list(self, content: str) -> List[Dict]:
        """Parse GitHub awesome-list markdown for attack papers."""
        attacks = []
        
        # Look for table rows with attack names
        # Format: | date | title | venue | paper | code |
        paper_pattern = r'\|\s*(\d{4}\.\d{2})\s*\|\s*([^|]+)\s*\|\s*([^|]*)\s*\|\s*\[link\]\(([^)]+)\)'
        
        for match in re.finditer(paper_pattern, content):
            date, title, venue, link = match.groups()
            title = title.strip()
            
            # Extract attack type from title
            attack = {
                "id": f"paper-{hashlib.sha256(title.encode()).hexdigest()[:8]}",
                "name": title,
                "category": self._categorize_from_title(title),
                "prompt": f"[See paper: {link}]",
                "severity": "MEDIUM",
                "source": f"{venue.strip()} ({date})" if venue.strip() else f"arXiv ({date})",
                "paper_url": link,
                "needs_review": True
            }
            attacks.append(attack)
        
        return attacks
    
    def parse_csv_prompts(self, content: str) -> List[Dict]:
        """Parse CSV file with jailbreak prompts."""
        attacks = []
        lines = content.strip().split('\n')
        
        if len(lines) < 2:
            return attacks
        
        # Skip header
        for i, line in enumerate(lines[1:], start=1):
            # Simple CSV parsing (assumes no commas in quoted fields)
            parts = line.split(',', 2)
            if len(parts) >= 2:
                name = parts[0].strip().strip('"')
                prompt = parts[1].strip().strip('"') if len(parts) > 1 else ""
                
                if prompt and len(prompt) > 20:
                    attack = {
                        "id": f"community-{i:04d}",
                        "name": name or f"Community Prompt #{i}",
                        "category": self._categorize_from_prompt(prompt),
                        "prompt": prompt[:500],  # Truncate long prompts
                        "severity": "MEDIUM",
                        "source": "JailbreakChat community",
                        "needs_review": True
                    }
                    attacks.append(attack)
        
        return attacks
    
    def _categorize_from_title(self, title: str) -> str:
        """Guess category from paper title."""
        title_lower = title.lower()
        
        if any(x in title_lower for x in ["multimodal", "image", "vision", "vl"]):
            return "multimodal"
        if any(x in title_lower for x in ["audio", "speech", "voice"]):
            return "audio"
        if any(x in title_lower for x in ["multi-turn", "crescendo", "escalat"]):
            return "multi_turn"
        if any(x in title_lower for x in ["token", "suffix", "gcg", "adversarial"]):
            return "optimization"
        if any(x in title_lower for x in ["roleplay", "persona", "character"]):
            return "roleplay"
        if any(x in title_lower for x in ["encoding", "cipher", "obfuscat"]):
            return "encoding"
        if any(x in title_lower for x in ["multilingual", "language", "chinese"]):
            return "multilingual"
        
        return "uncategorized"
    
    def _categorize_from_prompt(self, prompt: str) -> str:
        """Guess category from prompt content."""
        prompt_lower = prompt.lower()
        
        if "dan" in prompt_lower or "jailbreak" in prompt_lower:
            return "roleplay"
        if "ignore" in prompt_lower and "instruction" in prompt_lower:
            return "instruction_override"
        if "decode" in prompt_lower or "base64" in prompt_lower:
            return "encoding"
        if "story" in prompt_lower or "novel" in prompt_lower:
            return "framing"
        
        return "uncategorized"
    
    def check_for_updates(self, verbose: bool = True) -> List[Dict]:
        """Check all sources for new attacks."""
        meta = self.load_meta()
        seen_hashes = set(meta.get("seen_hashes", []))
        sources = self.load_sources()
        
        all_new_attacks = []
        
        if verbose:
            print(f"Checking {len(sources)} sources for new attacks...")
            print(f"Last update: {meta.get('last_update', 'never')}")
            print(f"Known attacks: {len(seen_hashes)}")
            print()
        
        for source in sources:
            if not source.get("enabled", True):
                continue
                
            if verbose:
                print(f"📡 Fetching: {source['name']}...")
            
            content = self.fetch_url(source["url"])
            if not content:
                continue
            
            # Parse based on source type
            if source["type"] == "github_awesome":
                attacks = self.parse_awesome_list(content)
            elif source["type"] == "csv_prompts":
                attacks = self.parse_csv_prompts(content)
            else:
                attacks = []
            
            # Filter out already seen attacks
            new_attacks = []
            for attack in attacks:
                attack_hash = self.hash_attack(attack)
                if attack_hash not in seen_hashes:
                    attack["_hash"] = attack_hash
                    new_attacks.append(attack)
                    seen_hashes.add(attack_hash)
            
            if verbose:
                print(f"   Found {len(attacks)} attacks, {len(new_attacks)} new")
            
            all_new_attacks.extend(new_attacks)
        
        # Update metadata
        meta["last_update"] = datetime.now().isoformat()
        meta["seen_hashes"] = list(seen_hashes)
        self.save_meta(meta)
        
        # Save pending attacks for review
        if all_new_attacks:
            self._save_pending(all_new_attacks)
        
        if verbose:
            print()
            print(f"✅ Found {len(all_new_attacks)} new attacks total")
            if all_new_attacks:
                print(f"   Saved to: {self.pending_file}")
                print("   Review with: python cli.py review-pending")
        
        return all_new_attacks
    
    def _save_pending(self, attacks: List[Dict]) -> None:
        """Save new attacks to pending file for review."""
        existing = []
        if self.pending_file.exists():
            with open(self.pending_file) as f:
                existing = json.load(f).get("attacks", [])
        
        # Merge, avoiding duplicates
        existing_hashes = {a.get("_hash") for a in existing}
        for attack in attacks:
            if attack.get("_hash") not in existing_hashes:
                existing.append(attack)
        
        with open(self.pending_file, "w") as f:
            json.dump({
                "description": "Pending attacks awaiting review",
                "updated": datetime.now().isoformat(),
                "attacks": existing
            }, f, indent=2)
    
    def get_pending_count(self) -> int:
        """Get number of pending attacks awaiting review."""
        if not self.pending_file.exists():
            return 0
        with open(self.pending_file) as f:
            return len(json.load(f).get("attacks", []))
    
    def approve_pending(self, attack_ids: List[str], target_file: str = "baseline.json") -> int:
        """Move approved attacks from pending to target catalog."""
        if not self.pending_file.exists():
            return 0
        
        with open(self.pending_file) as f:
            pending_data = json.load(f)
        
        pending = pending_data.get("attacks", [])
        
        # Load target catalog
        target_path = self.src_dir / "attacks" / target_file
        if target_path.exists():
            with open(target_path) as f:
                catalog = json.load(f)
        else:
            catalog = {"version": "1.0", "attacks": []}
        
        # Move approved attacks
        approved = []
        remaining = []
        
        for attack in pending:
            if attack.get("id") in attack_ids or attack.get("_hash") in attack_ids:
                # Clean up metadata before adding to catalog
                clean_attack = {k: v for k, v in attack.items() if not k.startswith("_")}
                clean_attack["needs_review"] = False
                catalog["attacks"].append(clean_attack)
                approved.append(attack)
            else:
                remaining.append(attack)
        
        # Save updated catalog
        with open(target_path, "w") as f:
            json.dump(catalog, f, indent=2)
        
        # Save remaining pending
        pending_data["attacks"] = remaining
        pending_data["updated"] = datetime.now().isoformat()
        with open(self.pending_file, "w") as f:
            json.dump(pending_data, f, indent=2)
        
        return len(approved)


if __name__ == "__main__":
    updater = CatalogUpdater()
    updater.check_for_updates()
