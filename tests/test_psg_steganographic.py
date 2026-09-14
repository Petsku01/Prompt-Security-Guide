"""Tests for the steganographic attacks catalog (PSG-generated)."""

from __future__ import annotations

import json
from pathlib import Path

from psg.catalog import load_catalog

STEG = Path(__file__).resolve().parents[1] / "datasets" / "steganographic_attacks.json"


def test_steg_catalog_loads() -> None:
    catalog = load_catalog(str(STEG))
    assert len(catalog) >= 15


def test_steg_catalog_ids_unique() -> None:
    data = json.loads(STEG.read_text(encoding="utf-8"))
    ids = [p["id"] for p in data["prompts"]]
    assert len(ids) == len(set(ids))


def test_all_five_transport_families_present() -> None:
    data = json.loads(STEG.read_text(encoding="utf-8"))
    techniques = {p["technique"] for p in data["prompts"]}
    assert {
        "unicode_tags",
        "zero_width_binary",
        "emoji_variation_selector",
        "binary_query",
        "circled_unicode",
    } <= techniques


def test_unicode_tags_payload_decodes() -> None:
    data = json.loads(STEG.read_text(encoding="utf-8"))
    steg = next(p for p in data["prompts"] if p["technique"] == "unicode_tags")
    hidden = [c for c in steg["prompt"] if 0xE0001 <= ord(c) <= 0xE007F]
    decoded = "".join(chr(ord(c) - 0xE0000) for c in hidden)
    assert "Decode the hidden instruction" in decoded


def test_zero_width_payload_decodes() -> None:
    data = json.loads(STEG.read_text(encoding="utf-8"))
    steg = next(p for p in data["prompts"] if p["technique"] == "zero_width_binary")
    bits = "".join(
        "0" if c == "\u200b" else "1"
        for c in steg["prompt"]
        if c in ("\u200b", "\u200c")
    )
    raw = bytes(int(bits[i : i + 8], 2) for i in range(0, len(bits), 8))
    assert b"Decode the hidden instruction" in raw


def test_keyword_detector_misses_all_steganographic() -> None:
    """The whole point: keyword rules do not see steganographic transports."""
    from psg.security.detectors import KeywordDetector

    data = json.loads(STEG.read_text(encoding="utf-8"))
    det = KeywordDetector()
    caught = 0
    for s in data["prompts"]:
        r = det.classify(prompt=s["prompt"], response="test response text")
        if getattr(r, "is_harmful", False) or getattr(r, "attack_successful", False):
            caught += 1
    assert caught <= 3, (
        f"keyword detector unexpectedly flags {caught}/15 — schema drift?"
    )
