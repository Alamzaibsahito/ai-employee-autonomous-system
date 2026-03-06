#!/bin/bash
# ============================================================
# Process Tasks Startup Script for WSL/PM2
# ============================================================
# This script ensures proper virtual environment activation
# before running process_tasks.py under PM2 in WSL.
#
# Usage:
#   ./start_process_tasks.sh
# ============================================================

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate virtual environment if it exists
if [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
    echo "Virtual environment activated: $SCRIPT_DIR/venv"
elif [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
    source "$SCRIPT_DIR/.venv/bin/activate"
    echo "Virtual environment activated: $SCRIPT_DIR/.venv"
else
    echo "No virtual environment found, using system Python"
fi

# Ensure Python can find site modules
export PYTHONHOME=""
export PYTHONPATH=""

# Change to script directory
cd "$SCRIPT_DIR"

# Run process_tasks.py with the activated Python
exec python "$SCRIPT_DIR/process_tasks.py" "$@"
