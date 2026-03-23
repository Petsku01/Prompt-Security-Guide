from __future__ import annotations

import logging
import time
from dataclasses import asdict

from .catalog import load_catalog
from .checkpoint import JSONLCheckpoint
from .errors import CatalogError, ClassifierError, ReportError
from .llm.client import OpenAICompatibleClient
from .llm.errors import LLMError
from .llm.transport import Transport
from .models import AppConfig, AttemptResult, RunSummary
from .reporting.json_report import write_json_report
from .reporting.text_report import write_text_report
from .security.classifier import classify_response_v2
from .security.redaction import redact_text

logger = logging.getLogger(__name__)


def run(cfg: AppConfig) -> tuple[RunSummary, list[AttemptResult]]:
    started = time.perf_counter()
    try:
        attacks = load_catalog(cfg.catalog_path)
    except Exception as exc:
        raise CatalogError(f"failed to load catalog {cfg.catalog_path}: {exc}") from exc

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
            llm_resp = client.chat(
                model=cfg.model, 
                prompt=attack.prompt, 
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens
            )
            redacted_text = redact_text(llm_resp.content, cfg.redaction_mode)
            try:
                classification = classify_response_v2(redacted_text)
            except Exception as exc:
                raise ClassifierError(f"classifier failed for attack_id={attack.id}: {exc}") from exc
            result = AttemptResult(
                attack_id=attack.id,
                prompt=attack.prompt,
                response_text=redacted_text,
                flagged=classification.attack_successful,
                labels=classification.harmful_labels,
                harm_score=classification.harm_score,
                is_refusal=classification.is_refusal,
                has_disclaimer=classification.has_disclaimer,
            )
        except (LLMError, ClassifierError) as exc:
            logger.error("attack processing failed for attack_id=%s: %s", attack.id, exc)
            result = AttemptResult(
                attack_id=attack.id,
                prompt=attack.prompt,
                response_text="",
                flagged=False,
                labels=[],
                error=str(exc),
            )
        except Exception as exc:
            logger.exception("unexpected attack processing error for attack_id=%s", attack.id)
            result = AttemptResult(
                attack_id=attack.id,
                prompt=attack.prompt,
                response_text="",
                flagged=False,
                labels=[],
                error=f"unexpected error: {exc}",
            )

        try:
            checkpoint.append(asdict(result))
        except Exception:
            logger.exception("failed to append checkpoint for attack_id=%s", attack.id)
        results.append(result)

    elapsed = time.perf_counter() - started
    summary = RunSummary(
        total=len(results),
        succeeded=sum(1 for r in results if not r.error),
        failed=sum(1 for r in results if r.error),
        flagged=sum(1 for r in results if r.flagged),
        duration_seconds=elapsed,
    )

    report_errors: list[str] = []
    for report_path, writer in (
        (cfg.report_json_path, write_json_report),
        (cfg.report_text_path, write_text_report),
    ):
        try:
            writer(report_path, summary, results)
        except Exception as exc:
            err = ReportError(f"failed writing report {report_path}: {exc}")
            logger.error(str(err))
            report_errors.append(str(err))

    if report_errors:
        logger.warning("run completed with report errors: %s", "; ".join(report_errors))

    return summary, results
