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
from .models import AppConfig, Attack, AttemptResult, RunSummary
from .reporting.defense_report import write_defense_report
from .reporting.json_report import write_json_report
from .reporting.text_report import write_text_report
from .security.detectors import Detector, build_detector
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
    client = OpenAICompatibleClient(cfg.base_url, transport, api_key=cfg.api_key)
    checkpoint = JSONLCheckpoint(cfg.checkpoint_path)
    detector = build_detector(cfg)

    defended_results = _run_attacks(
        cfg=cfg,
        attacks=attacks,
        client=client,
        checkpoint=checkpoint,
        detector=detector,
        system_prompt=cfg.system_prompt,
        checkpoint_tag="defended",
    )
    results = defended_results

    baseline_results: list[AttemptResult] | None = None
    if cfg.defense_report and cfg.system_prompt:
        baseline_results = _run_attacks(
            cfg=cfg,
            attacks=attacks,
            client=client,
            checkpoint=checkpoint,
            detector=detector,
            system_prompt=None,
            checkpoint_tag="baseline",
        )

    elapsed = time.perf_counter() - started
    summary = RunSummary(
        total=len(results),
        succeeded=sum(1 for r in results if not r.error),
        failed=sum(1 for r in results if r.error),
        flagged=sum(1 for r in results if r.flagged),
        duration_seconds=elapsed,
        report_write_failed=False,
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

    if cfg.defense_report:
        try:
            write_defense_report(
                cfg.defense_report_path,
                model=cfg.model,
                catalog_path=cfg.catalog_path,
                system_prompt=cfg.system_prompt,
                attacks=attacks,
                defended_results=defended_results,
                baseline_results=baseline_results,
            )
        except Exception as exc:
            err = ReportError(f"failed writing report {cfg.defense_report_path}: {exc}")
            logger.error(str(err))
            report_errors.append(str(err))

    if report_errors:
        logger.warning("run completed with report errors: %s", "; ".join(report_errors))
        summary.report_write_failed = True

    return summary, results


def _run_attacks(
    *,
    cfg: AppConfig,
    attacks: list[Attack],
    client: OpenAICompatibleClient,
    checkpoint: JSONLCheckpoint,
    detector: Detector,
    system_prompt: str | None,
    checkpoint_tag: str,
) -> list[AttemptResult]:
    results: list[AttemptResult] = []
    for attack in attacks:
        result = _process_attack(
            cfg=cfg,
            attack=attack,
            client=client,
            detector=detector,
            system_prompt=system_prompt,
        )
        try:
            checkpoint.append({**asdict(result), "mode": checkpoint_tag})
        except Exception:
            logger.exception("failed to append checkpoint for attack_id=%s mode=%s", attack.id, checkpoint_tag)
        results.append(result)
    return results


def _process_attack(
    *,
    cfg: AppConfig,
    attack: Attack,
    client: OpenAICompatibleClient,
    detector: Detector,
    system_prompt: str | None,
) -> AttemptResult:
    redacted_prompt = redact_text(attack.prompt, cfg.redaction_mode)
    try:
        llm_resp = client.chat(
            model=cfg.model,
            prompt=attack.prompt,
            system_prompt=system_prompt,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        )
        # Classify on raw output; redaction is for storage/reporting only.
        redacted_text = redact_text(llm_resp.content, cfg.redaction_mode)
        try:
            classification = detector.classify(prompt=attack.prompt, response=llm_resp.content)
        except Exception as exc:
            raise ClassifierError(f"classifier failed for attack_id={attack.id}: {exc}") from exc
        return AttemptResult(
            attack_id=attack.id,
            prompt=redacted_prompt,
            response_text=redacted_text,
            flagged=classification.attack_successful,
            labels=classification.harmful_labels,
            harm_score=classification.harm_score,
            is_refusal=classification.is_refusal,
            has_disclaimer=classification.has_disclaimer,
        )
    except (LLMError, ClassifierError) as exc:
        logger.error("attack processing failed for attack_id=%s: %s", attack.id, exc)
        return AttemptResult(
            attack_id=attack.id,
            prompt=redacted_prompt,
            response_text="",
            flagged=False,
            labels=[],
            error=str(exc),
        )
    except Exception as exc:
        logger.exception("unexpected attack processing error for attack_id=%s", attack.id)
        return AttemptResult(
            attack_id=attack.id,
            prompt=redacted_prompt,
            response_text="",
            flagged=False,
            labels=[],
            error=f"unexpected error: {exc}",
        )
