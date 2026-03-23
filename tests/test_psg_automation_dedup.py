from __future__ import annotations

from psg.automation.dedup import DeduplicationStore


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
