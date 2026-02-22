#!/bin/bash

# NutriScale Pi Setup Script
# Run this on your Raspberry Pi 5

# Exit on any error
set -e

echo "[+] Starting NutriScale Pi 5 Setup..."

# 1. Update System
echo "[+] Updating system packages..."
sudo apt-get update || (sleep 5 && sudo apt-get update)
sudo apt-get install -f -y

# 2. Install System Dependencies
echo "[+] Installing system dependencies (Pi 5 GPIO support)..."
sudo apt-get install -y libopenjp2-7 libtiff-dev python3-venv libcamera-apps rpicam-apps python3-lgpio swig liblgpio-dev

# Quick verify
if ! command -v swig &> /dev/null; then
    echo "[-] ERROR: swig failed to install. Please run 'sudo apt-get update && sudo apt-get install -y swig' manually."
    exit 1
fi

# 3. Create Python Virtual Environment (PEP 668 compliant)
echo "[+] Setting up Python Virtual Environment..."

# Check if .venv exists AND is valid (contains activate script)
if [ -d ".venv" ] && [ -f ".venv/bin/activate" ]; then
    echo "[.] Virtual environment looks good."
else
    echo "[!] Virtual environment missing or broken. Recreating..."
    rm -rf .venv
    python3 -m venv .venv
    echo "[+] Virtual environment created."
fi

# 4. Activate and Install Requirements
echo "[+] Installing Python dependencies..."
if source .venv/bin/activate; then
    pip install --upgrade pip setuptools wheel
    pip install -r requirements.txt
else
    echo "[-] FAILED to activate virtual environment. Is python3-venv installed?"
    exit 1
fi

# 5. Create .env if missing
if [ ! -f ".env" ]; then
    echo "[+] Creating default .env file..."
    echo "USE_REAL_HARDWARE=true" > .env
    echo "FLASK_ENV=production" >> .env
    echo "GEMINI_API_KEY=" >> .env
    echo "OLLAMA_HOST=http://localhost:11434" >> .env
    echo "[!] Please edit .env and add your GEMINI_API_KEY if needed."
fi

echo ">>> Setup Complete! Run ./run_pi.sh to start."
