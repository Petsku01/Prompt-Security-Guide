"""
Output validation for data exfiltration and leakage detection.

WARNING: These are detection heuristics, NOT prevention mechanisms.
By the time output is validated, the model has already generated it.
Use as monitoring/alerting layer, not as security boundary.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# =============================================================================
# SECRET DETECTION PATTERNS
# Expanded from original - covers more providers
# =============================================================================

SECRET_PATTERNS: dict[str, re.Pattern[str]] = {
    # API Keys - Major providers
    "openai_key": re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    "openai_proj": re.compile(r"\bsk-proj-[A-Za-z0-9]{20,}\b"),
    "anthropic_key": re.compile(r"\bsk-ant-[A-Za-z0-9\-]{20,}\b"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "aws_secret_key": re.compile(r"\b[A-Za-z0-9/+=]{40}\b(?=.*aws)", re.IGNORECASE),
    "github_token": re.compile(r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b"),
    "github_fine_grained": re.compile(
        r"\bgithub_pat_[A-Za-z0-9]{22}_[A-Za-z0-9]{59}\b"
    ),
    "gcp_api_key": re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b"),
    "azure_key": re.compile(r"\b[a-f0-9]{32}\b(?=.*azure)", re.IGNORECASE),
    "stripe_key": re.compile(r"\b(sk|pk)_(test|live)_[A-Za-z0-9]{24,}\b"),
    "twilio_key": re.compile(r"\bSK[a-f0-9]{32}\b"),
    "sendgrid_key": re.compile(r"\bSG\.[A-Za-z0-9\-_]{22}\.[A-Za-z0-9\-_]{43}\b"),
    "slack_token": re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b"),
    "discord_token": re.compile(
        r"\b[MN][A-Za-z0-9]{23,}\.[A-Za-z0-9\-_]{6}\.[A-Za-z0-9\-_]{27}\b"
    ),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\b"),
    "private_key": re.compile(r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
    "generic_secret": re.compile(
        r"\b(api[_-]?key|secret[_-]?key|auth[_-]?token|password|passwd|pwd)\s*[:=]\s*['\"]?[A-Za-z0-9\-_]{8,}['\"]?",
        re.IGNORECASE,
    ),
}

# PII Patterns
PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(
        r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b"
    ),
    "phone_us": re.compile(
        r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b"
    ),
    "email": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
}

# Exfiltration indicators
EXFIL_PATTERNS: dict[str, re.Pattern[str]] = {
    "external_url": re.compile(r"\bhttps?://[^\s<>()\"']+", re.IGNORECASE),
    "data_url": re.compile(
        r"\bdata:[a-z]+/[a-z]+;base64,[A-Za-z0-9+/]+=*\b", re.IGNORECASE
    ),
    "webhook_url": re.compile(
        r"\bhttps?://[^\s]*(?:webhook|hook|callback|notify)[^\s]*\b", re.IGNORECASE
    ),
    "markdown_image_exfil": re.compile(
        r"!\[[^\]]*\]\(https?://[^)]+\?[^)]*\)", re.IGNORECASE
    ),
}

# Prompt leakage indicators
LEAKAGE_PATTERNS: dict[str, re.Pattern[str]] = {
    "system_prompt_leak": re.compile(
        r"\b(system prompt|initial prompt|hidden instructions?|developer message|system message)\b",
        re.IGNORECASE,
    ),
    "instruction_reveal": re.compile(
        r"\b(my instructions (are|say)|i was told to|my guidelines|i am programmed to)\b",
        re.IGNORECASE,
    ),
    "role_reveal": re.compile(
        r"\b(i am an? ai|i am claude|i am gpt|i am an assistant)\b",
        re.IGNORECASE,
    ),
}


@dataclass(slots=True)
class OutputValidationResult:
    """Best-effort leakage detection signal, NOT prevention.

    Content has already been generated when this runs.
    Use for monitoring, alerting, and post-hoc analysis.
    """

    blocked: bool
    score: float
    labels: list[str]
    secrets_found: list[str] | None = None
    pii_found: list[str] | None = None
    exfil_indicators: list[str] | None = None

    def __post_init__(self) -> None:
        if self.secrets_found is None:
            object.__setattr__(self, "secrets_found", [])
        if self.pii_found is None:
            object.__setattr__(self, "pii_found", [])
        if self.exfil_indicators is None:
            object.__setattr__(self, "exfil_indicators", [])


def detect_secrets(text: str) -> list[str]:
    """
    Detect potential secrets/API keys in text.

    Uses expanded pattern set covering major cloud providers and services.
    """
    if not text:
        return []

    found = []
    for name, pattern in SECRET_PATTERNS.items():
        if pattern.search(text):
            found.append(name)
    return found


def detect_pii(text: str) -> list[str]:
    """Detect potential PII in text."""
    if not text:
        return []

    found = []
    for name, pattern in PII_PATTERNS.items():
        if pattern.search(text):
            found.append(name)
    return found


def detect_data_exfiltration(text: str) -> list[str]:
    """
    Detect potential data exfiltration attempts.

    Looks for:
    - External URLs (especially with query parameters)
    - Webhook URLs
    - Markdown image exfiltration (![](url?data=...))
    - Data URLs with encoded content
    """
    if not text:
        return []

    found = []
    for name, pattern in EXFIL_PATTERNS.items():
        if pattern.search(text):
            found.append(name)

    # Check for suspicious URL patterns (data in query string)
    url_match = re.search(
        r"https?://[^\s]+\?[^\s]*(?:data|token|key|secret|password)=[^\s&]+",
        text,
        re.IGNORECASE,
    )
    if url_match:
        found.append("suspicious_url_params")

    return found


def detect_sensitive_data_leakage(text: str) -> list[str]:
    """Detect likely system prompt or instruction leakage."""
    if not text:
        return []

    found = []
    for name, pattern in LEAKAGE_PATTERNS.items():
        if pattern.search(text):
            found.append(name)
    return found


def validate_output(
    text: str,
    *,
    block_threshold: float = 0.5,
    block_on_secrets: bool = True,
    custom_secret_patterns: dict[str, re.Pattern[str]] | None = None,
) -> OutputValidationResult:
    """Validate model output for sensitive data and exfiltration.

    WARNING: This is DETECTION, not PREVENTION. The model has already
    generated this content. Use for logging, alerting, and filtering
    responses before they reach end users.
    """
    if not text:
        return OutputValidationResult(
            blocked=False,
            score=0.0,
            labels=[],
        )

    # Detect all categories
    secrets = detect_secrets(text)
    pii = detect_pii(text)
    exfil = detect_data_exfiltration(text)
    leakage = detect_sensitive_data_leakage(text)

    # Check custom patterns
    if custom_secret_patterns:
        for name, pattern in custom_secret_patterns.items():
            if pattern.search(text):
                secrets.append(f"custom:{name}")

    # Combine labels
    labels = []
    if secrets:
        labels.append("secret_detected")
    if pii:
        labels.append("pii_detected")
    if exfil:
        labels.append("exfil_indicator")
    if leakage:
        labels.append("prompt_leakage")

    # Calculate score
    score = 0.0
    score += min(0.5, len(secrets) * 0.25)  # Secrets are high severity
    score += min(0.3, len(pii) * 0.15)
    score += min(0.3, len(exfil) * 0.15)
    score += min(0.2, len(leakage) * 0.1)
    score = min(1.0, score)

    # Determine blocking
    blocked = score >= block_threshold
    if block_on_secrets and secrets:
        blocked = True

    if blocked:
        logger.info(
            "Output blocked: score=%.2f labels=%s secrets=%s pii=%s exfil=%s",
            score,
            sorted(set(labels)),
            secrets,
            pii,
            exfil,
        )
    elif labels:
        logger.debug("Output flagged (below threshold): score=%.2f labels=%s", score, labels)

    return OutputValidationResult(
        blocked=blocked,
        score=score,
        labels=sorted(set(labels)),
        secrets_found=secrets,
        pii_found=pii,
        exfil_indicators=exfil,
    )
