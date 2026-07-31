@echo off
title Unified Market Sniper Dashboard - Server
echo ======================================================
echo   KHOI CHAY UNIFIED MARKET SNIPER DASHBOARD
echo ======================================================
echo.

cd /d "%~dp0"

echo [1/2] Dang kiem tra moi truong Node.js...
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [LOI] Khong tim thay Node.js tren may tinh!
    echo Vui long cai dat Node.js tai: https://nodejs.org
    echo.
    pause
    exit /b
)

echo [2/2] Dang khoi chay Server va tu dong mo trinh duyet...
echo.
echo Dashboard se mo tai: http://localhost:5176
echo (De dung ung dung, dong cua so nay hoac bam Ctrl + C)
echo ======================================================
echo.

npm run dev -- --open
pause
