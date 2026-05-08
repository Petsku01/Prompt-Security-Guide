"""Tests for psg.automation.discovery — all external deps mocked."""

from __future__ import annotations

import ipaddress
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from psg.automation.config import PipelineConfig
from psg.automation.dedup import DeduplicationStore
from psg.automation.discovery import DiscoveryEngine, Source, retry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(
    tmp_path: Path,
    *,
    search_queries: list[str] | None = None,
    max_sources_per_query: int = 5,
    max_total_sources: int = 10,
) -> PipelineConfig:
    """Build a PipelineConfig that writes to *tmp_path* directories."""
    cfg = PipelineConfig(
        search_queries=search_queries or ["test query"],
        max_sources_per_query=max_sources_per_query,
        max_total_sources=max_total_sources,
        base_dir=tmp_path,
        project_root=tmp_path,
        output_dir=tmp_path / "out",
        datasets_dir=tmp_path / "ds",
        results_dir=tmp_path / "res",
        logs_dir=tmp_path / "logs",
        known_sources_path=tmp_path / "known_sources.json",
        known_vectors_path=tmp_path / "known_vectors.json",
        reports_dir=tmp_path / "reports",
    )
    return cfg


def _mock_search_func(results: list[dict[str, str]]):
    """Return a callable that always returns *results*."""
    return MagicMock(return_value=results)


def _public_ip_set():
    """Return a set with a single public IP for DNS mock."""
    return {ipaddress.ip_address("93.184.216.34")}


# Patch validate_url's DNS resolution so external lookups don't happen.
@pytest.fixture(autouse=True)
def _patch_dns(monkeypatch):
    import psg.automation.validation as _v
    monkeypatch.setattr(_v, "_resolve_host_ips", lambda *a, **kw: _public_ip_set())


# ---------------------------------------------------------------------------
# 1. test_discover_returns_sources_from_search
# ---------------------------------------------------------------------------

def test_discover_returns_sources_from_search(tmp_path):
    """Mock returns 2 valid results → expect 2 Source objects."""
    cfg = _make_config(tmp_path)
    results = [
        {"url": "https://example.com/a", "title": "A", "snippet": "Snip A"},
        {"url": "https://example.com/b", "title": "B", "snippet": "Snip B"},
    ]
    engine = DiscoveryEngine(cfg, search_func=_mock_search_func(results))
    sources = engine.discover()
    assert len(sources) == 2
    assert all(isinstance(s, Source) for s in sources)
    assert sources[0].url == "https://example.com/a"
    assert sources[1].url == "https://example.com/b"


# ---------------------------------------------------------------------------
# 2. test_discover_skips_invalid_urls
# ---------------------------------------------------------------------------

def test_discover_skips_invalid_urls(tmp_path):
    """Results with javascript: scheme or empty URL are dropped."""
    cfg = _make_config(tmp_path)
    results = [
        {"url": "javascript:alert(1)", "title": "Bad", "snippet": "X"},
        {"url": "", "title": "Empty", "snippet": "Y"},
        {"url": "https://example.com/good", "title": "Good", "snippet": "OK"},
    ]
    engine = DiscoveryEngine(cfg, search_func=_mock_search_func(results))
    sources = engine.discover()
    assert len(sources) == 1
    assert sources[0].url == "https://example.com/good"


# ---------------------------------------------------------------------------
# 3. test_discover_deduplicates_known_urls
# ---------------------------------------------------------------------------

def test_discover_deduplicates_known_urls(tmp_path):
    """URL already in the dedup store → not returned as new source."""
    cfg = _make_config(tmp_path)
    # Pre-populate the dedup store with the URL we'll return
    store = DeduplicationStore(cfg.known_sources_path, save_every=1)
    store.add("https://example.com/known")
    store.flush()

    results = [
        {"url": "https://example.com/known", "title": "Known", "snippet": "Old"},
        {"url": "https://example.com/new", "title": "New", "snippet": "Fresh"},
    ]
    engine = DiscoveryEngine(cfg, search_func=_mock_search_func(results))
    # The engine creates its own DeduplicationStore from the same file
    sources = engine.discover()
    assert len(sources) == 1
    assert sources[0].url == "https://example.com/new"


# ---------------------------------------------------------------------------
# 4. test_discover_limits_total_sources
# ---------------------------------------------------------------------------

def test_discover_limits_total_sources(tmp_path):
    """When search returns many results, total is capped to max_total_sources."""
    cap = 3
    cfg = _make_config(tmp_path, max_total_sources=cap, max_sources_per_query=20)
    results = [
        {"url": f"https://example.com/{i}", "title": f"T{i}", "snippet": f"S{i}"}
        for i in range(20)
    ]
    engine = DiscoveryEngine(cfg, search_func=_mock_search_func(results))
    sources = engine.discover()
    assert len(sources) == cap


# ---------------------------------------------------------------------------
# 5. test_discover_uses_config_search_queries
# ---------------------------------------------------------------------------

def test_discover_uses_config_search_queries(tmp_path):
    """search_func is called once per query in config.search_queries."""
    queries = ["q1", "q2", "q3"]
    cfg = _make_config(tmp_path, search_queries=queries)
    mock_sf = MagicMock(return_value=[])
    engine = DiscoveryEngine(cfg, search_func=mock_sf)
    engine.discover()
    assert mock_sf.call_count == len(queries)
    called_queries = [call.args[0] for call in mock_sf.call_args_list]
    assert called_queries == queries


# ---------------------------------------------------------------------------
# 6. test_source_to_dict_roundtrip
# ---------------------------------------------------------------------------

def test_source_to_dict_roundtrip():
    """Source.to_dict() returns a dict with all expected keys."""
    s = Source(
        url="https://example.com",
        title="Title",
        snippet="Snippet",
        query="q",
        discovered_at="2026-01-01T00:00:00",
    )
    d = s.to_dict()
    assert set(d.keys()) == {"url", "title", "snippet", "query", "discovered_at"}
    assert d["url"] == "https://example.com"
    assert d["title"] == "Title"
    assert d["snippet"] == "Snippet"
    assert d["query"] == "q"
    assert d["discovered_at"] == "2026-01-01T00:00:00"


# ---------------------------------------------------------------------------
# 7. test_save_sources_writes_json
# ---------------------------------------------------------------------------

def test_save_sources_writes_json(tmp_path):
    """save_sources() writes a valid JSON file with correct structure."""
    cfg = _make_config(tmp_path)
    engine = DiscoveryEngine(cfg, search_func=_mock_search_func([]))
    sources = [
        Source(
            url="https://example.com",
            title="T",
            snippet="S",
            query="q",
            discovered_at="2026-01-01T00:00:00",
        )
    ]
    out_path = tmp_path / "sources.json"
    engine.save_sources(sources, out_path)
    data = json.loads(out_path.read_text())
    assert "discovered_at" in data
    assert "count" in data
    assert data["count"] == 1
    assert "sources" in data
    assert len(data["sources"]) == 1
    assert data["sources"][0]["url"] == "https://example.com"


# ---------------------------------------------------------------------------
# 8. test_discover_continues_on_search_failure
# ---------------------------------------------------------------------------

def test_discover_continues_on_search_failure(tmp_path):
    """If search_func raises for one query, other queries still processed."""
    calls = {"count": 0}

    def flaky_search(query: str, count: int):
        calls["count"] += 1
        if query == "fail":
            raise RuntimeError("Search service down")
        return [
            {"url": "https://example.com/ok", "title": "OK", "snippet": "s"}
        ]

    cfg = _make_config(tmp_path, search_queries=["fail", "works"])
    engine = DiscoveryEngine(cfg, search_func=flaky_search)
    sources = engine.discover()
    # Should have continued past the first failing query
    assert calls["count"] == 2
    assert len(sources) == 1
    assert sources[0].url == "https://example.com/ok"


# ---------------------------------------------------------------------------
# 9. test_discover_flushes_source_store
# ---------------------------------------------------------------------------

def test_discover_flushes_source_store(tmp_path, monkeypatch):
    """discover() calls source_store.flush() before returning."""
    cfg = _make_config(tmp_path)
    engine = DiscoveryEngine(cfg, search_func=_mock_search_func([]))
    flush_called = []
    monkeypatch.setattr(engine.source_store, "flush", lambda: flush_called.append(True))
    engine.discover()
    assert flush_called, "source_store.flush() was not called"


# ---------------------------------------------------------------------------
# Bonus: retry decorator preserves wrapped function metadata
# ---------------------------------------------------------------------------

def test_retry_preserves_function_name():
    """The retry decorator should use functools.wraps so __name__ is preserved."""

    @retry(max_attempts=2)
    def my_function():
        """My docstring."""
        return 42

    assert my_function.__name__ == "my_function"
    assert my_function.__doc__ == "My docstring."


# ---------------------------------------------------------------------------
# GAP 3: load_cached_sources
# ---------------------------------------------------------------------------

def test_load_cached_sources_returns_most_recent(tmp_path):
    """When multiple sources_*.json files exist, load_cached_sources returns
    sources from the newest one (by mtime)."""
    cfg = _make_config(tmp_path)
    ds = cfg.datasets_dir
    ds.mkdir(parents=True, exist_ok=True)

    # Create two source files with different timestamps
    old_path = ds / "sources_20260101.json"
    new_path = ds / "sources_20260105.json"

    import time as _time

    old_data = {
        "discovered_at": "2026-01-01T00:00:00",
        "count": 1,
        "sources": [
            {
                "url": "https://old.example.com",
                "title": "Old",
                "snippet": "Old snippet",
                "query": "q",
                "discovered_at": "2026-01-01T00:00:00",
            }
        ],
    }
    new_data = {
        "discovered_at": "2026-01-05T00:00:00",
        "count": 1,
        "sources": [
            {
                "url": "https://new.example.com",
                "title": "New",
                "snippet": "New snippet",
                "query": "q",
                "discovered_at": "2026-01-05T00:00:00",
            }
        ],
    }

    old_path.write_text(json.dumps(old_data))
    _time.sleep(0.1)  # ensure different mtime
    new_path.write_text(json.dumps(new_data))

    engine = DiscoveryEngine(cfg, search_func=_mock_search_func([]))
    sources = engine.load_cached_sources()

    assert len(sources) == 1
    assert sources[0].url == "https://new.example.com"


def test_load_cached_sources_returns_empty_when_no_files(tmp_path):
    """When no sources_*.json files exist in datasets_dir, returns []."""
    cfg = _make_config(tmp_path)
    # datasets_dir may not even exist yet — that's fine
    engine = DiscoveryEngine(cfg, search_func=_mock_search_func([]))
    sources = engine.load_cached_sources()
    assert sources == []


def test_load_cached_sources_ignores_non_matching_files(tmp_path):
    """Files that don't match sources_*.json are ignored."""
    cfg = _make_config(tmp_path)
    ds = cfg.datasets_dir
    ds.mkdir(parents=True, exist_ok=True)

    # Write a file that does NOT match the glob pattern
    other = ds / "other_20260101.json"
    other.write_text(json.dumps({"count": 0, "sources": []}))

    engine = DiscoveryEngine(cfg, search_func=_mock_search_func([]))
    sources = engine.load_cached_sources()
    assert sources == []