from __future__ import annotations

import logging
import time

from .catalog import load_catalog
from .checkpoint import JSONLCheckpoint
from .errors import CatalogError, ReportError
from .execution.crescendo import run_crescendo_attack
from .execution.many_shot import run_many_shot_attack
from .execution.parallel import _run_attacks_parallel as _run_attacks_parallel_impl
from .execution.sequential import _run_attacks_sequential as _run_attacks_sequential_impl
from .execution.single_turn import _process_attack as _process_attack_impl
from .llm.client import OpenAICompatibleClient
from .llm.transport import Transport
from .models import AppConfig, Attack, AttemptResult, RunSummary
from .reporting.defense_report import write_defense_report
from .reporting.json_report import write_json_report
from .reporting.text_report import write_text_report
from .security.detectors import Detector, build_detector

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
    """Dispatch to sequential or parallel execution based on cfg.workers."""
    runner = _run_attacks_parallel_impl if cfg.workers > 1 else _run_attacks_sequential_impl
    return runner(
        cfg=cfg,
        attacks=attacks,
        client=client,
        checkpoint=checkpoint,
        detector=detector,
        system_prompt=system_prompt,
        checkpoint_tag=checkpoint_tag,
        process_attack_fn=_process_attack,
    )


def _process_attack(
    cfg: AppConfig,
    attack: Attack,
    client: OpenAICompatibleClient,
    detector: Detector,
    system_prompt: str | None,
) -> AttemptResult:
    """Process a single attack, dispatching by ``cfg.attack_mode``.

    Signature intentionally positional so it can be passed as the
    ``process_attack_fn`` callback to sequential/parallel runners without
    a lambda adapter.
    """
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
    # Single-turn path: the impl's None-defaults resolve to the correct
    # multi-turn and classify helpers, so no injection lambdas are needed.
    return _process_attack_impl(
        cfg=cfg,
        attack=attack,
        client=client,
        detector=detector,
        system_prompt=system_prompt,
    )
