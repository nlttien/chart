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
    if command -v curl &> /dev/null; then
        curl -sSL https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    elif command -v wget &> /dev/null; then
        wget -q https://bootstrap.pypa.io/get-pip.py -O get-pip.py
    else
        python3 -c "import urllib.request; urllib.request.urlretrieve('https://bootstrap.pypa.io/get-pip.py', 'get-pip.py')"
    fi
    python get-pip.py
    rm -f get-pip.py
fi

echo "[2/3] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "[INFO] Installing/Verifying Playwright Chromium Browser..."
python -m playwright install chromium || playwright install chromium || true
python -m playwright install-deps chromium 2>/dev/null || true

# 2. Build Unified Web UI if NVM/Node is available (Requires Node >= 18 for Vite 5)
if [ -d "unified-chart" ] && [ ! -d "unified-chart/dist" ]; then
    export NVM_DIR="$HOME/.nvm"
    if [ -s "$NVM_DIR/nvm.sh" ]; then
        \. "$NVM_DIR/nvm.sh"
        nvm use 20 2>/dev/null || nvm use 18 2>/dev/null || nvm use --lts 2>/dev/null || true
    fi
    NODE_MAJOR=$(node -v 2>/dev/null | cut -d'.' -f1 | sed 's/v//')
    if [ -n "$NODE_MAJOR" ] && [ "$NODE_MAJOR" -ge 18 ] 2>/dev/null; then
        echo "[INFO] Building Web UI Dashboard (Node $NODE_MAJOR)..."
        (cd unified-chart && npm install && npm run build) || echo "[WARN] Web UI build failed, proceeding..."
    else
        echo "[INFO] Skipping Web UI build (Node.js version is older than 18). FastAPI Server starting directly..."
    fi
fi

# 3. Start FastAPI Server with Graphical Display (DISPLAY=:0 for Headed Chrome)
echo "[3/3] Launching FastAPI Unified Server on http://0.0.0.0:8000..."

# Auto-detect dynamic XAUTHORITY for Ubuntu GDM3 / LightDM / Desktop session
if [ -z "$XAUTHORITY" ] || [ ! -f "$XAUTHORITY" ]; then
    USER_ID=$(id -u frappe 2>/dev/null || id -u)
    DYNAMIC_XAUTH=$(find /run/user/$USER_ID /tmp /home -maxdepth 3 \( -name "*Xauthority*" -o -name "xauth_*" \) 2>/dev/null | head -n 1)
    if [ -n "$DYNAMIC_XAUTH" ]; then
        export XAUTHORITY="$DYNAMIC_XAUTH"
    fi
fi

# Detect active X11 sockets (:0 or :1)
if [ -e "/tmp/.X11-unix/X0" ]; then
    export DISPLAY=":0"
elif [ -e "/tmp/.X11-unix/X1" ]; then
    export DISPLAY=":1"
else
    export DISPLAY="${DISPLAY:-:0}"
fi

echo "[INFO] GUI Display target set to DISPLAY=$DISPLAY (XAUTHORITY=$XAUTHORITY)"
xhost +local: 2>/dev/null || xhost + 2>/dev/null || true

# Free port 8000 if occupied by old process
fuser -k 8000/tcp >/dev/null 2>&1 || true
sleep 1

exec uvicorn server.main:app --host 0.0.0.0 --port 8000
