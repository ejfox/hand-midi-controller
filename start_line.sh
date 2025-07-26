#!/bin/bash

# Motion Line Controller startup script

echo "🎵 Starting Motion Line Controller..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "[!] No virtual environment found"
    echo "    Run ./setup.sh first to install dependencies"
    exit 1
fi

# Activate virtual environment and run motion line controller
source venv/bin/activate
python motion_line_controller.py "$@"