@echo off
rem ASCII-only wrapper: Chinese paths live in project_b\nightly_bulk_all.py
cd /d D:\wx409.github.io
"C:\Users\yezhe\AppData\Local\Programs\Python\Python310\python.exe" -X utf8 project_b\nightly_bulk_all.py
exit /b %ERRORLEVEL%
