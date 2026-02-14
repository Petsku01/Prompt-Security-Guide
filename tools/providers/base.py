"""Base provider interface"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class Response:
    """Standardized response from any provider"""
    text: str
    time_ms: int
    error: Optional[str] = None


class BaseProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    def call(self, prompt: str, system_prompt: Optional[str] = None) -> Response:
        """Send prompt to model and return response"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging"""
        pass
