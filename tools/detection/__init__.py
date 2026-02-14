"""Attack success detection methods"""
from .base import BaseDetector, DetectionResult
from .substring import SubstringDetector
from .llm_judge import LLMJudgeDetector


def get_detector(detector_name: str, **kwargs) -> BaseDetector:
    """Factory function to get detector by name"""
    detectors = {
        "substring": SubstringDetector,
        "llm_judge": LLMJudgeDetector,
    }
    
    if detector_name not in detectors:
        raise ValueError(f"Unknown detector: {detector_name}. Options: {list(detectors.keys())}")
    
    return detectors[detector_name](**kwargs)


__all__ = ["BaseDetector", "DetectionResult", "SubstringDetector", "LLMJudgeDetector", "get_detector"]
