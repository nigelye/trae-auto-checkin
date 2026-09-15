@echo off
chcp 65001 >nul
echo ========================================
echo   TRAE 每日自动签到
echo ========================================
echo.

cd /d "%~dp0"

python trae_checkin.py

echo.
echo 按任意键退出...
pause >nul
