@echo off
title Qiandao Sniper Client
cd /d "%~dp0client_tool"
..\..\eldo-chart\venv\Scripts\python.exe sniper_client.py
pause
