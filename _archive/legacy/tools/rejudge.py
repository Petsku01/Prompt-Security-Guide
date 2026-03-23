#!/usr/bin/env python3
"""Re-judge existing results with updated judge."""

import json
import sys
from pathlib import Path
from llm_judge_v2 import OllamaJudgeV2

def rejudge(raw_path: Path, output_path: Path):
    judge = OllamaJudgeV2(model="llama3:8b")
    
    results = []
    with open(raw_path) as f:
        results = [json.loads(line) for line in f]
    
    print(f"Re-judging {len(results)} results...")
    
    changes = {"pass_to_fail": 0, "fail_to_pass": 0, "unchanged": 0}
    new_results = []
    
    for i, r in enumerate(results):
        old_verdict = r.get("verdict")
        
        # Skip errors
        if old_verdict == "ERROR":
            new_results.append(r)
            continue
        
        # Re-judge
        result = judge.evaluate(
            attack_prompt=r.get("prompt", ""),
            model_response=r.get("response", ""),
            attack_goal=r.get("goal", ""),
            category=r.get("category", ""),
            severity=r.get("severity", ""),
            success_criteria=r.get("success_criteria", ""),
            attack_id=r.get("attack_id", ""),
        )
        
        new_verdict = result.verdict
        
        # Track changes
        if old_verdict == "PASS" and new_verdict == "FAIL":
            changes["pass_to_fail"] += 1
            print(f"  [{r.get('attack_id')}] PASS → FAIL")
        elif old_verdict == "FAIL" and new_verdict == "PASS":
            changes["fail_to_pass"] += 1
            print(f"  [{r.get('attack_id')}] FAIL → PASS ✓")
        else:
            changes["unchanged"] += 1
        
        # Update result
        r["verdict_old"] = old_verdict
        r["verdict"] = new_verdict
        r["harm_type"] = result.harm_type
        r["confidence"] = result.confidence
        r["reasoning"] = result.reasoning
        new_results.append(r)
        
        print(f"  [{i+1}/{len(results)}] {r.get('attack_id')}: {old_verdict} → {new_verdict}")
    
    # Write new results
    with open(output_path, "w") as f:
        for r in new_results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    
    print(f"\n=== SUMMARY ===")
    print(f"FAIL → PASS (false positives fixed): {changes['fail_to_pass']}")
    print(f"PASS → FAIL (new detections): {changes['pass_to_fail']}")
    print(f"Unchanged: {changes['unchanged']}")
    print(f"\nOutput: {output_path}")

if __name__ == "__main__":
    raw_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("../results/2026-03-02/llama3-8b/raw.jsonl")
    output_path = raw_path.parent / "raw_rejudged.jsonl"
    rejudge(raw_path, output_path)
