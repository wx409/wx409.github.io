@echo off
chcp 65001 >nul
echo.
echo ========================================
echo   王晰GEO站点 · 一键全自动部署
echo ========================================
echo.

cd /d "%~dp0"

:: 填入你的密钥（只改这两行）
set DEEPSEEK_API_KEY=sk-2409323722314659b5130dfeda20b4c0
set GITHUB_TOKEN=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

python deploy.py

echo.
pause