#!/bin/bash

# quick run script

if [ ! -d "venv" ]; then
    echo "[!] no virtual environment found"
    echo "    run ./setup.sh first"
    exit 1
fi

source venv/bin/activate
python hand_midi_controller_final.py "$@"