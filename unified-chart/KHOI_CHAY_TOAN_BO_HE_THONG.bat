@echo off
chcp 65001 >nul
title KHOI CHAY TOAN BO HE THONG - MAY DUNG
echo =========================================================================
echo               KHOI CHAY TOAN BO HE THONG MARKET SNIPER
echo                        MAY: C:\Users\dung
echo =========================================================================
echo.

set "BASE_DIR=C:\Users\dung\Desktop\chart"

echo [1/3] DANG KHOI CHAY 4 BACKEND SERVERS (Ports 8000, 8001, 8002, 8003)...
start "[BACKEND] DD373 Server (Port 8000)" cmd /k "cd /d "%BASE_DIR%\dd373-chart\backend" && if exist "..\venv\Scripts\activate.bat" call "..\venv\Scripts\activate.bat" && python main.py"
start "[BACKEND] Eldorado Server (Port 8001)" cmd /k "cd /d "%BASE_DIR%\eldo-chart\backend" && if exist "..\venv\Scripts\activate.bat" call "..\venv\Scripts\activate.bat" && python main.py"
start "[BACKEND] G2G Server (Port 8002)" cmd /k "cd /d "%BASE_DIR%\g2g-chart\backend" && if exist "..\venv\Scripts\activate.bat" call "..\venv\Scripts\activate.bat" && python main.py"
start "[BACKEND] Qiandao Server (Port 8003)" cmd /k "cd /d "%BASE_DIR%\qiandao-chart\backend" && if exist "..\..\eldo-chart\venv\Scripts\activate.bat" call "..\..\eldo-chart\venv\Scripts\activate.bat" && python main.py"

timeout /t 2 /nobreak >nul

echo [2/3] DANG KHOI CHAY 4 FRONTEND WEBS (DD373, Eldorado, G2G, Unified)...
start "[FRONTEND] DD373 Web" cmd /k "cd /d "%BASE_DIR%\dd373-chart\frontend" && npm run dev"
start "[FRONTEND] Eldorado Web" cmd /k "cd /d "%BASE_DIR%\eldo-chart\frontend" && npm run dev"
start "[FRONTEND] G2G Web" cmd /k "cd /d "%BASE_DIR%\g2g-chart\frontend" && npm run dev"
start "[FRONTEND] Unified Dashboard" cmd /k "cd /d "%BASE_DIR%\unified-chart" && npm run dev -- --open"

timeout /t 2 /nobreak >nul

echo [3/3] DANG KHOI CHAY 4 SNIPER CLIENT TOOLS (GIAO DIEN CAO DU LIEU)...
start "[SNIPER] DD373 Client Tool" cmd /k "cd /d "%BASE_DIR%\dd373-chart" && if exist "venv\Scripts\activate.bat" call "venv\Scripts\activate.bat" && cd client_tool && python sniper_client.py"
start "[SNIPER] Eldorado Client Tool" cmd /k "cd /d "%BASE_DIR%\eldo-chart" && if exist "venv\Scripts\activate.bat" call "venv\Scripts\activate.bat" && cd client_tool && python sniper_client.py"
start "[SNIPER] G2G Client Tool" cmd /k "cd /d "%BASE_DIR%\g2g-chart" && if exist "venv\Scripts\activate.bat" call "venv\Scripts\activate.bat" && cd client_tool && python sniper_client.py"
start "[SNIPER] Qiandao Client Tool" cmd /k "cd /d "%BASE_DIR%\qiandao-chart" && if exist "..\eldo-chart\venv\Scripts\activate.bat" call "..\eldo-chart\venv\Scripts\activate.bat" && cd client_tool && python sniper_client.py"

echo.
echo =========================================================================
echo [SUCCESS] DA KHOI CHAY DAY DU TOAN BO HE THONG!
echo.
echo - 3 Backend Servers  : DD373 (8000), Eldorado (8001), G2G (8002)
echo - 4 Frontend Webs    : DD373 Web, Eldorado Web, G2G Web, Unified Dashboard
echo - 3 Sniper Clients   : DD373 Tool, Eldorado Tool, G2G Tool (San sang)
echo =========================================================================
pause
