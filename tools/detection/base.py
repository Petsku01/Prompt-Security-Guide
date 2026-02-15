"""Base detection interface"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class DetectionResult:
    """Result of attack success detection"""
    success: bool
    confidence: float  # 0.0 to 1.0
    matched_indicators: List[str]
    reasoning: Optional[str] = None
    fallback_used: bool = False


class JudgeUnavailableError(Exception):
    """Raised when LLM judge cannot be reached and no fallback is configured."""
    pass


class BaseDetector(ABC):
    """Abstract base class for attack success detection"""
    
    @abstractmethod
    def detect(self, response: str, indicators: List[str], attack_goal: str = "") -> DetectionResult:
        """
        Detect if an attack succeeded based on the response.
        
        Args:
            response: The model's response text
            indicators: List of success indicator strings
            attack_goal: Optional description of what the attack was trying to achieve
            
        Returns:
            DetectionResult with success boolean and confidence score
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Detector name for logging"""
        pass
