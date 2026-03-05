#!/bin/bash
# Overnight Rebuild Launcher
# Runs the orchestrator in tmux for overnight execution

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SESSION_NAME="overnight-rebuild"
LOG_FILE="$SCRIPT_DIR/logs/overnight-$(date +%Y%m%d_%H%M%S).log"

mkdir -p "$SCRIPT_DIR/logs"

echo "=== Overnight Rebuild Launcher ==="
echo "Time: $(date)"
echo "Session: $SESSION_NAME"
echo "Log: $LOG_FILE"

# Kill existing session if running
tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true

# Start new tmux session
tmux new-session -d -s "$SESSION_NAME" \
    "cd $SCRIPT_DIR && python3 orchestrator.py 2>&1 | tee $LOG_FILE; echo 'Press Enter to close'; read"

echo ""
echo "✅ Overnight rebuild started in tmux session: $SESSION_NAME"
echo ""
echo "Commands:"
echo "  tmux attach -t $SESSION_NAME    # Watch progress"
echo "  tmux kill-session -t $SESSION_NAME  # Stop"
echo "  tail -f $LOG_FILE               # Follow log"
echo ""
echo "Expected completion: ~08:00"
