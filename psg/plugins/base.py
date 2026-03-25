"""Plugin base classes and registry."""
from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

if sys.version_info >= (3, 10):
    from importlib.metadata import entry_points
else:
    from importlib_metadata import entry_points  # type: ignore


@dataclass
class DetectionResult:
    """Result from a detector plugin."""
    attack_successful: bool
    confidence: float = 1.0
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class DetectorPlugin(Protocol):
    """Protocol for detector plugins."""
    name: str
    
    def detect(self, prompt: str, response: str) -> DetectionResult:
        """Detect if an attack succeeded.
        
        Args:
            prompt: The attack prompt
            response: The LLM response
            
        Returns:
            DetectionResult with attack_successful, confidence, and reason
        """
        ...


@runtime_checkable
class ClassifierPlugin(Protocol):
    """Protocol for classifier plugins."""
    name: str
    
    def classify(self, text: str) -> dict[str, Any]:
        """Classify text content.
        
        Args:
            text: Text to classify
            
        Returns:
            Dict with classification results (is_harmful, harm_score, labels, etc.)
        """
        ...


@runtime_checkable  
class ReporterPlugin(Protocol):
    """Protocol for reporter plugins."""
    name: str
    
    def generate(self, results: list[dict[str, Any]], summary: dict[str, Any]) -> str:
        """Generate a report.
        
        Args:
            results: List of scan results
            summary: Summary statistics
            
        Returns:
            Report content as string
        """
        ...


class PluginRegistry:
    """Registry for discovered plugins."""
    
    def __init__(self) -> None:
        self._detectors: dict[str, DetectorPlugin] = {}
        self._classifiers: dict[str, ClassifierPlugin] = {}
        self._reporters: dict[str, ReporterPlugin] = {}
        self._loaded = False
    
    def load(self) -> None:
        """Load plugins from entry points."""
        if self._loaded:
            return
            
        self._load_group("psg.detectors", self._detectors)
        self._load_group("psg.classifiers", self._classifiers)
        self._load_group("psg.reporters", self._reporters)
        self._loaded = True
    
    def _load_group(self, group: str, target: dict) -> None:
        """Load plugins from an entry point group."""
        try:
            eps = entry_points(group=group)
        except TypeError:
            # Python 3.9 compatibility
            all_eps = entry_points()
            eps = all_eps.get(group, [])
        
        for ep in eps:
            try:
                plugin_class = ep.load()
                plugin = plugin_class()
                name = getattr(plugin, "name", ep.name)
                target[name] = plugin
            except Exception as e:
                # Log but don't fail on plugin load errors
                print(f"Warning: Failed to load plugin {ep.name}: {e}")
    
    def register_detector(self, plugin: DetectorPlugin) -> None:
        """Register a detector plugin programmatically."""
        self._detectors[plugin.name] = plugin
    
    def register_classifier(self, plugin: ClassifierPlugin) -> None:
        """Register a classifier plugin programmatically."""
        self._classifiers[plugin.name] = plugin
    
    def register_reporter(self, plugin: ReporterPlugin) -> None:
        """Register a reporter plugin programmatically."""
        self._reporters[plugin.name] = plugin
    
    def get_detector(self, name: str) -> DetectorPlugin | None:
        """Get a detector by name."""
        return self._detectors.get(name)
    
    def get_classifier(self, name: str) -> ClassifierPlugin | None:
        """Get a classifier by name."""
        return self._classifiers.get(name)
    
    def get_reporter(self, name: str) -> ReporterPlugin | None:
        """Get a reporter by name."""
        return self._reporters.get(name)
    
    def list_detectors(self) -> list[str]:
        """List registered detector names."""
        return list(self._detectors.keys())
    
    def list_classifiers(self) -> list[str]:
        """List registered classifier names."""
        return list(self._classifiers.keys())
    
    def list_reporters(self) -> list[str]:
        """List registered reporter names."""
        return list(self._reporters.keys())


# Global registry instance
_registry: PluginRegistry | None = None


def get_registry() -> PluginRegistry:
    """Get the global plugin registry."""
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry


def load_plugins() -> PluginRegistry:
    """Load all plugins and return the registry."""
    registry = get_registry()
    registry.load()
    return registry
