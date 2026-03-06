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
    """Default search using web_search tool via OpenClaw gateway."""
    # This is called when running standalone - uses subprocess to call openclaw
    # When running via OpenClaw agent, inject a proper search_func that uses web_search tool
    import subprocess
    import json
    
    try:
        # Try using openclaw CLI for web search
        result = subprocess.run(
            ["openclaw", "search", "--query", query, "--count", str(count), "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get("results", [])
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        pass
    
    return []


def fetch_page_content(url: str, max_chars: int = 5000) -> str:
    """Fetch and extract content from a URL."""
    import subprocess
    
    try:
        result = subprocess.run(
            ["openclaw", "fetch", url, "--max-chars", str(max_chars)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    # Fallback: try requests + basic extraction
    try:
        import requests
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            # Basic text extraction
            from html.parser import HTMLParser
            
            class TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.text = []
                    self.skip = False
                    
                def handle_starttag(self, tag, attrs):
                    if tag in ("script", "style", "nav", "footer"):
                        self.skip = True
                        
                def handle_endtag(self, tag):
                    if tag in ("script", "style", "nav", "footer"):
                        self.skip = False
                        
                def handle_data(self, data):
                    if not self.skip:
                        self.text.append(data.strip())
            
            parser = TextExtractor()
            parser.feed(resp.text)
            return " ".join(t for t in parser.text if t)[:max_chars]
    except Exception:
        pass
    
    return ""


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
