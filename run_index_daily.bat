@echo off
rem ASCII-only wrapper: all Chinese paths live in project_b\index_daily_all.py
cd /d D:\wx409.github.io
if errorlevel 1 exit /b 9
"C:\Users\yezhe\AppData\Local\Programs\Python\Python310\python.exe" -X utf8 project_b\index_daily_all.py
exit /b %ERRORLEVEL%
