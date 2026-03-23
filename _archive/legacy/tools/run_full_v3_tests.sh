#!/bin/bash
# Full V3 Statistical Tests - 5 runs, multi-judge
# Estimated time: 4-8 hours total

cd /home/ette/.openclaw/workspace/prompt-security-guide/tools
CATEGORIES="hierarchy,identity,classic,emotional,jailbreak,meta"
JUDGES="qwen2.5:3b,llama3:8b"
RUNS=5
OUTDIR="../results/v3-stats"

mkdir -p "$OUTDIR"

echo "=============================================="
echo "V3 STATISTICAL TESTS - $(date)"
echo "5 runs per attack, multi-judge consensus"
echo "=============================================="

for MODEL in qwen2.5:3b qwen2.5:1.5b llama3:8b mistral:7b; do
    SAFE_NAME=$(echo $MODEL | tr ':' '-')
    OUTFILE="$OUTDIR/${SAFE_NAME}-v3-$(date +%Y%m%d).json"
    LOGFILE="$OUTDIR/${SAFE_NAME}-v3-$(date +%Y%m%d).log"
    
    echo ""
    echo ">>> Starting $MODEL at $(date)"
    echo ">>> Output: $OUTFILE"
    echo ""
    
    python3 -u tester.py \
        --provider ollama \
        --model "$MODEL" \
        --runs "$RUNS" \
        --detector multi_judge \
        --judge-models "$JUDGES" \
        --categories "$CATEGORIES" \
        --output "$OUTFILE" \
        --verbose 2>&1 | tee "$LOGFILE"
    
    echo ""
    echo ">>> Finished $MODEL at $(date)"
    echo "=============================================="
done

echo ""
echo "ALL TESTS COMPLETE - $(date)"
echo "Results in: $OUTDIR"
