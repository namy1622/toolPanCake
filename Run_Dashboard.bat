@echo off
title Pancake Automation Dashboard
echo =======================================================
echo     DANG KHOI DONG PANCAKE AUTOMATION DASHBOARD SERVER
echo =======================================================
echo.
cd /d "%~dp0"
python backend/main.py
pause
