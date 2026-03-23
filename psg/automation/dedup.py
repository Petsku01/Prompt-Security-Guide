"""Deduplication utilities using SHA256 hashing."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def hash_text(text: str) -> str:
    """Generate SHA256 hash of text."""
    return hashlib.sha256(text.strip().lower().encode()).hexdigest()[:16]


class DeduplicationStore:
    """Store for tracking seen items via hashes."""
    
    def __init__(self, path: Path, save_every: int = 100) -> None:
        self.path = path
        self.save_every = max(1, int(save_every))
        self.hashes: set[str] = set()
        self._pending_writes = 0
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
        self._pending_writes += 1
        if self._pending_writes >= self.save_every:
            self.flush()
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
            self._pending_writes += new_count
            self.flush()
        return new_count

    def flush(self) -> None:
        """Persist pending updates to disk."""
        if self._pending_writes == 0:
            return
        self._save()
        self._pending_writes = 0
    
    def __len__(self) -> int:
        return len(self.hashes)


if __name__ == "__main__":
    # Quick test
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        store = DeduplicationStore(Path(f.name), save_every=1)
        assert store.add("test prompt")
        assert not store.add("test prompt")
        assert store.is_known("test prompt")
        assert not store.is_known("new prompt")
        store.flush()
        print("Dedup tests passed!")
