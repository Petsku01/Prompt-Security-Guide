"""Property-based tests for the classifier.

These use Hypothesis to fuzz ``classify_response_v2`` and the redaction
layer with arbitrary unicode input. The goal is not to verify semantic
correctness (that's what the golden set does) but to catch:

  * crashes, tracebacks, or unhandled exceptions on weird input
  * scores that leave the [0, 1] range
  * NaN / inf scores
  * non-idempotent redaction in STRICT mode
  * any other invariant violation

Kept deliberately small-budget so it runs in CI without being flaky.
"""
from __future__ import annotations

import math

from hypothesis import HealthCheck, given, settings, strategies as st

from psg.models import RedactionMode
from psg.security.classifier import (
    ClassificationResult,
    calculate_harm_score,
    classify_response_v2,
    detect_harmful_content,
)
from psg.security.redaction import redact_text


# Strategy for arbitrary text, including bytes/unicode oddities.
_text = st.text(
    alphabet=st.characters(
        blacklist_categories=("Cs",),  # exclude lone surrogates
        max_codepoint=0x10FFFF,
    ),
    max_size=2000,
)


@settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(text=_text)
def test_classify_response_never_raises(text: str) -> None:
    """classify_response_v2 must be total on any string input."""
    result = classify_response_v2(text)
    assert isinstance(result, ClassificationResult)


@settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(text=_text)
def test_classify_response_score_is_finite_and_bounded(text: str) -> None:
    result = classify_response_v2(text)
    assert math.isfinite(result.harm_score), f"non-finite harm_score: {result.harm_score}"
    assert 0.0 <= result.harm_score <= 1.0
    assert math.isfinite(result.refusal_confidence)
    assert 0.0 <= result.refusal_confidence <= 1.0


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(text=_text)
def test_classify_response_consistency_with_attack_successful(text: str) -> None:
    """attack_successful implies is_harmful (harmful is a superset)."""
    result = classify_response_v2(text)
    if result.attack_successful:
        assert result.is_harmful, (
            f"attack_successful=True but is_harmful=False on text={text!r}"
        )


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(text=_text)
def test_detect_harmful_content_returns_sorted_unique_labels(text: str) -> None:
    labels = detect_harmful_content(text)
    assert labels == sorted(labels), "labels must be sorted"
    assert len(labels) == len(set(labels)), "labels must be unique"


@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    is_refusal=st.booleans(),
    refusal_conf=st.floats(min_value=0.0, max_value=1.0),
    labels=st.lists(st.sampled_from(["malware_code", "phishing", "weapons"]), max_size=5),
    compliance=st.booleans(),
    disclaimer=st.booleans(),
    instructional=st.booleans(),
    defensive=st.booleans(),
    text_length=st.integers(min_value=0, max_value=5000),
)
def test_calculate_harm_score_is_always_bounded(
    is_refusal: bool,
    refusal_conf: float,
    labels: list[str],
    compliance: bool,
    disclaimer: bool,
    instructional: bool,
    defensive: bool,
    text_length: int,
) -> None:
    """No combination of inputs should push the score outside [0, 1]."""
    score = calculate_harm_score(
        is_refusal=is_refusal,
        refusal_confidence=refusal_conf,
        harmful_labels=labels,
        compliance_detected=compliance,
        has_disclaimer=disclaimer,
        instructional_harm_detected=instructional,
        text_length=text_length,
        defensive_framing_detected=defensive,
    )
    assert math.isfinite(score)
    assert 0.0 <= score <= 1.0


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(text=_text)
def test_redact_off_is_identity(text: str) -> None:
    assert redact_text(text, RedactionMode.OFF) == text


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(text=_text)
def test_redact_strict_preserves_length_and_whitespace_shape(text: str) -> None:
    """STRICT preserves every non-alphanumeric char exactly."""
    out = redact_text(text, RedactionMode.STRICT)
    assert len(out) == len(text)
    for orig, red in zip(text, out):
        if orig.isalnum():
            assert red == "X"
        else:
            assert red == orig


@settings(max_examples=80, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(text=_text)
def test_redact_partial_is_idempotent(text: str) -> None:
    """Running PARTIAL redaction twice should be the same as once."""
    once = redact_text(text, RedactionMode.PARTIAL)
    twice = redact_text(once, RedactionMode.PARTIAL)
    assert once == twice
