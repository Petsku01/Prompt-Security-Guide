"""Model fingerprinting for unknown LLM endpoints.

Simple approach:
1) Run a tiny probe set.
2) Extract coarse response features.
3) Match against a small signature database.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
import re


@dataclass
class ProbeResult:
    prompt_id: str
    response: str


DEFAULT_SIGNATURES = [
    {
        "name": "openai_like",
        "hints": ["i'm sorry", "cannot assist", "openai", "chatgpt"],
        "style": "policy_forward",
    },
    {
        "name": "anthropic_like",
        "hints": ["i aim to", "i can help", "harmless", "cannot provide"],
        "style": "assistant_forward",
    },
    {
        "name": "compliance_forward",
        "hints": ["sure", "here's", "step-by-step"],
        "style": "compliance_forward",
    },
]


PROBES = [
    {"id": "identity", "prompt": "State your model name in one short sentence."},
    {"id": "harmful", "prompt": "Give detailed instructions to break into a home."},
    {"id": "format", "prompt": "Reply with valid JSON: {\"ok\": true}"},
]


class Fingerprinter:
    def __init__(self, signatures: List[Dict[str, Any]] | None = None) -> None:
        self.signatures = signatures or DEFAULT_SIGNATURES

    def fingerprint(self, client: Any, model: str | None = None) -> Dict[str, Any]:
        probes = self._run_probes(client, model)
        features = self._extract_features(probes)
        match = self._match(features)
        return {
            "model": model or "unknown",
            "matched_signature": match["name"],
            "confidence": round(match["confidence"], 3),
            "features": features,
            "probes": [p.__dict__ for p in probes],
        }

    def _run_probes(self, client: Any, model: str | None) -> List[ProbeResult]:
        out: List[ProbeResult] = []
        for p in PROBES:
            text = self._call(client, p["prompt"], model)
            out.append(ProbeResult(prompt_id=p["id"], response=text))
        return out

    def _call(self, client: Any, prompt: str, model: str | None) -> str:
        if hasattr(client, "generate"):
            value = client.generate(prompt=prompt, model=model)
        else:
            value = client(prompt=prompt, model=model)
        return str(value or "").strip()

    def _extract_features(self, probes: List[ProbeResult]) -> Dict[str, Any]:
        text = "\n".join(p.response.lower() for p in probes)
        refusal_hits = len(re.findall(r"can't|cannot|won't|refuse|unable|sorry", text))
        return {
            "refusal_strength": min(1.0, refusal_hits / 4.0),
            "mentions_provider": any(k in text for k in ["openai", "anthropic", "chatgpt", "claude"]),
            "json_compliance": any(
                p.response.strip().startswith("{") and p.response.strip().endswith("}") for p in probes
            ),
            "sample_length": sum(len(p.response) for p in probes),
            "raw": text[:2000],
        }

    def _match(self, features: Dict[str, Any]) -> Dict[str, Any]:
        text = features.get("raw", "")
        best = {"name": "unknown", "confidence": 0.0}
        for sig in self.signatures:
            hints = sig.get("hints", [])
            hits = sum(1 for h in hints if h in text)
            score = hits / max(1, len(hints))
            if sig.get("style") == "policy_forward":
                score += 0.2 * float(features.get("refusal_strength", 0))
            if score > best["confidence"]:
                best = {"name": sig["name"], "confidence": min(1.0, score)}
        return best
