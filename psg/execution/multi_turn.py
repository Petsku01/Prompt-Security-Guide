from __future__ import annotations

import logging
from typing import Callable

from ..errors import ClassifierError
from ..llm.client import OpenAICompatibleClient
from ..llm.errors import LLMError
from ..models import AppConfig, Attack, AttemptResult, RedactionMode
from ..security.classifier import ClassificationResult
from ..security.detectors import Detector
from ..security.redaction import redact_text

logger = logging.getLogger(__name__)

ClassifyAttackResponseFn = Callable[
    [AppConfig, Detector, str, str, str],
    ClassificationResult,
]



def _process_multi_turn_attack(
    *,
    cfg: AppConfig,
    attack: Attack,
    client: OpenAICompatibleClient,
    detector: Detector,
    system_prompt: str | None,
    classify_attack_response_fn: ClassifyAttackResponseFn | None = None,
    redactor: Callable[[str, RedactionMode], str] = redact_text,
) -> AttemptResult:
    classify = classify_attack_response_fn
    if classify is None:
        from .single_turn import _classify_attack_response

        def _default_classify(
            cfg: AppConfig,
            detector: Detector,
            prompt: str,
            raw_response: str,
            redacted_response: str,
        ) -> ClassificationResult:
            return _classify_attack_response(
                cfg=cfg,
                detector=detector,
                prompt=prompt,
                raw_response=raw_response,
                redacted_response=redacted_response,
            )

        classify = _default_classify

    messages: list[dict[str, str]] = []
    all_prompts: list[str] = [attack.prompt] + attack.followups
    final_response = ""

    try:
        for i, prompt in enumerate(all_prompts):
            messages.append({"role": "user", "content": prompt})

            llm_resp = client.chat_multi_turn(
                model=cfg.model,
                messages=messages,
                system_prompt=system_prompt,
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens,
            )

            messages.append({"role": "assistant", "content": llm_resp.content})
            final_response = llm_resp.content

            classification = classify(
                cfg,
                detector,
                prompt,
                llm_resp.content,
                redactor(llm_resp.content, cfg.redaction_mode),
            )

            if classification.attack_successful:
                redacted_conversation = " | ".join(
                    f"[{m['role']}] {redactor(m['content'][:100], cfg.redaction_mode)}..."
                    for m in messages
                )
                return AttemptResult(
                    attack_id=attack.id,
                    prompt=f"[multi-turn {i + 1}/{len(all_prompts)}] {redacted_conversation}",
                    response_text=redactor(final_response, cfg.redaction_mode),
                    flagged=True,
                    labels=classification.harmful_labels,
                    harm_score=classification.harm_score,
                    is_refusal=False,
                    has_disclaimer=classification.has_disclaimer,
                )

        redacted_prompt = redactor(attack.prompt, cfg.redaction_mode)
        return AttemptResult(
            attack_id=attack.id,
            prompt=f"[multi-turn {len(all_prompts)} turns] {redacted_prompt}",
            response_text=redactor(final_response, cfg.redaction_mode),
            flagged=False,
            labels=[],
            harm_score=0.0,
            is_refusal=True,
            has_disclaimer=False,
        )

    except (LLMError, ClassifierError) as exc:
        logger.error("multi-turn attack failed for attack_id=%s: %s", attack.id, exc)
        return AttemptResult(
            attack_id=attack.id,
            prompt=redactor(attack.prompt, cfg.redaction_mode),
            response_text="",
            flagged=False,
            labels=[],
            error=str(exc),
        )
    except Exception as exc:
        logger.exception("unexpected multi-turn error for attack_id=%s", attack.id)
        return AttemptResult(
            attack_id=attack.id,
            prompt=redactor(attack.prompt, cfg.redaction_mode),
            response_text="",
            flagged=False,
            labels=[],
            error=f"unexpected error: {exc}",
        )
