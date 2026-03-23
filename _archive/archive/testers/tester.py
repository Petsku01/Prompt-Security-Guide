#!/usr/bin/env python3
"""
Unified Security Tester

Single entry point for all LLM security testing.
Combines attacks from multiple modules with configurable detection.

Usage:
    python tester.py --provider ollama --model qwen2.5:3b
    python tester.py --provider groq --model llama3-8b-8192 --detector llm_judge
    python tester.py --provider ollama --model llama3:8b --categories hierarchy,identity
    python tester.py --provider ollama --model llama3:8b --detector multi_judge --judge-models qwen2.5:3b,mistral:7b
"""

import argparse
import json
import math
from datetime import datetime

from providers import get_provider
from detection import get_detector
from attacks import get_attacks, list_categories, Attack


def wilson_score_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a binomial proportion."""
    if total <= 0:
        return 0.0, 0.0

    p = successes / total
    z2 = z * z
    denom = 1 + z2 / total
    center = (p + z2 / (2 * total)) / denom
    margin = (z * math.sqrt((p * (1 - p) + z2 / (4 * total)) / total)) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def run_test(provider, detector, attacks: list, system_prompt: str = None, verbose: bool = False, runs: int = 1) -> dict:
    """Run attacks against a model and collect results."""

    results = []
    successful_runs = 0
    blocked_runs = 0
    errors = 0
    categories = {}

    total_attacks = len(attacks)
    total_runs = total_attacks * runs

    print(f"\nRunning {total_attacks} attacks x {runs} run(s) against {provider.name}")
    print(f"Detector: {detector.name}")
    print("=" * 60)

    for i, attack in enumerate(attacks, 1):
        print(f"[{i}/{total_attacks}] {attack.id}: {attack.name}")

        run_results = []
        attack_success_count = 0
        attack_error_count = 0

        for run_idx in range(1, runs + 1):
            response = provider.call(attack.prompt, system_prompt)

            if response.error:
                errors += 1
                attack_error_count += 1
                outcome = "error"
                run_result = {
                    "run": run_idx,
                    "success": False,
                    "outcome": outcome,
                    "error": response.error,
                    "time_ms": response.time_ms,
                }
            else:
                detection = detector.detect(response.text, attack.indicators, attack.goal)

                if detection.success:
                    successful_runs += 1
                    attack_success_count += 1
                    outcome = "success"
                else:
                    blocked_runs += 1
                    outcome = "blocked"

                run_result = {
                    "run": run_idx,
                    "success": detection.success,
                    "outcome": outcome,
                    "confidence": detection.confidence,
                    "matched_indicators": detection.matched_indicators,
                    "response": response.text[:500] if verbose else response.text[:200],
                    "response_full": response.text if verbose else None,
                    "time_ms": response.time_ms,
                    "reasoning": detection.reasoning,
                }

            run_results.append(run_result)

        attack_total_runs = len(run_results)
        attack_success_rate = (attack_success_count / attack_total_runs) if attack_total_runs > 0 else 0.0
        ci_low, ci_high = wilson_score_interval(attack_success_count, attack_total_runs)

        if runs == 1:
            only = run_results[0]
            if only["outcome"] == "error":
                error_type = "TIMEOUT" if "timeout" in (only.get("error") or "").lower() else "ERROR"
                print(f"         {error_type}: {only.get('error')}")
            elif only["success"]:
                print(f"         SUCCEEDED (confidence: {only.get('confidence', 0):.0%})")
                if verbose:
                    print(f"         Reason: {str(only.get('reasoning') or '')[:100]}")
                    print(f"         Matched: {only.get('matched_indicators')}")
            else:
                print(f"         BLOCKED ({only.get('time_ms')}ms)")
                if verbose and only.get("reasoning"):
                    print(f"         Reason: {str(only.get('reasoning'))[:100]}")
        else:
            run_summary = " | ".join(
                [f"Run {r['run']}: {'SUCCEEDED' if r['success'] else ('ERROR' if r['outcome'] == 'error' else 'BLOCKED')}" for r in run_results]
            )
            print(f"         {run_summary}")
            print(
                f"         Success Rate: {attack_success_rate * 100:.1f}% "
                f"({attack_success_count}/{attack_total_runs}), "
                f"95% CI: [{ci_low * 100:.1f}%, {ci_high * 100:.1f}%]"
            )

        result = {
            "id": attack.id,
            "name": attack.name,
            "category": attack.category,
            # Backward-compatible top-level fields: mirror first run when runs=1
            "success": run_results[0]["success"] if runs == 1 else attack_success_count > 0,
            "outcome": run_results[0]["outcome"] if runs == 1 else ("success" if attack_success_count > 0 else ("error" if attack_error_count == attack_total_runs else "blocked")),
            "error": run_results[0].get("error") if runs == 1 else None,
            "confidence": run_results[0].get("confidence") if runs == 1 else None,
            "matched_indicators": run_results[0].get("matched_indicators") if runs == 1 else None,
            "response": run_results[0].get("response") if runs == 1 else None,
            "response_full": run_results[0].get("response_full") if runs == 1 else None,
            "time_ms": run_results[0].get("time_ms") if runs == 1 else None,
            "reasoning": run_results[0].get("reasoning") if runs == 1 else None,
            # New multi-run statistics
            "success_count": attack_success_count,
            "total_runs": attack_total_runs,
            "error_count": attack_error_count,
            "success_rate": attack_success_rate,
            "ci_95_wilson": {
                "low": ci_low,
                "high": ci_high,
            },
            "runs": run_results,
        }

        cat = attack.category
        if cat not in categories:
            categories[cat] = {
                "attacks": 0,
                "total_runs": 0,
                "success": 0,
                "blocked": 0,
                "error": 0,
            }
        categories[cat]["attacks"] += 1
        categories[cat]["total_runs"] += attack_total_runs
        categories[cat]["success"] += attack_success_count
        categories[cat]["error"] += attack_error_count
        categories[cat]["blocked"] += (attack_total_runs - attack_success_count - attack_error_count)

        results.append(result)

    print()
    print("=" * 60)
    success_rate = 100 * successful_runs / total_runs if total_runs > 0 else 0
    ci_low, ci_high = wilson_score_interval(successful_runs, total_runs)

    print(f"RESULTS: {successful_runs}/{total_runs} succeeded ({success_rate:.1f}%)")
    print(f"         95% CI (Wilson): [{ci_low * 100:.1f}%, {ci_high * 100:.1f}%]")
    if errors > 0:
        print(f"         {errors} errors/timeouts (excluded from adjusted security analysis)")
        actual_tests = total_runs - errors
        if actual_tests > 0:
            adjusted_rate = 100 * successful_runs / actual_tests
            adj_low, adj_high = wilson_score_interval(successful_runs, actual_tests)
            print(
                f"         Adjusted rate (excluding errors): {successful_runs}/{actual_tests} ({adjusted_rate:.1f}%), "
                f"95% CI: [{adj_low * 100:.1f}%, {adj_high * 100:.1f}%]"
            )
    print("=" * 60)

    print("\nBy Category (aggregated across runs):")
    for cat, stats in sorted(categories.items()):
        pct = 100 * stats["success"] / stats["total_runs"] if stats["total_runs"] > 0 else 0
        cat_low, cat_high = wilson_score_interval(stats["success"], stats["total_runs"])
        error_note = f", {stats['error']} errors" if stats["error"] > 0 else ""
        print(
            f"  {cat}: {stats['success']}/{stats['total_runs']} ({pct:.1f}%), "
            f"95% CI: [{cat_low * 100:.1f}%, {cat_high * 100:.1f}%], "
            f"{stats['attacks']} attacks{error_note}"
        )

    successful_attack_count = sum(1 for r in results if r.get("success_count", 0) > 0)
    if successful_attack_count > 0:
        print("\nSuccessful Attacks:")
        for r in results:
            if r.get("success_count", 0) > 0:
                print(f"  [{r['id']}] {r['name']}: {r['success_count']}/{r['total_runs']}")

    if errors > 0:
        print("\nErrors/Timeouts (not security failures):")
        for r in results:
            for run in r.get("runs", []):
                if run.get("outcome") == "error":
                    print(f"  [{r['id']}] {r['name']} run {run.get('run')}: {str(run.get('error', 'unknown'))[:50]}")

    adjusted_total = total_runs - errors

    return {
        "timestamp": datetime.now().isoformat(),
        "provider": provider.name,
        "detector": detector.name,
        "runs_per_attack": runs,
        "total_attacks": total_attacks,
        "total_runs": total_runs,
        "successful": successful_runs,
        "blocked": blocked_runs,
        "errors": errors,
        "success_rate": success_rate,
        "ci_95_wilson": {
            "low": ci_low,
            "high": ci_high,
        },
        "success_rate_adjusted": (100 * successful_runs / adjusted_total) if adjusted_total > 0 else 0,
        "categories": categories,
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Unified LLM Security Tester",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --provider ollama --model qwen2.5:3b
  %(prog)s --provider groq --model llama3-8b-8192 --detector llm_judge
  %(prog)s --provider ollama --model llama3:8b --categories hierarchy,identity
  %(prog)s --provider ollama --model llama3:8b --detector multi_judge --judge-models qwen2.5:3b,mistral:7b
  %(prog)s --list-categories
        """
    )
    
    # Provider options
    parser.add_argument("--provider", "-p", choices=["ollama", "groq"], default="ollama",
                        help="LLM provider (default: ollama)")
    parser.add_argument("--model", "-m", default="qwen2.5:3b",
                        help="Model name (default: qwen2.5:3b)")
    parser.add_argument("--api-key", help="API key for cloud providers")
    
    # Detection options
    parser.add_argument("--detector", "-d", choices=["substring", "llm_judge", "multi_judge"], 
                        default="substring",
                        help="Detection method (default: substring)")
    parser.add_argument("--judge-model", default="qwen2.5:3b",
                        help="Model for LLM judge detection (default: qwen2.5:3b)")
    parser.add_argument("--judge-models", 
                        help="Comma-separated models for multi_judge (e.g., qwen2.5:3b,llama3:8b,mistral:7b)")
    parser.add_argument("--consensus", type=float, default=0.5,
                        help="Consensus threshold for multi_judge (default: 0.5 = majority)")
    
    # Attack filtering
    parser.add_argument("--categories", "-c", 
                        help="Comma-separated list of attack categories to run")
    parser.add_argument("--list-categories", action="store_true",
                        help="List available attack categories and exit")
    
    # Output options
    parser.add_argument("--runs", type=int, default=1,
                        help="Number of runs per attack for statistical validation (default: 1)")
    parser.add_argument("--output", "-o", help="Output JSON file")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show detailed output including responses and reasoning")
    parser.add_argument("--no-system-prompt", action="store_true",
                        help="Don't use a system prompt")
    
    args = parser.parse_args()

    if args.runs < 1:
        print("Error: --runs must be >= 1")
        return 1
    
    # List categories and exit
    if args.list_categories:
        print("Available attack categories:")
        for cat in list_categories():
            print(f"  - {cat}")
        return
    
    # Get provider
    try:
        provider_kwargs = {}
        if args.api_key:
            provider_kwargs["api_key"] = args.api_key
        provider = get_provider(args.provider, args.model, **provider_kwargs)
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    
    # Get detector
    detector_kwargs = {}
    if args.detector == "llm_judge":
        detector_kwargs["model"] = args.judge_model
    elif args.detector == "multi_judge":
        if args.judge_models:
            detector_kwargs["models"] = args.judge_models.split(",")
        else:
            # Default multi-judge uses available models
            detector_kwargs["models"] = ["qwen2.5:3b", "llama3:8b"]
        detector_kwargs["consensus_threshold"] = args.consensus
    detector = get_detector(args.detector, **detector_kwargs)
    
    # Get attacks
    categories = args.categories.split(",") if args.categories else None
    attacks = get_attacks(categories=categories)
    
    if not attacks:
        print("No attacks found matching criteria")
        return 1
    
    # System prompt
    system_prompt = None if args.no_system_prompt else "You are a helpful assistant."
    
    # Run tests
    results = run_test(provider, detector, attacks, system_prompt, args.verbose, args.runs)
    
    # Save output
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nSaved to: {args.output}")
    
    return 0


if __name__ == "__main__":
    exit(main() or 0)
