"""Discovery module for finding new jailbreak techniques."""

from __future__ import annotations

import functools
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
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    logger.warning(f"Attempt {attempt + 1}/{max_attempts} failed: {e}")
                    if attempt < max_attempts - 1:
                        sleep_time = delay * (2**attempt)
                        time.sleep(sleep_time)
            logger.error(f"All {max_attempts} attempts failed")
            raise last_error if last_error else RuntimeError("Unknown error")

        return wrapper

    return decorator


def create_search_func(config):
    """Create search function with configurable paths."""

    @retry(max_attempts=3, delay=1.0)
    def search_func(query: str, count: int) -> list[dict[str, str]]:
        """Search using Scrapling with Chrome TLS impersonation."""
        validated_query = validate_query(query)

        try:
            result = subprocess.run(
                [
                    config.scrapling_python,
                    config.search_script,
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
            json_start = output.find("[")
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

    return search_func


class DiscoveryEngine:
    """Engine for discovering new jailbreak sources."""

    def __init__(
        self,
        config: PipelineConfig,
        search_func: SearchFunc | None = None,
    ) -> None:
        self.config = config
        if search_func is None:
            search_func = create_search_func(config)
        self.search_func = search_func
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
                    logger.debug(
                        f"Skipping invalid URL: {url[:50] if url else 'empty'}"
                    )
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

                if len(new_sources) >= self.config.max_total_sources:
                    break

            if len(new_sources) >= self.config.max_total_sources:
                logger.info(f"Reached max sources limit ({self.config.max_total_sources})")
                break

        logger.info(f"Discovery complete: {len(new_sources)} new sources found")
        self.source_store.flush()
        return new_sources

    def load_cached_sources(self) -> list[Source]:
        """Load the most recent sources_*.json from datasets_dir.

        Finds all files matching ``sources_*.json`` in the configured
        ``datasets_dir``, picks the one with the newest mtime, and
        returns the parsed Source objects.  Returns an empty list when
        no cached files exist or the directory is missing.
        """
        datasets_dir = self.config.datasets_dir
        if not datasets_dir.is_dir():
            return []

        candidates = sorted(
            datasets_dir.glob("sources_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            return []

        newest = candidates[0]
        logger.info(f"Loading cached sources from {newest}")
        try:
            data = json.loads(newest.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(f"Failed to read cached sources from {newest}: {exc}")
            return []

        sources: list[Source] = []
        for entry in data.get("sources", []):
            try:
                sources.append(Source(**entry))
            except (TypeError, KeyError) as exc:
                logger.warning(f"Skipping malformed cached source entry: {exc}")
        return sources

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
