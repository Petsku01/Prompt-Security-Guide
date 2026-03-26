from __future__ import annotations

import logging
from typing import Callable

from ..errors import ClassifierError
from ..llm.client import OpenAICompatibleClient
from ..llm.errors import LLMError
from ..models import AppConfig, Attack, AttemptResult, ClassificationInputMode, RedactionMode
from ..security.classifier import ClassificationResult
from ..security.detectors import Detector
from ..security.redaction import redact_text

logger = logging.getLogger(__name__)


ProcessMultiTurnFn = Callable[
    [
        AppConfig,
        Attack,
        OpenAICompatibleClient,
        Detector,
        str | None,
    ],
    AttemptResult,
]

ClassifyAttackResponseFn = Callable[
    [AppConfig, Detector, str, str, str],
    ClassificationResult,
]



def _process_attack(
    *,
    cfg: AppConfig,
    attack: Attack,
    client: OpenAICompatibleClient,
    detector: Detector,
    system_prompt: str | None,
    process_multi_turn_attack_fn: ProcessMultiTurnFn | None = None,
    classify_attack_response_fn: ClassifyAttackResponseFn | None = None,
    redactor: Callable[[str, RedactionMode], str] = redact_text,
) -> AttemptResult:
    process_multi_turn = process_multi_turn_attack_fn
    if process_multi_turn is None:
        from .multi_turn import _process_multi_turn_attack

        def _default_process_multi_turn(
            cfg: AppConfig,
            attack: Attack,
            client: OpenAICompatibleClient,
            detector: Detector,
            system_prompt: str | None,
        ) -> AttemptResult:
            return _process_multi_turn_attack(
                cfg=cfg,
                attack=attack,
                client=client,
                detector=detector,
                system_prompt=system_prompt,
            )

        process_multi_turn = _default_process_multi_turn

    classify = classify_attack_response_fn or _classify_attack_response

    if cfg.multi_turn and attack.followups:
        return process_multi_turn(cfg, attack, client, detector, system_prompt)

    redacted_prompt = redactor(attack.prompt, cfg.redaction_mode)
    try:
        llm_resp = client.chat(
            model=cfg.model,
            prompt=attack.prompt,
            system_prompt=system_prompt,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        )
        redacted_text = redactor(llm_resp.content, cfg.redaction_mode)
        try:
            classification = classify(
                cfg,
                detector,
                attack.prompt,
                llm_resp.content,
                redacted_text,
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
        if cfg.detector == "keyword":
            inputs = [raw_response]
        else:
            inputs = [redacted_response]

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
