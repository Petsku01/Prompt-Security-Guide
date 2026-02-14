#!/usr/bin/env python3
"""
Unified Security Tester

Single entry point for all LLM security testing.
Combines attacks from multiple modules with configurable detection.

Usage:
    python tester.py --provider ollama --model qwen2.5:3b
    python tester.py --provider groq --model llama3-8b-8192 --detector llm_judge
    python tester.py --provider ollama --model llama3:8b --categories hierarchy,identity
"""

import argparse
import json
from datetime import datetime
from dataclasses import asdict

from providers import get_provider
from detection import get_detector
from attacks import get_attacks, list_categories, Attack


def run_test(provider, detector, attacks: list, system_prompt: str = None, verbose: bool = False) -> dict:
    """Run attacks against a model and collect results"""
    
    results = []
    successful = 0
    categories = {}
    
    total = len(attacks)
    print(f"\nRunning {total} attacks against {provider.name}")
    print(f"Detector: {detector.name}")
    print("=" * 60)
    
    for i, attack in enumerate(attacks, 1):
        print(f"[{i}/{total}] {attack.id}: {attack.name}")
        
        # Call the model
        response = provider.call(attack.prompt, system_prompt)
        
        if response.error:
            print(f"         ERROR: {response.error}")
            result = {
                "id": attack.id,
                "name": attack.name,
                "category": attack.category,
                "success": False,
                "error": response.error,
                "time_ms": response.time_ms
            }
        else:
            # Detect success
            detection = detector.detect(
                response.text, 
                attack.indicators, 
                attack.goal
            )
            
            if detection.success:
                successful += 1
                print(f"         SUCCEEDED (confidence: {detection.confidence:.0%})")
                if verbose:
                    print(f"         Matched: {detection.matched_indicators}")
            else:
                print(f"         BLOCKED ({response.time_ms}ms)")
            
            result = {
                "id": attack.id,
                "name": attack.name,
                "category": attack.category,
                "success": detection.success,
                "confidence": detection.confidence,
                "matched_indicators": detection.matched_indicators,
                "response": response.text[:500] if verbose else response.text[:200],
                "time_ms": response.time_ms,
                "reasoning": detection.reasoning
            }
        
        # Track by category
        cat = attack.category
        if cat not in categories:
            categories[cat] = {"total": 0, "success": 0}
        categories[cat]["total"] += 1
        if result.get("success"):
            categories[cat]["success"] += 1
        
        results.append(result)
    
    # Summary
    print()
    print("=" * 60)
    success_rate = 100 * successful / total if total > 0 else 0
    print(f"RESULTS: {successful}/{total} succeeded ({success_rate:.1f}%)")
    print("=" * 60)
    
    print("\nBy Category:")
    for cat, stats in sorted(categories.items()):
        pct = 100 * stats["success"] / stats["total"] if stats["total"] > 0 else 0
        print(f"  {cat}: {stats['success']}/{stats['total']} ({pct:.0f}%)")
    
    if successful > 0:
        print("\nSuccessful Attacks:")
        for r in results:
            if r.get("success"):
                print(f"  [{r['id']}] {r['name']}")
    
    return {
        "timestamp": datetime.now().isoformat(),
        "provider": provider.name,
        "detector": detector.name,
        "total_attacks": total,
        "successful": successful,
        "success_rate": success_rate,
        "categories": categories,
        "results": results
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
    parser.add_argument("--detector", "-d", choices=["substring", "llm_judge"], default="substring",
                        help="Detection method (default: substring)")
    parser.add_argument("--judge-model", default="qwen2.5:3b",
                        help="Model for LLM judge detection (default: qwen2.5:3b)")
    
    # Attack filtering
    parser.add_argument("--categories", "-c", 
                        help="Comma-separated list of attack categories to run")
    parser.add_argument("--list-categories", action="store_true",
                        help="List available attack categories and exit")
    
    # Output options
    parser.add_argument("--output", "-o", help="Output JSON file")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show detailed output including responses")
    parser.add_argument("--no-system-prompt", action="store_true",
                        help="Don't use a system prompt")
    
    args = parser.parse_args()
    
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
    results = run_test(provider, detector, attacks, system_prompt, args.verbose)
    
    # Save output
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nSaved to: {args.output}")
    
    return 0


if __name__ == "__main__":
    exit(main() or 0)
