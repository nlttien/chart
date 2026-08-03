#!/usr/bin/env bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "      STARTING UNIFIED CHART API & WEB SERVER (LINUX)       "
echo "============================================================"

# 1. Virtual environment setup
if [ ! -d "venv" ]; then
    echo "[1/3] Creating Python Virtual Environment (venv)..."
    python3 -m venv venv 2>/dev/null || python3 -m venv --without-pip venv
fi

source venv/bin/activate

if ! command -v pip &> /dev/null; then
    echo "[INFO] Installing pip into virtualenv..."
    curl -sSL https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    python get-pip.py
    rm -f get-pip.py
fi

echo "[2/3] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 2. Build Unified Web UI if NVM/Node is available
if [ -d "unified-chart" ] && [ ! -d "unified-chart/dist" ]; then
    echo "[INFO] Building Web UI Dashboard (unified-chart)..."
    export NVM_DIR="$HOME/.nvm"
    if [ -s "$NVM_DIR/nvm.sh" ]; then
        \. "$NVM_DIR/nvm.sh"
    fi
    if command -v npm &> /dev/null; then
        (cd unified-chart && npm install && npm run build) || echo "[WARN] Web UI build failed, proceeding..."
    fi
fi

# 3. Start FastAPI Server with auto-reload
echo "[3/3] Launching FastAPI Unified Server on http://0.0.0.0:8000..."
exec uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
