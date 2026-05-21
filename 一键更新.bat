@echo off
chcp 65001 >nul
echo.
echo ========================================
echo   王晰GEO站点 · 一键全自动部署
echo ========================================
echo.

cd /d "%~dp0"

:: 加载本地密钥
if exist secrets.bat (
    call secrets.bat
) else (
    echo [错误] 找不到 secrets.bat
    pause
    exit /b 1
)

python deploy.py
pause