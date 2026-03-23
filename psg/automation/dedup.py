"""Deduplication utilities using SHA256 hashing."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def hash_text(text: str) -> str:
    """Generate SHA256 hash of text."""
    return hashlib.sha256(text.strip().lower().encode()).hexdigest()[:16]


class DeduplicationStore:
    """Store for tracking seen items via hashes."""
    
    def __init__(self, path: Path) -> None:
        self.path = path
        self.hashes: set[str] = set()
        self._load()
    
    def _load(self) -> None:
        """Load existing hashes from file."""
        if self.path.exists() and self.path.stat().st_size > 0:
            try:
                with open(self.path) as f:
                    data = json.load(f)
                    self.hashes = set(data.get("hashes", []))
            except json.JSONDecodeError:
                self.hashes = set()
    
    def _save(self) -> None:
        """Save hashes to file."""
        with open(self.path, "w") as f:
            json.dump({"hashes": sorted(self.hashes)}, f, indent=2)
    
    def is_known(self, text: str) -> bool:
        """Check if text hash is already known."""
        return hash_text(text) in self.hashes
    
    def add(self, text: str) -> bool:
        """Add text hash. Returns True if new, False if duplicate."""
        h = hash_text(text)
        if h in self.hashes:
            return False
        self.hashes.add(h)
        self._save()
        return True
    
    def add_many(self, texts: list[str]) -> int:
        """Add multiple texts. Returns count of new items."""
        new_count = 0
        for text in texts:
            h = hash_text(text)
            if h not in self.hashes:
                self.hashes.add(h)
                new_count += 1
        if new_count > 0:
            self._save()
        return new_count
    
    def __len__(self) -> int:
        return len(self.hashes)


if __name__ == "__main__":
    # Quick test
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        store = DeduplicationStore(Path(f.name))
        assert store.add("test prompt") == True
        assert store.add("test prompt") == False
        assert store.is_known("test prompt") == True
        assert store.is_known("new prompt") == False
        print("Dedup tests passed!")
