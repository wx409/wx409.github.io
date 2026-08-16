@echo off
chcp 65001 >nul
REM 王晰数字档案自动更新任务 · 一键安装（双击运行）
echo ============================================
echo  王晰数字档案自动更新任务 - 安装
echo ============================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_auto_update_task.ps1"
echo.
pause
