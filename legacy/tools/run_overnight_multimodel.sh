#!/usr/bin/env bash
set -euo pipefail

# Overnight multi-model security benchmark (unattended)
# - Runs all attacks (tier 3, default catalog=76 attacks) per model
# - Uses llm_judge_v2 via unified_tester_v2.py --judge-mode llm_v2
# - Writes per-model raw + summary files under results/YYYY-MM-DD/<model>/

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS_DIR="$ROOT_DIR/tools"
DATE_TAG="$(date +%Y-%m-%d)"
STAMP="$(date +%Y%m%d-%H%M%S)"
LOG_DIR="$ROOT_DIR/results/$DATE_TAG/overnight_logs"

mkdir -p "$LOG_DIR"

# Override from env if needed
JUDGE_MODEL="${JUDGE_MODEL:-llama3:8b}"
BASE_URL="${BASE_URL:-http://localhost:11434}"
SEED="${SEED:-42}"
TEMPERATURE="${TEMPERATURE:-0.0}"
TIMEOUT="${TIMEOUT:-90}"
NUM_PREDICT="${NUM_PREDICT:-64}"

# Auto-detect text-generation models (exclude embeddings)
mapfile -t MODELS < <(
  ollama list | awk "NR>1{print \\$1}" | grep -Ev "embed|embedding" || true
)

if [[ ${#MODELS[@]} -eq 0 ]]; then
  echo "[FATAL] No Ollama generation models found."
  exit 1
fi

MASTER_LOG="$LOG_DIR/overnight_$STAMP.log"

echo "============================================================" | tee -a "$MASTER_LOG"
echo "Overnight multi-model run started: $(date -Is)" | tee -a "$MASTER_LOG"
echo "Root:        $ROOT_DIR" | tee -a "$MASTER_LOG"
echo "Judge model: $JUDGE_MODEL" | tee -a "$MASTER_LOG"
echo "Seed/temp:   $SEED / $TEMPERATURE" | tee -a "$MASTER_LOG"
echo "Models:      ${MODELS[*]}" | tee -a "$MASTER_LOG"
echo "Master log:  $MASTER_LOG" | tee -a "$MASTER_LOG"
echo "============================================================" | tee -a "$MASTER_LOG"

cd "$TOOLS_DIR"

for MODEL in "${MODELS[@]}"; do
  SAFE_MODEL="${MODEL//:/-}"
  MODEL_LOG="$LOG_DIR/${SAFE_MODEL}_$STAMP.log"

  echo "" | tee -a "$MASTER_LOG"
  echo ">>> [$MODEL] START $(date -Is)" | tee -a "$MASTER_LOG"

  if python3 -u unified_tester_v2.py \
      --catalog attack_catalog.json \
      --model "$MODEL" \
      --judge-mode llm_v2 \
      --judge-model "$JUDGE_MODEL" \
      --base-url "$BASE_URL" \
      --tier 3 \
      --temperature "$TEMPERATURE" \
      --seed "$SEED" \
      --num-predict "$NUM_PREDICT" \
      --timeout "$TIMEOUT" \
      --output-suffix "_overnight" \
      2>&1 | tee "$MODEL_LOG"; then
    echo ">>> [$MODEL] DONE  $(date -Is)" | tee -a "$MASTER_LOG"
  else
    echo ">>> [$MODEL] FAIL  $(date -Is)  (continuing)" | tee -a "$MASTER_LOG"
  fi

done

echo "" | tee -a "$MASTER_LOG"
echo "Overnight multi-model run finished: $(date -Is)" | tee -a "$MASTER_LOG"
echo "Logs: $LOG_DIR" | tee -a "$MASTER_LOG"
