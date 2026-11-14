@echo off
rem Monthly AI/search visibility probe. Scheduled by DSH 2026-11-14.
cd /d D:\wx409.github.io
"D:\wx409.github.io\analysis\.venv\Scripts\python.exe" -X utf8 "D:\wx409.github.io\analysis\citeprobe\probe.py" >> "D:\wx409.github.io\analysis\citeprobe\probe.log" 2>&1
exit /b %ERRORLEVEL%
