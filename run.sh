#!/bin/bash
set -e
cd "$(dirname "$0")"

# Create venv if missing
if [ ! -f ".venv/bin/python" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Install / update dependencies
echo "Installing dependencies..."
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

# Create needed folders
mkdir -p tmp/uploads tmp/outputs

echo ""
echo "Starting app at http://localhost:8080"
echo "Press Ctrl+C to stop."
echo ""

PORT=8080 .venv/bin/python app.py
