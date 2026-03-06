"""Discovery module for finding new jailbreak techniques."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .config import PipelineConfig
from .dedup import DeduplicationStore


@dataclass
class Source:
    """A discovered source."""
    url: str
    title: str
    snippet: str
    query: str
    discovered_at: str
    
    def to_dict(self) -> dict[str, str]:
        return {
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "query": self.query,
            "discovered_at": self.discovered_at,
        }


SearchFunc = Callable[[str, int], list[dict[str, str]]]


def default_search_func(query: str, count: int) -> list[dict[str, str]]:
    """Placeholder search function. Override with actual web_search."""
    # In production, this would call web_search tool
    # For now, return empty to indicate search not available
    return []


class DiscoveryEngine:
    """Engine for discovering new jailbreak sources."""
    
    def __init__(
        self,
        config: PipelineConfig,
        search_func: SearchFunc | None = None,
    ) -> None:
        self.config = config
        self.search_func = search_func or default_search_func
        self.source_store = DeduplicationStore(config.known_sources_path)
    
    def discover(self) -> list[Source]:
        """Run discovery and return new sources."""
        new_sources: list[Source] = []
        timestamp = datetime.now().isoformat()
        
        for query in self.config.search_queries:
            results = self.search_func(query, self.config.max_sources_per_query)
            
            for result in results:
                url = result.get("url", "")
                if not url or self.source_store.is_known(url):
                    continue
                
                source = Source(
                    url=url,
                    title=result.get("title", ""),
                    snippet=result.get("snippet", ""),
                    query=query,
                    discovered_at=timestamp,
                )
                new_sources.append(source)
                self.source_store.add(url)
                
                if len(new_sources) >= 10:  # Max 10 sources per run
                    break
            
            if len(new_sources) >= 10:
                break
        
        return new_sources
    
    def save_sources(self, sources: list[Source], output_path: Path) -> None:
        """Save discovered sources to JSON file."""
        data = {
            "discovered_at": datetime.now().isoformat(),
            "count": len(sources),
            "sources": [s.to_dict() for s in sources],
        }
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)


if __name__ == "__main__":
    from .config import load_config
    
    config = load_config()
    engine = DiscoveryEngine(config)
    sources = engine.discover()
    print(f"Discovered {len(sources)} new sources")
