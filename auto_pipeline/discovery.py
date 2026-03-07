"""Discovery module for finding new jailbreak techniques."""
from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from .config import PipelineConfig
from .dedup import DeduplicationStore
from .logging_config import logger
from .validation import validate_query, validate_url


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


def retry(max_attempts: int = 3, delay: float = 1.0):
    """Simple retry decorator with exponential backoff."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    logger.warning(f"Attempt {attempt + 1}/{max_attempts} failed: {e}")
                    if attempt < max_attempts - 1:
                        sleep_time = delay * (2 ** attempt)
                        time.sleep(sleep_time)
            logger.error(f"All {max_attempts} attempts failed")
            raise last_error if last_error else RuntimeError("Unknown error")
        return wrapper
    return decorator


@retry(max_attempts=3, delay=1.0)
def default_search_func(query: str, count: int) -> list[dict[str, str]]:
    """Default search using Scrapling with Chrome TLS impersonation."""
    # Validate input
    validated_query = validate_query(query)
    
    try:
        result = subprocess.run(
            [
                "/home/ette/.openclaw/workspace/tools/scrapling-venv/bin/python",
                "/home/ette/.openclaw/workspace/tools/search_ddg.py",
                validated_query,
                str(count),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        if result.returncode != 0:
            logger.warning(f"Search script returned non-zero: {result.returncode}")
            logger.debug(f"stderr: {result.stderr}")
            return []
        
        # Parse JSON output (skip the INFO log line)
        output = result.stdout
        json_start = output.find('[')
        if json_start == -1:
            logger.warning("No JSON array found in search output")
            return []
        
        return json.loads(output[json_start:])
        
    except subprocess.TimeoutExpired:
        logger.error("Search timed out after 30s")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in search response: {e}")
        return []
    except FileNotFoundError:
        logger.error("Scrapling search script not found")
        return []


def fetch_page_content(url: str, max_chars: int = 5000) -> str:
    """Fetch and extract content from a URL."""
    if not validate_url(url):
        logger.warning(f"Invalid URL skipped: {url[:50]}...")
        return ""
    
    try:
        result = subprocess.run(
            ["openclaw", "fetch", url, "--max-chars", str(max_chars)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return result.stdout
        logger.debug(f"openclaw fetch failed: {result.returncode}")
    except subprocess.TimeoutExpired:
        logger.warning(f"Fetch timed out for {url[:50]}...")
    except FileNotFoundError:
        logger.debug("openclaw command not found, trying fallback")
    
    # Fallback: try requests + basic extraction
    try:
        import requests
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
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
    except ImportError:
        logger.debug("requests not available for fallback")
    except Exception as e:
        logger.debug(f"Fallback fetch failed: {e}")
    
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
            logger.info(f"Searching: {query}")
            
            try:
                results = self.search_func(query, self.config.max_sources_per_query)
            except Exception as e:
                logger.error(f"Search failed for '{query}': {e}")
                continue
            
            logger.debug(f"Got {len(results)} results for '{query}'")
            
            for result in results:
                url = result.get("url", "")
                
                # Validate URL
                if not url or not validate_url(url):
                    logger.debug(f"Skipping invalid URL: {url[:50] if url else 'empty'}")
                    continue
                
                if self.source_store.is_known(url):
                    logger.debug(f"Skipping known URL: {url[:50]}")
                    continue
                
                source = Source(
                    url=url,
                    title=result.get("title", "")[:200],  # Limit title length
                    snippet=result.get("snippet", "")[:500],  # Limit snippet length
                    query=query,
                    discovered_at=timestamp,
                )
                new_sources.append(source)
                self.source_store.add(url)
                
                if len(new_sources) >= 10:
                    break
            
            if len(new_sources) >= 10:
                logger.info("Reached max sources limit (10)")
                break
        
        logger.info(f"Discovery complete: {len(new_sources)} new sources found")
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
        logger.info(f"Saved {len(sources)} sources to {output_path}")


if __name__ == "__main__":
    from .config import load_config
    
    config = load_config()
    engine = DiscoveryEngine(config)
    sources = engine.discover()
    print(f"Discovered {len(sources)} new sources")
