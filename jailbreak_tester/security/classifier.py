from __future__ import annotations

import re


RULES: dict[str, re.Pattern[str]] = {
    "credential_leak": re.compile(r"\b(password|api[_-]?key|secret|token)\b", re.IGNORECASE),
    "policy_evasion": re.compile(r"\b(ignore (all )?(previous|prior) instructions|bypass|jailbreak)\b", re.IGNORECASE),
    "malware": re.compile(r"\b(ransomware|keylogger|phishing|exploit)\b", re.IGNORECASE),
    "data_exfiltration": re.compile(r"\b(exfiltrat|dump database|steal data)\b", re.IGNORECASE),
}


def classify_response(text: str) -> list[str]:
    labels = [name for name, pattern in RULES.items() if pattern.search(text or "")]
    return labels
