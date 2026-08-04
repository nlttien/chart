#!/usr/bin/env bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Smart sudo detection
if [ "$(id -u)" -eq 0 ]; then
    CMD_SUDO=""
    REAL_USER="frappe"
    if [ -n "$SUDO_USER" ]; then
        REAL_USER="$SUDO_USER"
    fi
else
    CMD_SUDO="sudo"
    REAL_USER="$USER"
fi

echo "============================================================"
echo "    INSTALLING CHART API BACKGROUND SERVICE (SYSTEMD)       "
echo "============================================================"
echo " Running User  : $REAL_USER"
echo " Working Dir   : $SCRIPT_DIR"

# Make start_server.sh executable
chmod +x start_server.sh

SERVICE_PATH="/etc/systemd/system/chart-api.service"

echo "[1/3] Generating dynamic service configuration..."
$CMD_SUDO tee $SERVICE_PATH > /dev/null << EOF
[Unit]
Description=Unified Chart Market Scraper & API Server
After=network.target

[Service]
Type=simple
User=$REAL_USER
WorkingDirectory=$SCRIPT_DIR
ExecStart=$SCRIPT_DIR/start_server.sh
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/$REAL_USER/.Xauthority

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd manager configuration
echo "[2/3] Reloading systemd daemon..."
$CMD_SUDO systemctl daemon-reload

# Enable service to run on boot
echo "[3/3] Enabling chart-api service on boot..."
$CMD_SUDO systemctl enable chart-api

# Start/Restart service
echo "Starting chart-api background service..."
$CMD_SUDO systemctl restart chart-api

echo ""
echo "============================================================"
echo " [SUCCESS] Chart API Service installed and started 24/7!"
echo " Status check:"
echo "------------------------------------------------------------"
$CMD_SUDO systemctl status chart-api --no-pager
