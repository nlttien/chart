#!/usr/bin/env bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Dynamic user detection (if run with sudo, get original user)
REAL_USER="${SUDO_USER:-$USER}"

echo "============================================================"
echo "    INSTALLING CHART API BACKGROUND SERVICE (SYSTEMD)       "
echo "============================================================"
echo " Detected User : $REAL_USER"
echo " Detected Path : $SCRIPT_DIR"

# Make start_server.sh executable
chmod +x start_server.sh

SERVICE_PATH="/etc/systemd/system/chart-api.service"

echo "[1/3] Generating dynamic service configuration..."
cat << EOF | sudo tee $SERVICE_PATH > /dev/null
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

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd manager configuration
echo "[2/3] Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable service to run on boot
echo "[3/3] Enabling chart-api service on boot..."
sudo systemctl enable chart-api

# Start/Restart service
echo "Starting chart-api background service..."
sudo systemctl restart chart-api

echo ""
echo "============================================================"
echo " [SUCCESS] Chart API Service installed and started 24/7!"
echo " Status check:"
echo "------------------------------------------------------------"
sudo systemctl status chart-api --no-pager
