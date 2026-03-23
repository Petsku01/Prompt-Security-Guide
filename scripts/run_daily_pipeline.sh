#!/bin/bash
# Daily Auto Vector Pipeline - runs discovery, generation, and testing in tmux
# Requires: Scrapling venv, Ollama running

set -e
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
DATE=$(date +%Y%m%d)
SESSION_NAME="auto-pipeline-$DATE"
PSG_SCRAPLING_VENV="${PSG_SCRAPLING_VENV:-$HOME/.openclaw/workspace/tools/scrapling-venv}"
PSG_OLLAMA_URL="${PSG_OLLAMA_URL:-http://localhost:11434}"
SCRAPLING_PYTHON="$PSG_SCRAPLING_VENV/bin/python"
SCRAPLING_ACTIVATE="$PSG_SCRAPLING_VENV/bin/activate"

mkdir -p "$LOG_DIR"

echo "=== AUTO VECTOR PIPELINE - $(date) ===" >> "$LOG_DIR/pipeline_$DATE.log"

fail_startup() {
    local msg="$1"
    echo "ERROR: $msg" | tee -a "$LOG_DIR/pipeline_$DATE.log" >&2
    exit 1
}

for cmd in tmux curl python3; do
    command -v "$cmd" >/dev/null 2>&1 || fail_startup "Missing dependency: $cmd"
done

[ -f "$SCRAPLING_ACTIVATE" ] || fail_startup "Scrapling venv activate script not found: $SCRAPLING_ACTIVATE"
[ -x "$SCRAPLING_PYTHON" ] || fail_startup "Scrapling Python not executable: $SCRAPLING_PYTHON"

if ! "$SCRAPLING_PYTHON" -c "import scrapling" >/dev/null 2>&1; then
    fail_startup "Scrapling import failed using $SCRAPLING_PYTHON"
fi

# Check daily marker
MARKER_FILE="$PROJECT_ROOT/psg/automation/.last_discovery"
TODAY=$(date +%Y-%m-%d)

if [ -f "$MARKER_FILE" ] && [ "$(cat "$MARKER_FILE")" = "$TODAY" ]; then
    echo "Already ran today, skipping." >> "$LOG_DIR/pipeline_$DATE.log"
    exit 0
fi

# Check Ollama
if ! curl -s "$PSG_OLLAMA_URL/api/tags" > /dev/null 2>&1; then
    fail_startup "Ollama not reachable at $PSG_OLLAMA_URL"
fi

# Kill existing session if any
tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true

# Start pipeline in tmux
tmux new-session -d -s "$SESSION_NAME" "
    cd '$PROJECT_ROOT'
    export PSG_SCRAPLING_VENV='$PSG_SCRAPLING_VENV'
    export PSG_OLLAMA_URL='$PSG_OLLAMA_URL'
    source '$SCRAPLING_ACTIVATE'
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
