#!/bin/bash
cd /home/ette/.openclaw/workspace/prompt-security-guide
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MODELS="llama3:8b mistral:7b qwen2.5:3b phi3:mini gemma2:2b"

echo "═══════════════════════════════════════════════════════════"
echo "  NEW VECTORS TEST - $TIMESTAMP"
echo "═══════════════════════════════════════════════════════════"

for MODEL in $MODELS; do
    MODEL_SAFE=$(echo $MODEL | tr ':' '_')
    echo ""
    echo "────────────────────────────────────────────────────────────"
    echo "Testing: $MODEL"
    echo "Started: $(date)"
    echo "────────────────────────────────────────────────────────────"
    
    python3 -m jailbreak_tester \
        --catalog datasets/new_vectors_2026-03-06.json \
        --model "$MODEL" \
        --allow-insecure-http \
        --timeout 120 \
        --checkpoint "results/newvec_${MODEL_SAFE}_${TIMESTAMP}.jsonl" \
        --json-report "results/newvec_${MODEL_SAFE}_${TIMESTAMP}.json" \
        --text-report "results/newvec_${MODEL_SAFE}_${TIMESTAMP}.txt"
done

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ALL TESTS COMPLETE - $(date)"
echo "═══════════════════════════════════════════════════════════"
