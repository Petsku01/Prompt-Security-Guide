#!/usr/bin/env python3
"""
CLI entrypoint for security testing.

This module handles:
- Argument parsing
- Console output/progress

- JSON file writing

All business logic lives in runner.py.
"""
import argparse
import sys
from typing import Optional

from .config import RunConfig
from .runner import create_runner
from .attacks import get_attacks, list_categories, Attack
from .schema import AttackResult


def print_progress(attack: Attack, result: AttackResult, index: int, total: int, verbose: bool):
    """Print progress for a single attack."""
    status = "SUCCEEDED" if result.success else "BLOCKED"
    if result.error:
        status = f"ERROR: {result.error[:50]}"

    print(f"[{index}/{total}] {attack.id}: {attack.name}")

    if result.success:
        print(f"         {status} (confidence: {result.confidence:.0%})")
        if verbose and result.matched_indicators:
            print(f"         Matched: {result.matched_indicators}")
    elif result.error:
        print(f"         {status}")
    else:
        print(f"         {status} ({result.time_ms}ms)")


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        description="LLM Security Tester",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Provider options
    parser.add_argument("--provider", "-p", choices=["ollama"], default="ollama")
    parser.add_argument("--model", "-m", default="qwen2.5:3b")
    parser.add_argument("--api-key")

    # Reproducibility options
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    parser.add_argument("--temperature", type=float, default=0.7)

    # Detection options
    parser.add_argument("--detector", "-d", choices=["substring", "llm_judge"], default="substring")
    parser.add_argument("--judge-model", default="qwen2.5:3b")
    parser.add_argument("--judge-temperature", type=float, default=0.1)
    parser.add_argument(
        "--allow-judge-fallback",
        action="store_true",
        help="Fall back to substring matching if judge unavailable",
    )

    # Attack filtering
    parser.add_argument("--categories", "-c")
    parser.add_argument("--list-categories", action="store_true")

    # Output options
    parser.add_argument("--output", "-o")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--no-system-prompt", action="store_true")

    args = parser.parse_args(argv)

    if args.list_categories:
        print("Available attack categories:")
        for cat in list_categories():
            print(f"  - {cat}")
        return 0

    # Build config
    config = RunConfig(
        provider=args.provider,
        model=args.model,
        api_key=args.api_key,
        seed=args.seed,
        temperature=args.temperature,
        detector=args.detector,
        judge_model=args.judge_model,
        judge_temperature=args.judge_temperature,
        allow_judge_fallback=args.allow_judge_fallback,
        categories=args.categories.split(",") if args.categories else None,
        verbose=args.verbose,
        output_file=args.output,
        system_prompt=None if args.no_system_prompt else "You are a helpful assistant.",
    )

    # Get attacks
    attacks = get_attacks(categories=config.categories)
    if not attacks:
        print("No attacks found matching criteria")
        return 1

    # Create runner with progress callback
    runner = create_runner(config)

    attack_index = [0]  # Mutable counter for closure

    def on_progress(attack: Attack, result: AttackResult):
        attack_index[0] += 1
        print_progress(attack, result, attack_index[0], len(attacks), config.verbose)

    runner.on_attack_complete = on_progress

    # Run tests
    print(f"\nRunning {len(attacks)} attacks against {runner.provider.name}")
    print(f"Detector: {runner.detector.name}")
    print("=" * 60)

    test_run = runner.run(attacks, config.system_prompt)

    # Print summary
    print()
    print("=" * 60)
    print(f"RESULTS: {test_run.successful}/{test_run.total_attacks} succeeded ({test_run.success_rate:.1f}%)")
    print("=" * 60)

    print("\nBy Category:")
    for cat, stats in sorted(test_run.categories.items()):
        pct = 100 * stats["success"] / stats["total"] if stats["total"] > 0 else 0
        print(f"  {cat}: {stats['success']}/{stats['total']} ({pct:.0f}%)")

    if test_run.warnings:
        print("\nWarnings:")
        for w in test_run.warnings:
            print(f"   {w}")

    if test_run.successful > 0:
        print("\nSuccessful Attacks:")
        for r in test_run.results:
            if r.success:
                print(f"  [{r.id}] {r.name}")

    # Save output
    if config.output_file:
        with open(config.output_file, "w", encoding="utf-8") as f:
            f.write(test_run.to_json())
        print(f"\nSaved to: {config.output_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
