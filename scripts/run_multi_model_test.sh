#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

MODELS=("llama3:8b" "mistral:7b" "qwen2.5:3b" "phi3:mini" "gemma2:2b")
CATALOG="datasets/obliteratus_attacks.json"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "═══════════════════════════════════════════════════════════"
echo "  MULTI-MODEL VULNERABILITY TEST - $TIMESTAMP"
echo "═══════════════════════════════════════════════════════════"
echo ""

for MODEL in "${MODELS[@]}"; do
    SAFE_NAME=$(echo $MODEL | tr ':' '_')
    echo "────────────────────────────────────────────────────────────"
    echo "Testing: $MODEL"
    echo "Started: $(date)"
    echo "────────────────────────────────────────────────────────────"
    
    python3 -m psg \
        --model "$MODEL" \
        --catalog "$CATALOG" \
        --base-url http://localhost:11434/v1 \
        --allow-insecure-http \
        --timeout 120 \
        --checkpoint "results/multitest_${SAFE_NAME}_${TIMESTAMP}.jsonl" \
        --json-report "results/multitest_${SAFE_NAME}_${TIMESTAMP}.json" \
        --text-report "results/multitest_${SAFE_NAME}_${TIMESTAMP}.txt"
    
    echo ""
done

echo "═══════════════════════════════════════════════════════════"
echo "  ALL TESTS COMPLETE - $(date)"
echo "═══════════════════════════════════════════════════════════"

# Generate summary
echo ""
echo "VULNERABILITY SUMMARY:"
echo "─────────────────────"
for MODEL in "${MODELS[@]}"; do
    SAFE_NAME=$(echo $MODEL | tr ':' '_')
    REPORT="results/multitest_${SAFE_NAME}_${TIMESTAMP}.txt"
    if [ -f "$REPORT" ]; then
        FLAGGED=$(grep "Flagged:" "$REPORT" | awk '{print $2}')
        TOTAL=$(grep "Total:" "$REPORT" | awk '{print $2}')
        echo "$MODEL: $FLAGGED/$TOTAL flagged"
    fi
done
