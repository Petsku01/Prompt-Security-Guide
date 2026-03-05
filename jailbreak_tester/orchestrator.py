from __future__ import annotations

import time
from dataclasses import asdict

from .catalog import load_catalog
from .checkpoint import JSONLCheckpoint
from .llm.client import OpenAICompatibleClient
from .llm.errors import LLMError
from .llm.transport import Transport
from .models import AppConfig, AttemptResult, RunSummary
from .reporting.json_report import write_json_report
from .reporting.text_report import write_text_report
from .security.classifier import classify_response
from .security.redaction import redact_text


def run(cfg: AppConfig) -> tuple[RunSummary, list[AttemptResult]]:
    started = time.perf_counter()
    attacks = load_catalog(cfg.catalog_path)

    transport = Transport(
        timeout_seconds=cfg.timeout_seconds,
        max_retries=cfg.max_retries,
        backoff_base_seconds=cfg.backoff_base_seconds,
        backoff_cap_seconds=cfg.backoff_cap_seconds,
    )
    client = OpenAICompatibleClient(cfg.base_url, transport)
    checkpoint = JSONLCheckpoint(cfg.checkpoint_path)

    results: list[AttemptResult] = []

    for attack in attacks:
        try:
            llm_resp = client.chat(model=cfg.model, prompt=attack.prompt, temperature=cfg.temperature)
            redacted_text = redact_text(llm_resp.content, cfg.redaction_mode)
            labels = classify_response(redacted_text)
            result = AttemptResult(
                attack_id=attack.id,
                prompt=attack.prompt,
                response_text=redacted_text,
                flagged=bool(labels),
                labels=labels,
            )
        except LLMError as exc:
            result = AttemptResult(
                attack_id=attack.id,
                prompt=attack.prompt,
                response_text="",
                flagged=False,
                labels=[],
                error=str(exc),
            )

        checkpoint.append(asdict(result))
        results.append(result)

    elapsed = time.perf_counter() - started
    summary = RunSummary(
        total=len(results),
        succeeded=sum(1 for r in results if not r.error),
        failed=sum(1 for r in results if r.error),
        flagged=sum(1 for r in results if r.flagged),
        duration_seconds=elapsed,
    )

    write_json_report(cfg.report_json_path, summary, results)
    write_text_report(cfg.report_text_path, summary, results)
    return summary, results
