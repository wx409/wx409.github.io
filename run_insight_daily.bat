@echo off
rem ?? 22:00 ???????? ? ???? ? ??????????? git ??????????????
cd /d D:\wx409.github.io
set LOG=temp\insight_daily.log
echo [%DATE% %TIME%] === insight daily start === >> %LOG%
"C:\Users\yezhe\AppData\Local\Programs\Python\Python310\python.exe" -X utf8 project_b\build_language_profile.py >> %LOG% 2>&1
"C:\Users\yezhe\AppData\Local\Programs\Python\Python310\python.exe" -X utf8 project_b\build_daily_insights.py >> %LOG% 2>&1
rem ??????????????????????????? pythonw?
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*?????*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >> %LOG% 2>&1
schtasks /run /tn "wx409_dashboard_watchdog" >> %LOG% 2>&1
timeout /t 300 /nobreak >nul
"C:\Users\yezhe\AppData\Local\Programs\Python\Python310\python.exe" -X utf8 project_b\audit_git_sync.py >> %LOG% 2>&1
echo [%DATE% %TIME%] === insight daily end === >> %LOG%
exit /b 0
