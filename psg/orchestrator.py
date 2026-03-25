from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from threading import Lock, Semaphore

from .catalog import load_catalog
from .checkpoint import JSONLCheckpoint
from .errors import CatalogError, ClassifierError, ReportError
from .llm.client import OpenAICompatibleClient
from .llm.errors import LLMError
from .llm.transport import Transport
from .models import AppConfig, Attack, AttemptResult, ClassificationInputMode, RunSummary
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
    """Run attacks sequentially (original behavior)."""
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


class _RateLimiter:
    """Simple token bucket rate limiter for controlling request rate."""
    
    def __init__(self, rate: float | None) -> None:
        self.rate = rate  # requests per second
        self.lock = Lock()
        self.last_request = 0.0
    
    def acquire(self) -> None:
        """Block until a request is allowed."""
        if self.rate is None or self.rate <= 0:
            return
        
        with self.lock:
            now = time.perf_counter()
            min_interval = 1.0 / self.rate
            elapsed = now - self.last_request
            
            if elapsed < min_interval:
                sleep_time = min_interval - elapsed
                time.sleep(sleep_time)
            
            self.last_request = time.perf_counter()


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
    """Run attacks in parallel using ThreadPoolExecutor.
    
    Thread-safety notes:
    - OpenAICompatibleClient uses requests.post() which is thread-safe
    - Checkpoint writes are protected by a lock
    - Rate limiting uses a simple token bucket algorithm
    - Each _process_attack call is independent (no shared mutable state)
    """
    results: dict[str, AttemptResult] = {}
    checkpoint_lock = Lock()
    rate_limiter = _RateLimiter(cfg.rate_limit)
    completed = 0
    total = len(attacks)
    
    def process_one(attack: Attack) -> tuple[str, AttemptResult]:
        nonlocal completed
        # Rate limiting - wait if needed before making request
        rate_limiter.acquire()
        
        # _process_attack already handles all exceptions internally
        result = _process_attack(
            cfg=cfg,
            attack=attack,
            client=client,
            detector=detector,
            system_prompt=system_prompt,
        )
        # Thread-safe checkpoint write
        with checkpoint_lock:
            try:
                checkpoint.append({**asdict(result), "mode": checkpoint_tag})
            except Exception:
                logger.exception("failed to append checkpoint for attack_id=%s mode=%s", attack.id, checkpoint_tag)
            completed += 1
            if completed % 10 == 0 or completed == total:
                logger.info("Progress: %d/%d attacks completed", completed, total)
        return attack.id, result
    
    # Validate workers count
    workers = min(cfg.workers, len(attacks), 32)  # Cap at 32 to avoid excessive threads
    if workers != cfg.workers:
        logger.warning("Adjusted workers from %d to %d", cfg.workers, workers)
    
    if cfg.rate_limit:
        logger.info("Running %d attacks with %d workers (rate limit: %.1f req/s)", total, workers, cfg.rate_limit)
    else:
        logger.info("Running %d attacks with %d workers", total, workers)
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_one, attack): attack for attack in attacks}
        
        for future in as_completed(futures):
            attack = futures[future]
            # _process_attack handles errors, so future.result() should not raise
            attack_id, result = future.result()
            results[attack_id] = result
    
    # Preserve original order
    return [results[attack.id] for attack in attacks]


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
        redacted_text = redact_text(llm_resp.content, cfg.redaction_mode)
        try:
            classification = _classify_attack_response(
                cfg=cfg,
                detector=detector,
                prompt=attack.prompt,
                raw_response=llm_resp.content,
                redacted_response=redacted_text,
            )
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


def _classify_attack_response(
    *,
    cfg: AppConfig,
    detector: Detector,
    prompt: str,
    raw_response: str,
    redacted_response: str,
) -> ClassificationResult:
    inputs: list[str]
    mode = cfg.classification_input_mode
    if mode == ClassificationInputMode.RAW:
        inputs = [raw_response]
    elif mode == ClassificationInputMode.REDACTED:
        inputs = [redacted_response]
    elif mode == ClassificationInputMode.BOTH:
        inputs = [raw_response, redacted_response]
    else:
        # Default to safer boundary for judge-backed detectors that may call remote endpoints.
        if cfg.detector == "keyword":
            inputs = [raw_response]
        else:
            inputs = [redacted_response]

    # Avoid duplicate work when redaction does not change output.
    unique_inputs = list(dict.fromkeys(inputs))
    results = [detector.classify(prompt=prompt, response=response) for response in unique_inputs]
    if len(results) == 1:
        return results[0]
    return _merge_classifications(results)


def _merge_classifications(results: list[ClassificationResult]) -> ClassificationResult:
    return ClassificationResult(
        is_refusal=all(r.is_refusal for r in results),
        is_harmful=any(r.is_harmful for r in results),
        attack_successful=any(r.attack_successful for r in results),
        harm_score=max(r.harm_score for r in results),
        refusal_confidence=max(r.refusal_confidence for r in results),
        harmful_labels=sorted({label for r in results for label in r.harmful_labels}),
        compliance_detected=any(r.compliance_detected for r in results),
        has_disclaimer=any(r.has_disclaimer for r in results),
        raw_text_length=max(r.raw_text_length for r in results),
    )
