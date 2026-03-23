#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

CATALOG="datasets/categories_combined.json"
DATE=$(date +%Y%m%d)
COMMON_ARGS="--catalog $CATALOG --timeout 240 --max-tokens 512 --allow-insecure-http"

# Qwen already running, wait for checkpoint to reach 120
echo "=== Waiting for qwen2.5:3b to finish ==="
while [ $(wc -l < results/checkpoint.jsonl 2>/dev/null || echo 0) -lt 120 ]; do
    sleep 30
    echo "Progress: $(wc -l < results/checkpoint.jsonl)/120"
done
echo "=== qwen2.5:3b DONE ==="

# Phi3
echo ""
echo "=== Starting phi3:mini ==="
rm -f results/checkpoint.jsonl
python3 -m psg --model phi3:mini \
    $COMMON_ARGS \
    --json-report results/phi3-mini-${DATE}.json \
    --text-report results/phi3-mini-${DATE}.txt
echo "=== phi3:mini DONE ==="

# Gemma2
echo ""
echo "=== Starting gemma2:2b ==="
rm -f results/checkpoint.jsonl
python3 -m psg --model gemma2:2b \
    $COMMON_ARGS \
    --json-report results/gemma2-2b-${DATE}.json \
    --text-report results/gemma2-2b-${DATE}.txt
echo "=== gemma2:2b DONE ==="

echo ""
echo "========================================"
echo "ALL TESTS COMPLETE"
echo "========================================"
