#!/usr/bin/env python3
"""Generate readable HTML report from test results."""

import json
import sys
from pathlib import Path
from datetime import datetime

def generate_html(summary_path: Path, raw_path: Path) -> str:
    summary = json.loads(summary_path.read_text())
    
    # Load raw results
    results = []
    with open(raw_path) as f:
        for line in f:
            results.append(json.loads(line))
    
    fails = [r for r in results if r.get('verdict') == 'FAIL']
    passes = [r for r in results if r.get('verdict') == 'PASS']
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Security Test Report - {summary['model']}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #1a1a2e; color: #eee; }}
        h1 {{ color: #00d4ff; }}
        h2 {{ color: #ff6b6b; border-bottom: 1px solid #333; padding-bottom: 10px; }}
        h3 {{ color: #ffd93d; }}
        .summary {{ background: #16213e; padding: 20px; border-radius: 10px; margin: 20px 0; }}
        .stat {{ display: inline-block; margin: 10px 20px; text-align: center; }}
        .stat-value {{ font-size: 2em; font-weight: bold; }}
        .stat-label {{ color: #888; }}
        .good {{ color: #4ade80; }}
        .bad {{ color: #f87171; }}
        .warning {{ color: #fbbf24; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #333; }}
        th {{ background: #0f3460; }}
        tr:hover {{ background: #1f4068; }}
        .fail {{ background: #3d1f1f; }}
        .pass {{ background: #1f3d1f; }}
        .prompt {{ background: #222; padding: 10px; border-radius: 5px; white-space: pre-wrap; font-family: monospace; font-size: 0.85em; max-height: 200px; overflow-y: auto; }}
        .response {{ background: #1a1a2e; padding: 10px; border-left: 3px solid #ff6b6b; margin: 10px 0; white-space: pre-wrap; font-size: 0.9em; max-height: 300px; overflow-y: auto; }}
        .category-table td:nth-child(3) {{ font-weight: bold; }}
        details {{ margin: 10px 0; }}
        summary {{ cursor: pointer; padding: 10px; background: #16213e; border-radius: 5px; }}
        summary:hover {{ background: #1f4068; }}
    </style>
</head>
<body>
    <h1>🛡️ Security Test Report</h1>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <div class="summary">
        <h2>Model: {summary['model']}</h2>
        <div class="stat">
            <div class="stat-value {'bad' if summary['overall_asr'] > 0.3 else 'warning' if summary['overall_asr'] > 0.15 else 'good'}">{summary['overall_asr']*100:.1f}%</div>
            <div class="stat-label">Attack Success Rate</div>
        </div>
        <div class="stat">
            <div class="stat-value bad">{summary['fail']}</div>
            <div class="stat-label">Failed (Vulnerable)</div>
        </div>
        <div class="stat">
            <div class="stat-value good">{summary['pass']}</div>
            <div class="stat-label">Passed (Safe)</div>
        </div>
        <div class="stat">
            <div class="stat-value">{summary.get('errors', 0)}</div>
            <div class="stat-label">Errors</div>
        </div>
        <p><strong>Test duration:</strong> {summary['elapsed_seconds']/60:.1f} minutes</p>
        <p><strong>Model size:</strong> {summary['model_info'].get('parameter_size', 'unknown')}</p>
        <p><strong>Quantization:</strong> {summary['model_info'].get('quantization_level', 'unknown')}</p>
    </div>
    
    <h2>📊 Results by Category</h2>
    <table class="category-table">
        <tr><th>Category</th><th>Total</th><th>ASR</th><th>Visual</th></tr>
"""
    
    # Sort categories by ASR descending
    cats = sorted(summary['per_category'].items(), key=lambda x: x[1]['asr'], reverse=True)
    for cat, data in cats:
        asr = data['asr'] * 100
        bar_width = int(asr)
        color = '#f87171' if asr > 50 else '#fbbf24' if asr > 25 else '#4ade80'
        html += f"""        <tr>
            <td>{cat.replace('_', ' ').title()}</td>
            <td>{data['total']}</td>
            <td style="color: {color}">{asr:.1f}%</td>
            <td><div style="background: {color}; width: {bar_width}%; height: 20px; border-radius: 3px;"></div></td>
        </tr>
"""
    
    html += """    </table>
    
    <h2>❌ Failed Attacks (Vulnerabilities Found)</h2>
"""
    
    for r in fails:
        prompt_escaped = r.get('prompt', '').replace('<', '&lt;').replace('>', '&gt;')
        response_escaped = r.get('response', '')[:1000].replace('<', '&lt;').replace('>', '&gt;')
        html += f"""    <details>
        <summary class="fail">
            <strong>{r.get('attack_id')}</strong> - {r.get('category', '').replace('_', ' ').title()} 
            (Severity: {r.get('severity')}, Harm: {r.get('harm_type', 'unknown')})
        </summary>
        <div style="padding: 15px;">
            <p><strong>Goal:</strong> {r.get('goal', '')}</p>
            <h4>Prompt:</h4>
            <div class="prompt">{prompt_escaped}</div>
            <h4>Model Response:</h4>
            <div class="response">{response_escaped}{'...' if len(r.get('response', '')) > 1000 else ''}</div>
            <p><strong>Judge reasoning:</strong> {r.get('reasoning', '')}</p>
        </div>
    </details>
"""
    
    html += """
    <h2>✅ Passed Attacks (Model Resisted)</h2>
    <details>
        <summary>Show {len(passes)} passed tests</summary>
        <table>
            <tr><th>ID</th><th>Category</th><th>Goal</th></tr>
""".replace('{len(passes)}', str(len(passes)))
    
    for r in passes:
        html += f"""            <tr class="pass"><td>{r.get('attack_id')}</td><td>{r.get('category', '').replace('_', ' ')}</td><td>{r.get('goal', '')[:80]}</td></tr>
"""
    
    html += """        </table>
    </details>
</body>
</html>"""
    
    return html


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: generate_report.py <results_dir>")
        print("Example: generate_report.py ../results/2026-03-02/llama3-8b")
        sys.exit(1)
    
    results_dir = Path(sys.argv[1])
    summary_path = results_dir / "summary.json"
    raw_path = results_dir / "raw.jsonl"
    
    if not summary_path.exists():
        # Try with suffix
        summaries = list(results_dir.glob("summary*.json"))
        if summaries:
            summary_path = sorted(summaries)[-1]  # Latest
    
    if not raw_path.exists():
        raws = list(results_dir.glob("raw*.jsonl"))
        if raws:
            raw_path = sorted(raws)[-1]
    
    if not summary_path.exists() or not raw_path.exists():
        print(f"Could not find summary.json and raw.jsonl in {results_dir}")
        sys.exit(1)
    
    html = generate_html(summary_path, raw_path)
    
    output_path = results_dir / "report.html"
    output_path.write_text(html)
    print(f"Report generated: {output_path}")
