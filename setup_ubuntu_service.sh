#!/usr/bin/env bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "    INSTALLING CHART API BACKGROUND SERVICE (SYSTEMD)       "
echo "============================================================"

# Make start_server.sh executable
chmod +x start_server.sh

# Copy service configuration to systemd
echo "[1/4] Copying chart-api.service to /etc/systemd/system/..."
sudo cp chart-api.service /etc/systemd/system/chart-api.service

# Reload systemd manager configuration
echo "[2/4] Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable service to run on boot
echo "[3/4] Enabling chart-api service on boot..."
sudo systemctl enable chart-api

# Start/Restart service
echo "[4/4] Starting chart-api background service..."
sudo systemctl restart chart-api

echo ""
echo "============================================================"
echo " [SUCCESS] Chart API Service installed and started 24/7!"
echo " Status check:"
echo "------------------------------------------------------------"
sudo systemctl status chart-api --no-pager
