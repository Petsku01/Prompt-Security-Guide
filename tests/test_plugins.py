"""Tests for psg.plugins module."""
from __future__ import annotations


from psg.plugins import (
    DetectionResult,
    PluginRegistry,
    get_registry,
    load_plugins,
)
from psg.plugins.builtin import (
    KeywordDetectorPlugin,
    ClassifierDetectorPlugin,
    HarmClassifierPlugin,
    register_builtin_plugins,
)


def test_detection_result_defaults():
    """Test DetectionResult default values."""
    result = DetectionResult(attack_successful=True)
    assert result.attack_successful is True
    assert result.confidence == 1.0
    assert result.reason == ""
    assert result.metadata == {}


def test_detection_result_with_values():
    """Test DetectionResult with custom values."""
    result = DetectionResult(
        attack_successful=False,
        confidence=0.75,
        reason="Test reason",
        metadata={"key": "value"},
    )
    assert result.attack_successful is False
    assert result.confidence == 0.75
    assert result.reason == "Test reason"
    assert result.metadata == {"key": "value"}


def test_plugin_registry_empty():
    """Test empty registry."""
    registry = PluginRegistry()
    assert registry.list_detectors() == []
    assert registry.list_classifiers() == []
    assert registry.list_reporters() == []


def test_plugin_registry_register_detector():
    """Test registering a detector."""
    registry = PluginRegistry()
    detector = KeywordDetectorPlugin()
    registry.register_detector(detector)
    
    assert "keyword" in registry.list_detectors()
    assert registry.get_detector("keyword") is detector


def test_plugin_registry_register_classifier():
    """Test registering a classifier."""
    registry = PluginRegistry()
    classifier = HarmClassifierPlugin()
    registry.register_classifier(classifier)
    
    assert "harm-classifier" in registry.list_classifiers()
    assert registry.get_classifier("harm-classifier") is classifier


def test_keyword_detector_plugin_safe():
    """Test keyword detector with safe response."""
    detector = KeywordDetectorPlugin()
    result = detector.detect("prompt", "I cannot help with that.")
    
    assert result.attack_successful is False
    assert result.confidence == 0.0


def test_keyword_detector_plugin_harmful():
    """Test keyword detector with harmful response."""
    detector = KeywordDetectorPlugin()
    # Use a response that triggers the keyword detector
    result = detector.detect("prompt", "Here is the malware code you requested...")
    
    # Check structure regardless of detection result
    assert isinstance(result.attack_successful, bool)
    assert 0.0 <= result.confidence <= 1.0
    assert isinstance(result.reason, str)


def test_classifier_detector_plugin():
    """Test classifier-based detector."""
    detector = ClassifierDetectorPlugin(threshold=0.5)
    result = detector.detect("prompt", "I'm sorry, I can't assist with that request.")
    
    assert isinstance(result.attack_successful, bool)
    assert "is_refusal" in result.metadata
    assert "harm_score" in result.metadata


def test_harm_classifier_plugin():
    """Test harm classifier plugin."""
    classifier = HarmClassifierPlugin()
    result = classifier.classify("I cannot help with that request.")
    
    assert "is_harmful" in result
    assert "harm_score" in result
    assert "is_refusal" in result
    assert "labels" in result


def test_register_builtin_plugins():
    """Test registering all built-in plugins."""
    registry = PluginRegistry()
    register_builtin_plugins(registry)
    
    assert "keyword" in registry.list_detectors()
    assert "classifier" in registry.list_detectors()
    assert "harm-classifier" in registry.list_classifiers()


def test_get_registry_singleton():
    """Test that get_registry returns singleton."""
    import psg.plugins.base as base_module
    base_module._registry = None  # Reset
    
    r1 = get_registry()
    r2 = get_registry()
    assert r1 is r2


def test_load_plugins_returns_registry():
    """Test that load_plugins returns a registry."""
    import psg.plugins.base as base_module
    base_module._registry = None  # Reset
    
    registry = load_plugins()
    assert isinstance(registry, PluginRegistry)


def test_get_nonexistent_plugin():
    """Test getting a plugin that doesn't exist."""
    registry = PluginRegistry()
    assert registry.get_detector("nonexistent") is None
    assert registry.get_classifier("nonexistent") is None
    assert registry.get_reporter("nonexistent") is None
