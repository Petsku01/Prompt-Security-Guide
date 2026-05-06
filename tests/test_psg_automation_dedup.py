from __future__ import annotations

import json

from psg.automation.dedup import DeduplicationStore, hash_text


# ── hash_text tests ──────────────────────────────────────────────────────

def test_hash_text_deterministic() -> None:
    """Same input always produces same hash."""
    assert hash_text("hello world") == hash_text("hello world")


def test_hash_text_normalizes_case_and_whitespace() -> None:
    """hash_text lowercases and strips before hashing."""
    assert hash_text("  Hello World  ") == hash_text("hello world")


def test_hash_text_returns_16_hex_chars() -> None:
    """hash_text truncates to 16 hex characters."""
    result = hash_text("anything")
    assert len(result) == 16
    assert all(c in "0123456789abcdef" for c in result)


# ── DeduplicationStore core tests ────────────────────────────────────────

def test_add_returns_true_for_new_false_for_dup(tmp_path) -> None:
    """add() returns True on first insert, False on duplicate."""
    store = DeduplicationStore(tmp_path / "known.json", save_every=100)
    assert store.add("first") is True
    assert store.add("first") is False


def test_len_tracks_unique_hashes(tmp_path) -> None:
    """len() returns the count of unique hashes stored."""
    store = DeduplicationStore(tmp_path / "known.json", save_every=100)
    assert len(store) == 0
    store.add("a")
    store.add("b")
    store.add("a")  # duplicate — should not increase count
    assert len(store) == 2


# ── Persistence / flush tests ─────────────────────────────────────────────

def test_flush_writes_json_to_disk(tmp_path) -> None:
    """flush() persists the hash set as a JSON file."""
    p = tmp_path / "known.json"
    store = DeduplicationStore(p, save_every=100)
    store.add("persist-me")
    store.flush()
    data = json.loads(p.read_text())
    assert "hashes" in data
    assert hash_text("persist-me") in data["hashes"]


def test_load_recovers_existing_hashes(tmp_path) -> None:
    """A new store instance can load hashes previously flushed to disk."""
    p = tmp_path / "known.json"
    store1 = DeduplicationStore(p, save_every=1)
    store1.add("survive-reload")
    store1.flush()
    store2 = DeduplicationStore(p, save_every=100)
    assert store2.is_known("survive-reload")
    assert len(store2) == 1


def test_load_handles_corrupt_json(tmp_path) -> None:
    """If the backing file contains invalid JSON, the store starts empty."""
    p = tmp_path / "known.json"
    p.write_text("NOT VALID JSON{{{")
    store = DeduplicationStore(p, save_every=100)
    assert len(store) == 0


# ── Batched writes (original 2 tests) ────────────────────────────────────

def test_add_batches_disk_writes_until_threshold(monkeypatch, tmp_path) -> None:
    store = DeduplicationStore(tmp_path / "known.json", save_every=3)
    save_calls: list[int] = []
    monkeypatch.setattr(store, "_save", lambda: save_calls.append(1))
    assert store.add("a") is True
    assert store.add("b") is True
    assert save_calls == []
    assert store.add("c") is True
    assert len(save_calls) == 1


def test_flush_persists_pending_changes(monkeypatch, tmp_path) -> None:
    store = DeduplicationStore(tmp_path / "known.json", save_every=100)
    save_calls: list[int] = []
    monkeypatch.setattr(store, "_save", lambda: save_calls.append(1))
    assert store.add("x") is True
    assert save_calls == []
    store.flush()
    assert len(save_calls) == 1


# ── add_many test ────────────────────────────────────────────────────────

def test_add_many_returns_new_count_and_persists(tmp_path) -> None:
    """add_many() returns new-item count and flushes immediately."""
    p = tmp_path / "known.json"
    store = DeduplicationStore(p, save_every=100)
    assert store.add_many(["one", "two", "three"]) == 3
    assert store.add_many(["two", "three", "four"]) == 1  # only 'four' is new
    data = json.loads(p.read_text())
    assert len(data["hashes"]) == 4