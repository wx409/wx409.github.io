@echo off
chcp 65001 >nul
cd /d D:\wx409.github.io
python -X utf8 project_b\auto_fetch_social.py %*
exit /b %ERRORLEVEL%
