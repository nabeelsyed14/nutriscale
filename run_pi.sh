#!/bin/bash

# NutriScale Pi Run Script

# Ensure we are in the script's directory
cd "$(dirname "$0")"

# Activate venv
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "[-] Virtual environment not found. Run ./setup_pi.sh first."
    exit 1
fi

# Run Flask on 0.0.0.0 (accessible on LAN)
echo "[+] Starting NutriScale Server..."
./.venv/bin/python backend/app.py
