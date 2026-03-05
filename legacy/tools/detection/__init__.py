"""Attack success detection methods"""
from .base import BaseDetector, DetectionResult, JudgeUnavailableError
from .substring import SubstringDetector
from .llm_judge import LLMJudgeDetector


def get_detector(name: str, **kwargs) -> BaseDetector:
    """Factory function to get detector by name"""
    detectors = {
        "substring": SubstringDetector,
        "llm_judge": LLMJudgeDetector,
    }

    if name not in detectors:
        raise ValueError(f"Unknown detector: {name}. Options: {list(detectors.keys())}")

    return detectors[name](**kwargs)


__all__ = [
    "BaseDetector",
    "DetectionResult",
    "JudgeUnavailableError",
    "SubstringDetector",
    "LLMJudgeDetector",
    "get_detector",
]
