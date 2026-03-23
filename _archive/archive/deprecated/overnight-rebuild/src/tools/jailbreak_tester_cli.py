#!/usr/bin/env python3
"""
Jailbreak Tester v4.0 - Unified CLI
===================================

ASSUMPTIONS:
1. All component modules are in same directory
2. Ollama available at localhost:11434
3. Research library exists in processed/

USAGE:
    ./jailbreak_tester_cli.py test llama3:8b [--thorough] [--technique=X] [--count=N]
    ./jailbreak_tester_cli.py compare llama3:8b mistral:7b
    ./jailbreak_tester_cli.py report results.json

Author: Kuu (SE methodology)
Date: 2026-03-04
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
import logging

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent))

from smart_selector import select_attacks, detect_model_family
from attack_runner import run_attacks, ensure_ollama_running, check_model_available
from report_generator import generate, analyze_results
from llm_judge import judge

# ============================================================
# CONFIGURATION
# ============================================================

RESULTS_DIR = Path(__file__).parent.parent / "results"
CHECKPOINT_DIR = Path(__file__).parent.parent / "checkpoints"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================
# COMMANDS
# ============================================================

def cmd_test(args):
    """Run security test on a model."""
    model = args.model
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║           JAILBREAK TESTER v4.0                              ║
╠══════════════════════════════════════════════════════════════╣
║  Model:     {model:<48} ║
║  Mode:      {'Thorough' if args.thorough else 'Standard':<48} ║
║  Technique: {args.technique or 'All':<48} ║
║  Max Count: {args.count:<48} ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    # Check Ollama
    print("Checking Ollama...")
    if not ensure_ollama_running():
        print("❌ Error: Ollama not available")
        return 1
    print("✓ Ollama running")
    
    # Check model
    print(f"Checking model {model}...")
    if not check_model_available(model):
        print(f"❌ Error: Model {model} not available")
        print("Available models: ollama list")
        return 1
    print(f"✓ Model {model} available")
    
    # Detect family
    family = detect_model_family(model)
    print(f"✓ Detected family: {family}")
    
    # Select attacks
    print(f"\nSelecting attacks...")
    attacks = select_attacks(
        model_name=model,
        technique=args.technique,
        max_count=args.count,
        min_sophistication=args.min_soph,
        thorough=args.thorough
    )
    
    if not attacks:
        print("❌ No attacks selected. Check if processed/ has data.")
        return 1
    
    print(f"✓ Selected {len(attacks)} attacks")
    
    # Create directories
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    checkpoint_file = CHECKPOINT_DIR / f"checkpoint_{model.replace(':', '_')}_{timestamp}.json"
    
    # Run attacks
    print(f"\n{'='*60}")
    print("RUNNING ATTACKS")
    print(f"{'='*60}\n")
    
    def progress(current, total):
        pct = current / total * 100
        bar = '█' * int(pct / 5) + '░' * (20 - int(pct / 5))
        print(f"\r[{bar}] {current}/{total} ({pct:.0f}%)", end='', flush=True)
    
    results = run_attacks(
        model=model,
        attacks=attacks,
        checkpoint_file=checkpoint_file,
        progress_callback=progress
    )
    
    print("\n")
    
    if not results:
        print("❌ No results collected")
        return 1
    
    # Generate report
    print("Generating report...")
    results_dicts = [
        {
            'attack_id': r.attack_id,
            'prompt': r.prompt,
            'technique': r.technique,
            'response': r.response,
            'verdict': r.verdict,
            'confidence': r.confidence,
            'judge_method': r.judge_method,
            'response_time_ms': r.response_time_ms,
            'timestamp': r.timestamp,
            'error': r.error
        }
        for r in results
    ]
    
    report = generate(model, results_dicts, RESULTS_DIR)
    
    # Print summary
    summary = report.summary
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                      TEST COMPLETE                           ║
╠══════════════════════════════════════════════════════════════╣
║  Model:            {model:<40} ║
║  Attacks Run:      {summary.get('total_attacks', 0):<40} ║
║  Safety Score:     {str(summary.get('safety_score', 0)) + '%':<40} ║
║  Vulnerability:    {str(summary.get('vulnerability_score', 0)) + '%':<40} ║
╠══════════════════════════════════════════════════════════════╣
║  Verdicts:                                                   ║
║    ✅ SAFE:      {summary.get('verdicts', {}).get('SAFE', 0):<43} ║
║    ❌ UNSAFE:    {summary.get('verdicts', {}).get('UNSAFE', 0):<43} ║
║    ❓ AMBIGUOUS: {summary.get('verdicts', {}).get('AMBIGUOUS', 0):<43} ║
╠══════════════════════════════════════════════════════════════╣
║  Reports:                                                    ║
║    Markdown: {str(report.markdown_path):<47} ║
║    JSON:     {str(report.json_path):<47} ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    return 0


def cmd_compare(args):
    """Compare two models."""
    models = [args.model1, args.model2]
    
    print(f"\nComparing: {models[0]} vs {models[1]}\n")
    
    results = {}
    for model in models:
        print(f"Testing {model}...")
        
        # Quick test with fewer attacks
        attacks = select_attacks(model, max_count=20, min_sophistication=4)
        if not attacks:
            print(f"  No attacks for {model}")
            continue
        
        checkpoint = CHECKPOINT_DIR / f"compare_{model.replace(':', '_')}.json"
        model_results = run_attacks(model, attacks, checkpoint)
        
        if model_results:
            results_dicts = [
                {'verdict': r.verdict, 'technique': r.technique}
                for r in model_results
            ]
            analysis = analyze_results(results_dicts)
            results[model] = analysis
    
    # Print comparison
    print(f"\n{'='*60}")
    print("COMPARISON RESULTS")
    print(f"{'='*60}\n")
    
    print(f"{'Metric':<25} {models[0]:<15} {models[1]:<15}")
    print("-" * 55)
    
    for model in models:
        if model in results:
            print(f"{'Safety Score':<25} {results[model].get('safety_score', '?')}%")
    
    return 0


def cmd_report(args):
    """Generate report from existing results."""
    results_file = Path(args.results_file)
    
    if not results_file.exists():
        print(f"❌ File not found: {results_file}")
        return 1
    
    with open(results_file) as f:
        data = json.load(f)
    
    model = data.get('model', 'unknown')
    results = data.get('results', [])
    
    report = generate(model, results, RESULTS_DIR)
    print(f"✓ Report generated: {report.markdown_path}")
    
    return 0


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='Jailbreak Tester v4.0 - LLM Security Testing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s test llama3:8b
  %(prog)s test llama3:8b --thorough --count=100
  %(prog)s test mistral:7b --technique=roleplay
  %(prog)s compare llama3:8b mistral:7b
  %(prog)s report results/report_llama3_8b.json
"""
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Test a model')
    test_parser.add_argument('model', help='Model name (e.g., llama3:8b)')
    test_parser.add_argument('--thorough', action='store_true', help='Thorough testing mode')
    test_parser.add_argument('--technique', help='Filter by technique')
    test_parser.add_argument('--count', type=int, default=50, help='Max attacks (default: 50)')
    test_parser.add_argument('--min-soph', type=int, default=3, help='Min sophistication (default: 3)')
    
    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare two models')
    compare_parser.add_argument('model1', help='First model')
    compare_parser.add_argument('model2', help='Second model')
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Generate report from results')
    report_parser.add_argument('results_file', help='Results JSON file')
    
    args = parser.parse_args()
    
    if args.command == 'test':
        sys.exit(cmd_test(args))
    elif args.command == 'compare':
        sys.exit(cmd_compare(args))
    elif args.command == 'report':
        sys.exit(cmd_report(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
