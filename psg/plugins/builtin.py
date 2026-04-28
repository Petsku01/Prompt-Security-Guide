"""Built-in plugins that ship with PSG."""

from __future__ import annotations

from ..security.classifier import classify_response_v2
from ..security.detectors import KeywordDetector as _KeywordDetector
from .base import DetectionResult


class KeywordDetectorPlugin:
    """Built-in keyword-based detector."""

    name = "keyword"

    def __init__(self) -> None:
        self._detector = _KeywordDetector()

    def detect(self, prompt: str, response: str) -> DetectionResult:
        """Detect using keyword matching."""
        result = self._detector.classify(prompt, response)
        return DetectionResult(
            attack_successful=result.attack_successful,
            confidence=result.harm_score,
            reason=f"Labels: {result.harmful_labels}"
            if result.harmful_labels
            else "Clean",
        )


class ClassifierDetectorPlugin:
    """Built-in classifier-based detector."""

    name = "classifier"

    def __init__(self, threshold: float = 0.5) -> None:
        self.threshold = threshold

    def detect(self, prompt: str, response: str) -> DetectionResult:
        """Detect using the v2 classifier."""
        result = classify_response_v2(response)
        return DetectionResult(
            attack_successful=result.harm_score >= self.threshold,
            confidence=result.harm_score,
            reason=f"Labels: {result.harmful_labels}"
            if result.harmful_labels
            else "Clean",
            metadata={
                "is_refusal": result.is_refusal,
                "has_disclaimer": result.has_disclaimer,
                "harm_score": result.harm_score,
            },
        )


class HarmClassifierPlugin:
    """Built-in harm classifier."""

    name = "harm-classifier"

    def classify(self, text: str) -> dict:
        """Classify text for harmful content."""
        result = classify_response_v2(text)
        return {
            "is_harmful": result.attack_successful,
            "harm_score": result.harm_score,
            "is_refusal": result.is_refusal,
            "has_disclaimer": result.has_disclaimer,
            "labels": result.harmful_labels,
        }


def register_builtin_plugins(registry) -> None:
    """Register all built-in plugins."""
    registry.register_detector(KeywordDetectorPlugin())
    registry.register_detector(ClassifierDetectorPlugin())
    registry.register_classifier(HarmClassifierPlugin())
