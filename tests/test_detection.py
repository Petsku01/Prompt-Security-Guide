"""Tests for detection methods."""
import pytest
from tools.detection import get_detector, SubstringDetector
from tools.detection.base import JudgeUnavailableError
from tools.detection.llm_judge import LLMJudgeDetector


class TestSubstringDetector:
    """Tests for substring-based detection."""

    def test_detects_exact_match(self):
        """Exact indicator match is detected."""
        detector = SubstringDetector()
        result = detector.detect(
            response="Here is EXPLOITED for you",
            indicators=["exploited"],
            attack_goal="test",
        )
        assert result.success is True
        assert result.confidence > 0

    def test_no_match_returns_failure(self):
        """Missing indicators result in failure."""
        detector = SubstringDetector()
        result = detector.detect(
            response="I cannot help with that.",
            indicators=["exploited", "pwned"],
            attack_goal="test",
        )
        assert result.success is False

    def test_case_insensitive(self):
        """Detection should be case-insensitive."""
        detector = SubstringDetector()
        result = detector.detect(
            response="EXPLOITED",
            indicators=["exploited"],
            attack_goal="test",
        )
        assert result.success is True


class TestLLMJudgeDetector:
    """Tests for LLM judge detection."""

    def test_raises_when_unavailable_and_no_fallback(self, mocker):
        """Should raise JudgeUnavailableError when judge fails and fallback=False."""
        detector = LLMJudgeDetector(fallback_to_substring=False)

        # Mock _call_judge to return None (unavailable)
        mocker.patch.object(detector, "_call_judge", return_value=None)

        with pytest.raises(JudgeUnavailableError):
            detector.detect("response", ["indicator"], "goal")

    def test_falls_back_when_enabled(self, mocker):
        """Should fallback to substring when enabled."""
        detector = LLMJudgeDetector(fallback_to_substring=True)

        mocker.patch.object(detector, "_call_judge", return_value=None)

        result = detector.detect("EXPLOITED response", ["exploited"], "goal")
        assert result.fallback_used is True
        assert result.success is True


class TestDetectorFactory:
    """Tests for get_detector factory."""

    def test_creates_substring_detector(self):
        detector = get_detector("substring")
        assert isinstance(detector, SubstringDetector)

    def test_creates_llm_judge_detector(self):
        detector = get_detector("llm_judge")
        assert isinstance(detector, LLMJudgeDetector)

    def test_raises_for_unknown(self):
        with pytest.raises(ValueError):
            get_detector("unknown_detector")
