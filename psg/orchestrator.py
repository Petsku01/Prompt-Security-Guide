from __future__ import annotations

import logging
import time

from .catalog import load_catalog
from .checkpoint import JSONLCheckpoint
from .errors import CatalogError, ReportError
from .execution.multi_turn import _process_multi_turn_attack as _process_multi_turn_attack_impl
from .execution.parallel import _run_attacks_parallel as _run_attacks_parallel_impl
from .execution.sequential import _run_attacks_sequential as _run_attacks_sequential_impl
from .execution.crescendo import run_crescendo_attack
from .execution.many_shot import run_many_shot_attack
from .execution.single_turn import _classify_attack_response as _classify_attack_response_impl
from .execution.single_turn import _process_attack as _process_attack_impl
from .llm.client import OpenAICompatibleClient
from .llm.transport import Transport
from .models import AppConfig, Attack, AttemptResult, RunSummary
from .reporting.defense_report import write_defense_report
from .reporting.json_report import write_json_report
from .reporting.text_report import write_text_report
from .security.classifier import ClassificationResult
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
    detector_failures = sum(1 for r in results if r.detector_failed)
    summary = RunSummary(
        total=len(results),
        succeeded=sum(1 for r in results if not r.error),
        failed=sum(1 for r in results if r.error),
        flagged=sum(1 for r in results if r.flagged),
        duration_seconds=elapsed,
        report_write_failed=False,
        detector_failures=detector_failures,
    )

    if detector_failures:
        # Loud warning: a "green" scan with a dead detector is misleading.
        logger.warning(
            "Detector failed to classify %d/%d attacks. Scan results may be unreliable.",
            detector_failures,
            len(results),
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
    if cfg.workers <= 1:
        return _run_attacks_sequential(
            cfg=cfg,
            attacks=attacks,
            client=client,
            checkpoint=checkpoint,
            detector=detector,
            system_prompt=system_prompt,
            checkpoint_tag=checkpoint_tag,
        )
    return _run_attacks_parallel(
        cfg=cfg,
        attacks=attacks,
        client=client,
        checkpoint=checkpoint,
        detector=detector,
        system_prompt=system_prompt,
        checkpoint_tag=checkpoint_tag,
    )


def _run_attacks_sequential(
    *,
    cfg: AppConfig,
    attacks: list[Attack],
    client: OpenAICompatibleClient,
    checkpoint: JSONLCheckpoint,
    detector: Detector,
    system_prompt: str | None,
    checkpoint_tag: str,
) -> list[AttemptResult]:
    return _run_attacks_sequential_impl(
        cfg=cfg,
        attacks=attacks,
        client=client,
        checkpoint=checkpoint,
        detector=detector,
        system_prompt=system_prompt,
        checkpoint_tag=checkpoint_tag,
        process_attack_fn=lambda cfg, attack, client, detector, system_prompt: _process_attack(
            cfg=cfg,
            attack=attack,
            client=client,
            detector=detector,
            system_prompt=system_prompt,
        ),
    )


def _run_attacks_parallel(
    *,
    cfg: AppConfig,
    attacks: list[Attack],
    client: OpenAICompatibleClient,
    checkpoint: JSONLCheckpoint,
    detector: Detector,
    system_prompt: str | None,
    checkpoint_tag: str,
) -> list[AttemptResult]:
    return _run_attacks_parallel_impl(
        cfg=cfg,
        attacks=attacks,
        client=client,
        checkpoint=checkpoint,
        detector=detector,
        system_prompt=system_prompt,
        checkpoint_tag=checkpoint_tag,
        process_attack_fn=lambda cfg, attack, client, detector, system_prompt: _process_attack(
            cfg=cfg,
            attack=attack,
            client=client,
            detector=detector,
            system_prompt=system_prompt,
        ),
    )


def _process_attack(
    *,
    cfg: AppConfig,
    attack: Attack,
    client: OpenAICompatibleClient,
    detector: Detector,
    system_prompt: str | None,
) -> AttemptResult:
    # Dispatch to alternative attack modes if configured
    if cfg.attack_mode == "crescendo":
        return run_crescendo_attack(
            cfg=cfg,
            attack=attack,
            client=client,
            detector=detector,
            system_prompt=system_prompt,
            max_turns=cfg.crescendo_turns,
        )
    if cfg.attack_mode == "many-shot":
        return run_many_shot_attack(
            cfg=cfg,
            attack=attack,
            client=client,
            detector=detector,
            system_prompt=system_prompt,
            num_examples=cfg.many_shot_examples,
        )

    return _process_attack_impl(
        cfg=cfg,
        attack=attack,
        client=client,
        detector=detector,
        system_prompt=system_prompt,
        process_multi_turn_attack_fn=lambda cfg, attack, client, detector, system_prompt: _process_multi_turn_attack(
            cfg=cfg,
            attack=attack,
            client=client,
            detector=detector,
            system_prompt=system_prompt,
        ),
        classify_attack_response_fn=lambda cfg, detector, prompt, raw_response, redacted_response: _classify_attack_response(
            cfg=cfg,
            detector=detector,
            prompt=prompt,
            raw_response=raw_response,
            redacted_response=redacted_response,
        ),
        redactor=redact_text,
    )


def _process_multi_turn_attack(
    *,
    cfg: AppConfig,
    attack: Attack,
    client: OpenAICompatibleClient,
    detector: Detector,
    system_prompt: str | None,
) -> AttemptResult:
    return _process_multi_turn_attack_impl(
        cfg=cfg,
        attack=attack,
        client=client,
        detector=detector,
        system_prompt=system_prompt,
        classify_attack_response_fn=lambda cfg, detector, prompt, raw_response, redacted_response: _classify_attack_response(
            cfg=cfg,
            detector=detector,
            prompt=prompt,
            raw_response=raw_response,
            redacted_response=redacted_response,
        ),
        redactor=redact_text,
    )


def _classify_attack_response(
    *,
    cfg: AppConfig,
    detector: Detector,
    prompt: str,
    raw_response: str,
    redacted_response: str,
) -> ClassificationResult:
    return _classify_attack_response_impl(
        cfg=cfg,
        detector=detector,
        prompt=prompt,
        raw_response=raw_response,
        redacted_response=redacted_response,
    )
