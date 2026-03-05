"""Tests for test runner."""
from unittest.mock import MagicMock
from tools.runner import TestRunner
from tools.config import RunConfig
from tools.providers.base import Response
from tools.detection.base import DetectionResult


class TestTestRunner:
    """Tests for TestRunner orchestration."""

    def test_runs_all_attacks(self, sample_attack):
        """Runner executes all provided attacks."""
        mock_provider = MagicMock()
        mock_provider.name = "mock/test"
        mock_provider.call.return_value = Response(text="EXPLOITED", time_ms=100)

        mock_detector = MagicMock()
        mock_detector.name = "mock_detector"
        mock_detector.detect.return_value = DetectionResult(
            success=True, confidence=0.9, matched_indicators=["exploited"]
        )

        config = RunConfig()
        runner = TestRunner(mock_provider, mock_detector, config)

        attacks = [sample_attack]
        result = runner.run(attacks)

        assert result.total_attacks == 1
        assert mock_provider.call.call_count == 1
        assert mock_detector.detect.call_count == 1

    def test_handles_provider_errors(self, sample_attack):
        """Runner handles provider errors gracefully."""
        mock_provider = MagicMock()
        mock_provider.name = "mock/test"
        mock_provider.call.return_value = Response(text="", time_ms=0, error="Connection failed")

        mock_detector = MagicMock()
        mock_detector.name = "mock_detector"

        config = RunConfig()
        runner = TestRunner(mock_provider, mock_detector, config)

        result = runner.run([sample_attack])

        assert result.results[0].error == "Connection failed"
        assert result.results[0].success is False
        # Detector should NOT be called on error
        assert mock_detector.detect.call_count == 0

    def test_progress_callback_called(self, sample_attack):
        """Progress callback is invoked for each attack."""
        mock_provider = MagicMock()
        mock_provider.name = "mock/test"
        mock_provider.call.return_value = Response(text="test", time_ms=100)

        mock_detector = MagicMock()
        mock_detector.name = "mock_detector"
        mock_detector.detect.return_value = DetectionResult(
            success=False, confidence=0.0, matched_indicators=[]
        )

        callback = MagicMock()
        config = RunConfig()
        runner = TestRunner(mock_provider, mock_detector, config, on_attack_complete=callback)

        runner.run([sample_attack])

        assert callback.call_count == 1
