#!/bin/bash
# Daily Auto Vector Pipeline - runs discovery, generation, and testing in tmux
# Requires: Scrapling venv, Ollama running

set -e
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# TODO: Make these runtime-configurable instead of hardcoding local paths/names.
LOG_DIR="$PROJECT_ROOT/logs"
DATE=$(date +%Y%m%d)
SESSION_NAME="auto-pipeline-$DATE"

mkdir -p "$LOG_DIR"

echo "=== AUTO VECTOR PIPELINE - $(date) ===" >> "$LOG_DIR/pipeline_$DATE.log"

# Check daily marker
MARKER_FILE="$PROJECT_ROOT/psg/automation/.last_discovery"
TODAY=$(date +%Y-%m-%d)

if [ -f "$MARKER_FILE" ] && [ "$(cat "$MARKER_FILE")" = "$TODAY" ]; then
    echo "Already ran today, skipping." >> "$LOG_DIR/pipeline_$DATE.log"
    exit 0
fi

# Check Ollama
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "ERROR: Ollama not running" >> "$LOG_DIR/pipeline_$DATE.log"
    exit 1
fi

# Kill existing session if any
tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true

# Start pipeline in tmux
tmux new-session -d -s "$SESSION_NAME" "
    cd '$PROJECT_ROOT'
    # TODO: Make venv path configurable via env/config.
    source ~/.openclaw/workspace/tools/scrapling-venv/bin/activate
    export PYTHONUNBUFFERED=1
    echo 'Starting pipeline...'
    if python3 -m psg.automation --tmux 2>&1 | tee -a '$LOG_DIR/pipeline_$DATE.log'; then
        echo '$TODAY' > '$MARKER_FILE'
        echo 'Pipeline complete!'
    else
        echo 'Pipeline failed - marker not updated' | tee -a '$LOG_DIR/pipeline_$DATE.log'
        exit 1
    fi
"

echo "Pipeline started in tmux session: $SESSION_NAME"
echo "Monitor: tmux attach -t $SESSION_NAME"
echo "Logs: $LOG_DIR/pipeline_$DATE.log"
