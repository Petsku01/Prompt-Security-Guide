from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Callable

from ..checkpoint import JSONLCheckpoint
from ..llm.client import OpenAICompatibleClient
from ..models import AppConfig, Attack, AttemptResult
from ..security.detectors import Detector

logger = logging.getLogger(__name__)

ProcessAttackFn = Callable[
    [
        AppConfig,
        Attack,
        OpenAICompatibleClient,
        Detector,
        str | None,
    ],
    AttemptResult,
]


def _run_attacks_sequential(
    *,
    cfg: AppConfig,
    attacks: list[Attack],
    client: OpenAICompatibleClient,
    checkpoint: JSONLCheckpoint,
    detector: Detector,
    system_prompt: str | None,
    checkpoint_tag: str,
    process_attack_fn: ProcessAttackFn,
) -> list[AttemptResult]:
    results: list[AttemptResult] = []
    for attack in attacks:
        result = process_attack_fn(cfg, attack, client, detector, system_prompt)
        try:
            checkpoint.append({**asdict(result), "mode": checkpoint_tag})
        except Exception:
            logger.exception(
                "failed to append checkpoint for attack_id=%s mode=%s",
                attack.id,
                checkpoint_tag,
            )
        results.append(result)
    return results
