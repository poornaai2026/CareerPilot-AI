#!/usr/bin/env bash
set -e

echo "======================================================================"
echo "          ⚡ CAREERPILOT AI — AUTOMATED INSTALLER & SETUP"
echo "======================================================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed!"
    echo "Please install Python 3.10+ using your package manager or from python.org"
    exit 1
fi

echo "[1/4] Setting up Python virtual environment (.venv)..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

echo "[2/4] Installing dependencies from requirements.txt..."
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

echo "[3/4] Installing Playwright Chromium browser binary..."
.venv/bin/playwright install chromium

echo "[4/4] Checking configuration (.env)..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Created .env from .env.example!"
fi

echo ""
echo "======================================================================"
echo "          ✅ INSTALLATION COMPLETE!"
echo "======================================================================"
echo "To start using CareerPilot AI:"
echo "  1. Add your OpenRouter/Gemini API key in .env"
echo "  2. Run: .venv/bin/python main.py dashboard"
echo "======================================================================"

