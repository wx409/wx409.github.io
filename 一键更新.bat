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

:: 禁用 Git 弹窗
set GIT_TERMINAL_PROMPT=0

:: 确保 remote 包含 Token
git remote set-url origin https://%GITHUB_TOKEN%@github.com/wx409/wx409.github.io.git

python deploy.py

echo.
pause