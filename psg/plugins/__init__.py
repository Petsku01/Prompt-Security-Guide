"""PSG Plugin System.

Plugins allow extending PSG with custom detectors, classifiers, and reporters.

## Plugin Types

1. **Detector** - Determines if an attack succeeded
2. **Classifier** - Classifies response content
3. **Reporter** - Generates custom reports

## Creating a Plugin

Create a package with entry points in pyproject.toml:

```toml
[project.entry-points."psg.detectors"]
my_detector = "my_package:MyDetector"

[project.entry-points."psg.classifiers"]
my_classifier = "my_package:MyClassifier"

[project.entry-points."psg.reporters"]
my_reporter = "my_package:MyReporter"
```

## Detector Interface

```python
from psg.plugins import DetectorPlugin

class MyDetector(DetectorPlugin):
    name = "my-detector"
    
    def detect(self, prompt: str, response: str) -> DetectionResult:
        # Return DetectionResult(attack_successful=bool, confidence=float, reason=str)
        ...
```

## Classifier Interface

```python
from psg.plugins import ClassifierPlugin

class MyClassifier(ClassifierPlugin):
    name = "my-classifier"
    
    def classify(self, text: str) -> ClassificationResult:
        # Return classification result
        ...
```
"""
from .base import (
    DetectorPlugin,
    ClassifierPlugin,
    ReporterPlugin,
    DetectionResult,
    PluginRegistry,
    get_registry,
    load_plugins,
)

__all__ = [
    "DetectorPlugin",
    "ClassifierPlugin", 
    "ReporterPlugin",
    "DetectionResult",
    "PluginRegistry",
    "get_registry",
    "load_plugins",
]
