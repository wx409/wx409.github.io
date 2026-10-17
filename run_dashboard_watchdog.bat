@echo off
rem ?? daemon ????? 10 ??????????? + ????
cd /d D:\wx409.github.io
"C:\Users\yezhe\AppData\Local\Programs\Python\Python310\python.exe" -X utf8 project_b\dashboard_watchdog.py >> temp\dashboard_watchdog_task.log 2>&1
exit /b %ERRORLEVEL%
