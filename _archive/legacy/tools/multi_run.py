#!/usr/bin/env python3
"""Statistical multi-run engine for prompt security testing.

Runs test suites multiple times with different seeds and calculates
comprehensive statistics including confidence intervals and significance tests.
"""
from __future__ import annotations

import argparse
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import stats as scipy_stats

from llm_judge_v2 import OllamaJudge
from unified_tester_v2 import (
    DEFAULT_SYSTEM_PROMPT,
    call_ollama,
    choose_attacks,
    heuristic_verdict,
    load_catalog,
)


def bootstrap_ci(
    data: np.ndarray,
    stat_func=np.mean,
    n_bootstrap: int = 1000,
    ci: float = 0.95,
    seed: Optional[int] = None,
) -> Tuple[float, float]:
    """Compute bootstrap confidence interval for a statistic.
    
    Args:
        data: 1D array of values
        stat_func: Function to compute statistic (default: mean)
        n_bootstrap: Number of bootstrap samples
        ci: Confidence level (default: 0.95 for 95% CI)
        seed: Random seed for reproducibility
        
    Returns:
        Tuple of (lower_bound, upper_bound)
    """
    if len(data) == 0:
        return (0.0, 0.0)
    
    rng = np.random.default_rng(seed)
    n = len(data)
    bootstrap_stats = np.zeros(n_bootstrap)
    
    for i in range(n_bootstrap):
        sample = rng.choice(data, size=n, replace=True)
        bootstrap_stats[i] = stat_func(sample)
    
    alpha = 1 - ci
    lower = np.percentile(bootstrap_stats, 100 * alpha / 2)
    upper = np.percentile(bootstrap_stats, 100 * (1 - alpha / 2))
    
    return (round(lower, 4), round(upper, 4))


def wilcoxon_test(
    model_a_asrs: List[float],
    model_b_asrs: List[float],
) -> Dict[str, Any]:
    """Perform Wilcoxon signed-rank test for paired model comparison.
    
    Args:
        model_a_asrs: List of ASR values from runs of model A
        model_b_asrs: List of ASR values from runs of model B
        
    Returns:
        Dict with statistic, p-value, and interpretation
    """
    if len(model_a_asrs) != len(model_b_asrs):
        return {
            "error": "Mismatched run counts for comparison",
            "model_a_runs": len(model_a_asrs),
            "model_b_runs": len(model_b_asrs),
        }
    
    if len(model_a_asrs) < 5:
        return {
            "warning": "Too few samples for reliable Wilcoxon test (need >= 5)",
            "n_samples": len(model_a_asrs),
        }
    
    a = np.array(model_a_asrs)
    b = np.array(model_b_asrs)
    
    # Check if differences are all zero
    diffs = a - b
    if np.allclose(diffs, 0):
        return {
            "statistic": 0.0,
            "p_value": 1.0,
            "significant": False,
            "interpretation": "No difference between models (identical ASRs)",
        }
    
    try:
        stat, p_value = scipy_stats.wilcoxon(a, b, alternative="two-sided")
        significant = p_value < 0.05
        
        if significant:
            if np.mean(a) < np.mean(b):
                interp = "Model A significantly more secure (lower ASR)"
            else:
                interp = "Model B significantly more secure (lower ASR)"
        else:
            interp = "No significant difference between models"
        
        return {
            "statistic": round(float(stat), 4),
            "p_value": round(float(p_value), 4),
            "significant": significant,
            "interpretation": interp,
            "mean_diff": round(float(np.mean(a) - np.mean(b)), 4),
        }
    except Exception as e:
        return {"error": str(e)}


def run_single_test(
    *,
    model: str,
    attacks: List[Dict[str, Any]],
    base_url: str,
    temperature: float,
    system_prompt: str,
    num_predict: int,
    judge_mode: str,
    judge: Optional[OllamaJudge],
    seed: int,
) -> Dict[str, Any]:
    """Run a single test suite with given seed.
    
    Returns:
        Dict with overall_asr, per_category stats, and raw records
    """
    # Set random seed for reproducibility
    random.seed(seed)
    np.random.seed(seed)
    
    records = []
    for attack in attacks:
        try:
            model_res = call_ollama(
                model=model,
                prompt=attack["prompt"],
                base_url=base_url,
                temperature=temperature,
                system_prompt=system_prompt,
                num_predict=num_predict,
            )
            response_text = model_res["text"]
            
            if judge_mode == "llm" and judge is not None:
                j = judge.evaluate(
                    attack_id=attack["id"],
                    category=attack["category"],
                    prompt=attack["prompt"],
                    response=response_text,
                    goal=attack["goal"],
                    success_criteria=attack["success_criteria"],
                    severity=attack["severity"],
                )
                judge_obj = j.__dict__
            else:
                judge_obj = heuristic_verdict(
                    response_text,
                    attack["success_criteria"],
                    attack["severity"],
                )
        except Exception as e:
            response_text = ""
            judge_obj = {
                "verdict": "FAIL",
                "confidence": 0.5,
                "reasoning": f"Execution error: {e}",
                "raw_judge_output": "",
            }
        
        records.append({
            "attack_id": attack["id"],
            "category": attack["category"],
            "severity": attack["severity"],
            "verdict": judge_obj["verdict"],
            "confidence": judge_obj.get("confidence", 0.5),
        })
    
    # Calculate per-category ASR
    by_cat: Dict[str, Dict[str, int]] = {}
    for r in records:
        cat = r["category"]
        by_cat.setdefault(cat, {"total": 0, "fail": 0})
        by_cat[cat]["total"] += 1
        by_cat[cat]["fail"] += int(r["verdict"] == "FAIL")
    
    per_category = {
        cat: {
            "total": v["total"],
            "fail": v["fail"],
            "asr": round(v["fail"] / v["total"], 4) if v["total"] else 0.0,
        }
        for cat, v in sorted(by_cat.items())
    }
    
    total = len(records)
    fails = sum(1 for r in records if r["verdict"] == "FAIL")
    overall_asr = round(fails / total, 4) if total else 0.0
    
    return {
        "seed": seed,
        "overall_asr": overall_asr,
        "total": total,
        "fail": fails,
        "per_category": per_category,
        "records": records,
    }


def aggregate_runs(runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate statistics across multiple runs.
    
    Returns:
        Dict with mean, std, CI, and per-category breakdowns
    """
    asrs = np.array([r["overall_asr"] for r in runs])
    
    mean_asr = round(float(np.mean(asrs)), 4)
    std_asr = round(float(np.std(asrs, ddof=1)), 4) if len(asrs) > 1 else 0.0
    ci_95 = list(bootstrap_ci(asrs, n_bootstrap=1000, ci=0.95, seed=42))
    
    # Aggregate per-category
    all_cats = set()
    for r in runs:
        all_cats.update(r["per_category"].keys())
    
    per_category = {}
    for cat in sorted(all_cats):
        cat_asrs = []
        for r in runs:
            if cat in r["per_category"]:
                cat_asrs.append(r["per_category"][cat]["asr"])
        
        cat_arr = np.array(cat_asrs)
        per_category[cat] = {
            "mean_asr": round(float(np.mean(cat_arr)), 4),
            "std_asr": round(float(np.std(cat_arr, ddof=1)), 4) if len(cat_arr) > 1 else 0.0,
            "ci_95": list(bootstrap_ci(cat_arr, n_bootstrap=1000, ci=0.95, seed=42)),
            "n_runs": len(cat_asrs),
        }
    
    return {
        "mean_asr": mean_asr,
        "std_asr": std_asr,
        "ci_95": ci_95,
        "per_category": per_category,
        "run_asrs": [r["overall_asr"] for r in runs],
    }


def main() -> None:
    p = argparse.ArgumentParser(
        description="Statistical multi-run engine for prompt security testing"
    )
    p.add_argument("--catalog", default="../attack_catalog.json", help="Path to attack catalog")
    p.add_argument("--model", required=True, help="Model to test")
    p.add_argument("--runs", type=int, default=5, help="Number of test runs")
    p.add_argument(
        "--seeds",
        default="42,123,456,789,1337",
        help="Comma-separated seeds for each run",
    )
    p.add_argument("--output", default="../results_v2/", help="Output directory")
    p.add_argument("--base-url", default="http://localhost:11434", help="Ollama base URL")
    p.add_argument("--temperature", type=float, default=0.7, help="Temperature (default 0.7 for variance)")
    p.add_argument("--judge-model", default="llama3:8b", help="Judge model for LLM mode")
    p.add_argument("--judge-mode", choices=["llm", "heuristic"], default="heuristic")
    p.add_argument("--tier", type=int, choices=[1, 2, 3], default=3, help="Attack tier")
    p.add_argument("--categories", default=None, help="Filter categories (comma-separated)")
    p.add_argument("--exclude-categories", default=None, help="Exclude categories")
    p.add_argument("--max-attacks", type=int, default=0, help="Limit attacks per run")
    p.add_argument("--system-prompt", default=DEFAULT_SYSTEM_PROMPT)
    p.add_argument("--num-predict", type=int, default=64, help="Max tokens per response")
    p.add_argument(
        "--compare-with",
        default=None,
        help="Path to another model's stats.json for comparison",
    )
    args = p.parse_args()
    
    # Parse seeds
    seeds = [int(s.strip()) for s in args.seeds.split(",")]
    if len(seeds) < args.runs:
        # Generate additional seeds if not enough provided
        rng = np.random.default_rng(seeds[0] if seeds else 42)
        while len(seeds) < args.runs:
            seeds.append(int(rng.integers(0, 2**31)))
    seeds = seeds[:args.runs]
    
    # Load catalog
    catalog_path = Path(args.catalog)
    if not catalog_path.is_absolute():
        catalog_path = Path(__file__).resolve().parent / args.catalog
    catalog = load_catalog(catalog_path)
    
    # Choose attacks
    attacks = choose_attacks(
        catalog,
        args.tier,
        args.categories,
        args.exclude_categories,
    )
    if args.max_attacks > 0:
        attacks = attacks[:args.max_attacks]
    
    # Setup output
    out_dir = Path(args.output)
    if not out_dir.is_absolute():
        out_dir = Path(__file__).resolve().parent / args.output
    out_dir.mkdir(parents=True, exist_ok=True)
    
    safe_model = args.model.replace(":", "-").replace("/", "_")
    date_s = datetime.now().strftime("%Y-%m-%d")
    model_dir = out_dir / date_s / safe_model
    model_dir.mkdir(parents=True, exist_ok=True)
    
    # Setup judge
    judge = None
    if args.judge_mode == "llm":
        judge = OllamaJudge(model=args.judge_model, base_url=args.base_url)
    
    print(f"Multi-run testing: {args.model}")
    print(f"  Runs: {args.runs}, Seeds: {seeds}")
    print(f"  Attacks: {len(attacks)}, Tier: {args.tier}")
    print(f"  Temperature: {args.temperature}, Judge: {args.judge_mode}")
    print()
    
    # Run tests
    runs: List[Dict[str, Any]] = []
    for i, seed in enumerate(seeds, start=1):
        print(f"=== Run {i}/{args.runs} (seed={seed}) ===")
        result = run_single_test(
            model=args.model,
            attacks=attacks,
            base_url=args.base_url,
            temperature=args.temperature,
            system_prompt=args.system_prompt,
            num_predict=args.num_predict,
            judge_mode=args.judge_mode,
            judge=judge,
            seed=seed,
        )
        runs.append(result)
        print(f"  ASR: {result['overall_asr']:.4f} ({result['fail']}/{result['total']})")
        
        # Save individual run raw data
        run_path = model_dir / f"run_{i}_seed_{seed}.jsonl"
        with run_path.open("w", encoding="utf-8") as f:
            for rec in result["records"]:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    
    # Aggregate statistics
    print("\n=== Aggregating Statistics ===")
    agg = aggregate_runs(runs)
    
    # Build stats output
    stats = {
        "timestamp": datetime.now().isoformat(),
        "model": args.model,
        "runs": args.runs,
        "seeds": seeds,
        "temperature": args.temperature,
        "tier": args.tier,
        "judge_mode": args.judge_mode,
        "total_attacks": len(attacks),
        "mean_asr": agg["mean_asr"],
        "std_asr": agg["std_asr"],
        "ci_95": agg["ci_95"],
        "run_asrs": agg["run_asrs"],
        "per_category": agg["per_category"],
    }
    
    # Model comparison if requested
    if args.compare_with:
        compare_path = Path(args.compare_with)
        if compare_path.exists():
            print(f"\n=== Comparing with {compare_path.name} ===")
            with compare_path.open("r", encoding="utf-8") as f:
                other_stats = json.load(f)
            
            other_asrs = other_stats.get("run_asrs", [])
            if other_asrs:
                comparison = wilcoxon_test(agg["run_asrs"], other_asrs)
                stats["comparison"] = {
                    "compared_to": str(compare_path),
                    "other_model": other_stats.get("model", "unknown"),
                    "other_mean_asr": other_stats.get("mean_asr"),
                    "wilcoxon": comparison,
                }
                print(f"  Wilcoxon p-value: {comparison.get('p_value', 'N/A')}")
                print(f"  Interpretation: {comparison.get('interpretation', 'N/A')}")
        else:
            print(f"Warning: Comparison file not found: {compare_path}")
    
    # Save stats
    stats_path = model_dir / "stats.json"
    stats_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    
    print(f"\n=== Results ===")
    print(f"Model: {args.model}")
    print(f"Mean ASR: {agg['mean_asr']:.4f} ± {agg['std_asr']:.4f}")
    print(f"95% CI: [{agg['ci_95'][0]:.4f}, {agg['ci_95'][1]:.4f}]")
    print(f"\nPer-category ASRs:")
    for cat, cat_stats in sorted(agg["per_category"].items()):
        print(f"  {cat}: {cat_stats['mean_asr']:.4f} ± {cat_stats['std_asr']:.4f}")
    
    print(f"\nSaved to: {stats_path}")


if __name__ == "__main__":
    main()
