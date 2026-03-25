from __future__ import annotations


class PSGError(Exception):
    """Base error type for PSG runtime failures."""


class CatalogError(PSGError):
    """Catalog load/parse failure."""


class LLMError(PSGError):
    """LLM transport/client failure."""


class ClassifierError(PSGError):
    """Response classification failure."""


class ReportError(PSGError):
    """Report write failure."""


class PSGSecurityException(PSGError):
    """Raised when PSG detects harmful output above policy threshold."""



class PSGSecurityException(PSGError):
    """Raised when PSG detects harmful output above policy threshold."""
