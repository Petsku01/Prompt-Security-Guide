#!/usr/bin/env python3
"""
Overnight Rebuild Orchestrator

Automates the full rebuild cycle:
1. Research (Gemini + Web)
2. Design (Opus)
3. Build (Codex)
4. Review (Codex + Gemini)
5. Iterate

Uses OpenClaw sessions_spawn for sub-agents.
"""

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
STATUS_FILE = BASE_DIR / "STATUS.md"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Senior Engineer prompt (condensed for task injection)
SE_PROMPT_CORE = """
You are a senior software engineer. Key behaviors:
1. SURFACE ASSUMPTIONS before coding - list them explicitly
2. STOP ON CONFUSION - don't guess, ask
3. PUSH BACK on bad ideas with concrete alternatives
4. SIMPLICITY over cleverness - prefer boring obvious solutions
5. SURGICAL SCOPE - touch only what's asked
6. CLEAN UP dead code - but ask first

After changes, always provide:
CHANGES MADE:
- [file]: [what and why]

POTENTIAL CONCERNS:
- [risks to verify]
"""

def log(msg: str):
    """Log with timestamp."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")
    with open(LOG_DIR / "orchestrator.log", "a") as f:
        f.write(f"[{ts}] {msg}\n")

def update_status(phase: str, status: str, details: str = ""):
    """Update STATUS.md file."""
    content = f"""# Overnight Rebuild Status

**Last Updated:** {datetime.now().isoformat()}
**Current Phase:** {phase}
**Status:** {status}

## Progress

{details}

## Phases
- [ ] Phase 1: Research
- [ ] Phase 2: Design
- [ ] Phase 3: Build
- [ ] Phase 4: Review
- [ ] Phase 5: Iterate
"""
    STATUS_FILE.write_text(content)

def openclaw_spawn(task: str, agent: str = "codex", label: str = None, timeout: int = 600) -> dict:
    """
    Spawn a sub-agent via OpenClaw CLI.
    
    Uses: openclaw session spawn --task "..." --agent codex/gemini
    """
    cmd = [
        "openclaw", "session", "spawn",
        "--task", task,
        "--runtime", "acp",
        "--mode", "run",
        "--timeout", str(timeout)
    ]
    
    if agent == "codex":
        cmd.extend(["--agent", "codex"])
    elif agent == "gemini":
        cmd.extend(["--agent", "gemini"])
    # Default is main agent (Opus)
    
    if label:
        cmd.extend(["--label", label])
    
    log(f"Spawning {agent}: {task[:80]}...")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 60
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def web_search(query: str) -> str:
    """Perform web search via OpenClaw."""
    cmd = ["openclaw", "web", "search", "--query", query, "--count", "5"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.stdout
    except:
        return ""

def save_output(filename: str, content: str):
    """Save output to file."""
    path = BASE_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    log(f"Saved: {filename}")

# ============================================================================
# PHASE 1: RESEARCH
# ============================================================================

def phase1_research():
    """Research phase using Gemini + Web Search."""
    log("=" * 60)
    log("PHASE 1: RESEARCH")
    log("=" * 60)
    
    update_status("Research", "In Progress", "Gathering SOTA attack techniques...")
    
    # Web searches for latest techniques
    searches = [
        "LLM jailbreak techniques 2024 2025 2026",
        "prompt injection attacks latest research",
        "Policy Puppetry LLM attack",
        "Crescendo multi-turn jailbreak",
        "LLM safety bypass techniques SOTA",
        "AI red teaming methodologies"
    ]
    
    search_results = []
    for query in searches:
        log(f"Searching: {query}")
        results = web_search(query)
        search_results.append(f"## {query}\n\n{results}\n")
        time.sleep(2)  # Rate limiting
    
    # Save raw search results
    save_output("research/web_search_raw.md", "\n".join(search_results))
    
    # Gemini task: Analyze and synthesize
    gemini_task = f"""
{SE_PROMPT_CORE}

TASK: Analyze LLM security attack techniques and create a comprehensive catalog.

I've gathered web search results about LLM attacks. Synthesize this into a structured document.

WEB SEARCH RESULTS:
{chr(10).join(search_results[:3])}  # First 3 to fit context

Create a document with:
1. ATTACK CATEGORIES (with descriptions)
2. SPECIFIC TECHNIQUES (name, how it works, effectiveness)
3. DEFENSE BYPASSES (what safety measures they defeat)
4. RECOMMENDED TEST CASES (for each technique)

Output as Markdown. Be thorough but concise.
Focus on attacks that work in 2024-2026.
"""
    
    result = openclaw_spawn(gemini_task, agent="gemini", label="research-gemini", timeout=900)
    
    if result["success"]:
        save_output("research/SOTA_ATTACKS_2026.md", result["stdout"])
        log("Research phase complete")
        return True
    else:
        log(f"Research failed: {result.get('error', result.get('stderr', 'Unknown'))}")
        return False

# ============================================================================
# PHASE 2: DESIGN
# ============================================================================

def phase2_design():
    """Design phase using Opus."""
    log("=" * 60)
    log("PHASE 2: DESIGN")
    log("=" * 60)
    
    update_status("Design", "In Progress", "Designing architecture...")
    
    # Read research output
    research_file = BASE_DIR / "research/SOTA_ATTACKS_2026.md"
    research_content = research_file.read_text() if research_file.exists() else "Research not available"
    
    design_task = f"""
{SE_PROMPT_CORE}

TASK: Design the architecture for an LLM security testing tool.

RESEARCH INPUT:
{research_content[:4000]}

REQUIREMENTS:
1. Model fingerprinting system (identify unknown models)
2. Attack catalog (JSON-based, extensible)
3. Test runner (supports Ollama, OpenAI API, raw endpoints)
4. Results analyzer (safety scores, vulnerability reports)
5. Web GUI - MUST BE SIMPLE:
   - NO frameworks, NO complex state
   - Pure HTML/CSS/JS
   - Search box + model details + test results
   - Clean, minimal design
6. CLI for automation

CONSTRAINTS:
- Python 3.10+
- Minimal dependencies (requests, json, pathlib)
- Single-file components where possible
- Must work offline (except for API calls to target)

Output a detailed ARCHITECTURE.md with:
1. Component diagram (ASCII)
2. File structure
3. Data flow
4. Key interfaces
5. GUI wireframe (ASCII)
"""
    
    # Using main agent (Opus) for design
    result = openclaw_spawn(design_task, agent="main", label="design-opus", timeout=900)
    
    if result["success"]:
        save_output("design/ARCHITECTURE.md", result["stdout"])
        log("Design phase complete")
        return True
    else:
        log(f"Design failed: {result.get('error', 'Unknown')}")
        return False

# ============================================================================
# PHASE 3: BUILD
# ============================================================================

def phase3_build():
    """Build phase using Codex."""
    log("=" * 60)
    log("PHASE 3: BUILD")
    log("=" * 60)
    
    update_status("Build", "In Progress", "Implementing components...")
    
    # Read design
    design_file = BASE_DIR / "design/ARCHITECTURE.md"
    design_content = design_file.read_text() if design_file.exists() else "Design not available"
    
    # Read research for attack catalog
    research_file = BASE_DIR / "research/SOTA_ATTACKS_2026.md"
    research_content = research_file.read_text() if research_file.exists() else ""
    
    build_task = f"""
{SE_PROMPT_CORE}

TASK: Implement the LLM security testing tool according to the design.

ARCHITECTURE:
{design_content[:3000]}

ATTACK RESEARCH:
{research_content[:2000]}

IMPLEMENT THESE FILES:

1. `src/core/fingerprinter.py`
   - Probe unknown models
   - Match against signature database
   - Return model info + confidence

2. `src/core/attack_runner.py`
   - Load attacks from catalog
   - Execute against target API
   - Collect responses

3. `src/core/analyzer.py`
   - Analyze responses for compliance/refusal
   - Calculate safety scores
   - Generate reports

4. `src/attacks/catalog.json`
   - 30+ attacks organized by category
   - Each: id, name, category, prompt, severity

5. `src/web/index.html`
   - SINGLE FILE, no frameworks
   - Search models, view vulns, run tests
   - Clean dark theme
   - NO complexity

6. `src/cli.py`
   - `python cli.py --url URL --auto`
   - `python cli.py --list-attacks`

OUTPUT FORMAT:
For each file, output:
```
=== FILE: path/to/file.py ===
[content]
=== END FILE ===
```

Keep code SIMPLE. No over-engineering.
"""
    
    result = openclaw_spawn(build_task, agent="codex", label="build-codex", timeout=1800)
    
    if result["success"]:
        # Parse and save files
        save_output("build/codex_output.md", result["stdout"])
        parse_and_save_files(result["stdout"])
        log("Build phase complete")
        return True
    else:
        log(f"Build failed: {result.get('error', 'Unknown')}")
        return False

def parse_and_save_files(output: str):
    """Parse Codex output and save individual files."""
    import re
    
    pattern = r'=== FILE: (.+?) ===\n(.*?)\n=== END FILE ==='
    matches = re.findall(pattern, output, re.DOTALL)
    
    for filepath, content in matches:
        filepath = filepath.strip()
        save_output(f"src/{filepath}", content.strip())

# ============================================================================
# PHASE 4: REVIEW
# ============================================================================

def phase4_review():
    """Review phase - Codex and Gemini critique the implementation."""
    log("=" * 60)
    log("PHASE 4: REVIEW")
    log("=" * 60)
    
    update_status("Review", "In Progress", "Running critique cycles...")
    
    # Gather all built files
    src_dir = BASE_DIR / "src"
    code_content = []
    
    if src_dir.exists():
        for f in src_dir.rglob("*"):
            if f.is_file() and f.suffix in [".py", ".json", ".html"]:
                try:
                    code_content.append(f"=== {f.relative_to(src_dir)} ===\n{f.read_text()[:2000]}\n")
                except:
                    pass
    
    code_summary = "\n".join(code_content)[:8000]
    
    review_prompt = f"""
{SE_PROMPT_CORE}

TASK: Critical code review of LLM security testing tool.

CODE TO REVIEW:
{code_summary}

REVIEW CRITERIA:
1. CODE QUALITY
   - Is it simple or over-engineered?
   - Are there unnecessary abstractions?
   - Is the code readable?

2. SECURITY
   - Is the tool itself secure?
   - Can it be abused?
   - Are there injection risks?

3. COMPLETENESS
   - Are all attack categories covered?
   - Is fingerprinting robust?
   - Does the GUI work?

4. USABILITY
   - Is the CLI intuitive?
   - Is the GUI clean (no clutter)?
   - Is documentation sufficient?

OUTPUT FORMAT:
## Summary
[one paragraph overall assessment]

## Critical Issues (must fix)
- [issue]: [why it matters] → [suggested fix]

## Improvements (should fix)
- [issue]: [suggestion]

## Minor (nice to have)
- [item]

## What's Good
- [positive points]
"""
    
    # Codex review
    log("Running Codex review...")
    codex_result = openclaw_spawn(review_prompt, agent="codex", label="review-codex", timeout=600)
    if codex_result["success"]:
        save_output("review/CODEX_REVIEW.md", codex_result["stdout"])
    
    # Gemini review
    log("Running Gemini review...")
    gemini_result = openclaw_spawn(review_prompt, agent="gemini", label="review-gemini", timeout=600)
    if gemini_result["success"]:
        save_output("review/GEMINI_REVIEW.md", gemini_result["stdout"])
    
    log("Review phase complete")
    return True

# ============================================================================
# PHASE 5: ITERATE
# ============================================================================

def phase5_iterate():
    """Iterate based on review feedback."""
    log("=" * 60)
    log("PHASE 5: ITERATE")
    log("=" * 60)
    
    update_status("Iterate", "In Progress", "Applying fixes...")
    
    # Read reviews
    codex_review = (BASE_DIR / "review/CODEX_REVIEW.md").read_text() if (BASE_DIR / "review/CODEX_REVIEW.md").exists() else ""
    gemini_review = (BASE_DIR / "review/GEMINI_REVIEW.md").read_text() if (BASE_DIR / "review/GEMINI_REVIEW.md").exists() else ""
    
    # Extract critical issues
    iterate_task = f"""
{SE_PROMPT_CORE}

TASK: Fix critical issues from code review.

CODEX REVIEW:
{codex_review[:3000]}

GEMINI REVIEW:
{gemini_review[:3000]}

Focus ONLY on "Critical Issues (must fix)" from both reviews.
Ignore minor issues.

For each fix, output:
```
=== FIX: path/to/file.py ===
[complete fixed file content]
=== END FIX ===
```

If no critical issues, output: "NO CRITICAL ISSUES FOUND"
"""
    
    result = openclaw_spawn(iterate_task, agent="codex", label="iterate-codex", timeout=900)
    
    if result["success"]:
        save_output("iterate/fixes.md", result["stdout"])
        if "NO CRITICAL ISSUES" not in result["stdout"]:
            parse_and_save_fixes(result["stdout"])
        log("Iterate phase complete")
        return True
    else:
        log(f"Iterate failed: {result.get('error', 'Unknown')}")
        return False

def parse_and_save_fixes(output: str):
    """Parse and apply fixes."""
    import re
    
    pattern = r'=== FIX: (.+?) ===\n(.*?)\n=== END FIX ==='
    matches = re.findall(pattern, output, re.DOTALL)
    
    for filepath, content in matches:
        filepath = filepath.strip()
        save_output(f"src/{filepath}", content.strip())
        log(f"Applied fix: {filepath}")

# ============================================================================
# MAIN ORCHESTRATION
# ============================================================================

def generate_final_report():
    """Generate final report for Petsku."""
    log("Generating final report...")
    
    report = f"""# Overnight Rebuild Complete

**Finished:** {datetime.now().isoformat()}

## Summary

The LLM security testing suite has been rebuilt from scratch.

## What Was Done

### Phase 1: Research
- Searched for latest LLM attack techniques (2024-2026)
- Synthesized SOTA attacks with Gemini
- Output: `research/SOTA_ATTACKS_2026.md`

### Phase 2: Design
- Designed clean architecture
- Focused on simplicity (no frameworks)
- Output: `design/ARCHITECTURE.md`

### Phase 3: Build
- Implemented with Codex + Senior Engineer prompt
- Components: fingerprinter, attack runner, analyzer, GUI, CLI
- Output: `src/` directory

### Phase 4: Review
- Codex reviewed for code quality
- Gemini reviewed for completeness
- Outputs: `review/CODEX_REVIEW.md`, `review/GEMINI_REVIEW.md`

### Phase 5: Iterate
- Fixed critical issues from reviews
- Output: `iterate/fixes.md`

## Files Created

```
overnight-rebuild/
├── research/
│   ├── web_search_raw.md
│   └── SOTA_ATTACKS_2026.md
├── design/
│   └── ARCHITECTURE.md
├── src/
│   ├── core/
│   │   ├── fingerprinter.py
│   │   ├── attack_runner.py
│   │   └── analyzer.py
│   ├── attacks/
│   │   └── catalog.json
│   ├── web/
│   │   └── index.html
│   └── cli.py
├── review/
│   ├── CODEX_REVIEW.md
│   └── GEMINI_REVIEW.md
└── iterate/
    └── fixes.md
```

## Next Steps

1. Review the generated code
2. Test with real models
3. Adjust based on your feedback

---
*Generated by overnight orchestrator*
"""
    
    save_output("FINAL_REPORT.md", report)
    return report

def main():
    """Run the full overnight cycle."""
    log("=" * 60)
    log("OVERNIGHT REBUILD STARTING")
    log(f"Time: {datetime.now().isoformat()}")
    log("=" * 60)
    
    update_status("Starting", "Initializing", "Overnight rebuild cycle beginning...")
    
    phases = [
        ("Research", phase1_research),
        ("Design", phase2_design),
        ("Build", phase3_build),
        ("Review", phase4_review),
        ("Iterate", phase5_iterate),
    ]
    
    for phase_name, phase_func in phases:
        log(f"\n>>> Starting {phase_name} phase...")
        try:
            success = phase_func()
            if not success:
                log(f"!!! {phase_name} phase failed, continuing...")
        except Exception as e:
            log(f"!!! {phase_name} phase error: {e}")
        
        # Brief pause between phases
        time.sleep(10)
    
    # Generate final report
    report = generate_final_report()
    
    log("=" * 60)
    log("OVERNIGHT REBUILD COMPLETE")
    log("=" * 60)
    
    update_status("Complete", "Done", "All phases finished. Check FINAL_REPORT.md")
    
    return report

if __name__ == "__main__":
    main()
