@echo off
title DD373 Recycle Sniper Client
echo ======================================================
echo          KHOI CHAY DD373 RECYCLE SNIPER
echo ======================================================
echo.

cd /d "%~dp0dd373-chart"
if exist "venv\Scripts\activate.bat" (
    echo [INFO] Kich hoat moi truong Python venv...
    call "venv\Scripts\activate.bat"
)

cd client_tool
echo [INFO] Dang mo giao dien DD373 Sniper Client...
python sniper_client.py

pause
