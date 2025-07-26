#!/bin/bash

# hand midi controller quick setup

echo ">>> hand midi controller setup"
echo ""

# check python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "[i] detected python: $python_version"

# check if python 3.12 exists
if command -v python3.12 &> /dev/null; then
    echo "[+] python 3.12 found"
    python_cmd="python3.12"
else
    echo "[!] python 3.12 not found - mediapipe needs 3.12 or lower"
    echo "    install with: brew install python@3.12"
    exit 1
fi

# create virtual environment
echo ""
echo "[+] creating virtual environment..."
$python_cmd -m venv venv

# activate and install
echo "[+] installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "[+] setup complete!"
echo ""
echo "to run:"
echo "  source venv/bin/activate"
echo "  python hand_midi_controller.py"
echo ""
echo "or just:"
echo "  ./run.sh"