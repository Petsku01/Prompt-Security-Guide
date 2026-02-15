"""
Core test runner - pure orchestration logic.

This module has NO CLI concerns, NO print statements, NO argparse.
It accepts typed configs and returns typed results.
"""
from typing import List, Optional, Callable
from .schema import TestRun, AttackResult, RuntimeConfig, SCHEMA_VERSION
from .config import RunConfig
from .providers import get_provider, BaseProvider
from .detection import get_detector, BaseDetector, JudgeUnavailableError
from .attacks import Attack


class TestRunner:
    """Orchestrates attack testing against a model."""

    def __init__(
        self,
        provider: BaseProvider,
        detector: BaseDetector,
        config: RunConfig,
        on_attack_complete: Optional[Callable[[Attack, AttackResult], None]] = None,
    ):
        self.provider = provider
        self.detector = detector
        self.config = config
        self.on_attack_complete = on_attack_complete  # Progress callback

    def run(self, attacks: List[Attack], system_prompt: Optional[str] = None) -> TestRun:
        """Execute attacks and return typed results."""
        results: List[AttackResult] = []
        warnings: List[str] = []
        successful = 0
        categories = {}

        for attack in attacks:
            result = self._run_single_attack(attack, system_prompt)
            results.append(result)

            if result.success:
                successful += 1

            # Track by category
            cat = attack.category
            if cat not in categories:
                categories[cat] = {"total": 0, "success": 0}
            categories[cat]["total"] += 1
            if result.success:
                categories[cat]["success"] += 1

            # Collect warnings
            if result.fallback_used:
                warnings.append(f"Attack {attack.id} used fallback detector")

            # Progress callback
            if self.on_attack_complete:
                self.on_attack_complete(attack, result)

        total = len(attacks)
        return TestRun(
            schema_version=SCHEMA_VERSION,
            provider=self.provider.name.split("/")[0] if "/" in self.provider.name else self.provider.name,
            model=self.config.model,
            detector=self.detector.name,
            system_prompt=system_prompt,
            runtime_config=RuntimeConfig(
                seed=self.config.seed,
                temperature=self.config.temperature,
                judge_temperature=self.config.judge_temperature,
            ),
            total_attacks=total,
            successful=successful,
            success_rate=100 * successful / total if total > 0 else 0.0,
            categories=categories,
            results=results,
            warnings=warnings,
        )

    def _run_single_attack(self, attack: Attack, system_prompt: Optional[str]) -> AttackResult:
        """Execute single attack and return result."""
        response = self.provider.call(attack.prompt, system_prompt)

        if response.error:
            return AttackResult(
                id=attack.id,
                name=attack.name,
                category=attack.category,
                success=False,
                confidence=0.0,
                matched_indicators=[],
                response_preview="",
                time_ms=response.time_ms,
                error=response.error,
            )

        try:
            detection = self.detector.detect(
                response.text,
                attack.indicators,
                attack.goal,
            )
        except JudgeUnavailableError as e:
            return AttackResult(
                id=attack.id,
                name=attack.name,
                category=attack.category,
                success=False,
                confidence=0.0,
                matched_indicators=[],
                response_preview=response.text[:500],
                time_ms=response.time_ms,
                error=str(e),
            )

        return AttackResult(
            id=attack.id,
            name=attack.name,
            category=attack.category,
            success=detection.success,
            confidence=detection.confidence,
            matched_indicators=detection.matched_indicators,
            response_preview=response.text[:500],
            time_ms=response.time_ms,
            reasoning=detection.reasoning,
            fallback_used=detection.fallback_used,
        )


def create_runner(config: RunConfig) -> TestRunner:
    """Factory function to create runner from config."""
    provider_kwargs = {"temperature": config.temperature}
    if config.seed is not None:
        provider_kwargs["seed"] = config.seed
    if config.api_key:
        provider_kwargs["api_key"] = config.api_key

    provider = get_provider(config.provider, config.model, **provider_kwargs)

    detector_kwargs = {}
    if config.detector == "llm_judge":
        detector_kwargs["model"] = config.judge_model
        detector_kwargs["fallback_to_substring"] = config.allow_judge_fallback
        detector_kwargs["temperature"] = config.judge_temperature

    detector = get_detector(config.detector, **detector_kwargs)

    return TestRunner(provider, detector, config)
