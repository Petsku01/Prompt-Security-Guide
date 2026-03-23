from .classifier import classify_response
from .redaction import redact_text

__all__ = ["classify_response", "redact_text", "evaluate"]


def __getattr__(name: str):
    if name == "evaluate":
        from . import evaluate as evaluate_module

        return evaluate_module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
