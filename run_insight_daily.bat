@echo off
rem 22:00 daily insight build; restart dashboard daemon safely (only that process)
cd /d D:\wx409.github.io
set LOG=temp\insight_daily.log
echo [%DATE% %TIME%] === insight daily start === >> %LOG%

"C:\Users\yezhe\AppData\Local\Programs\Python\Python310\python.exe" -X utf8 project_b\build_language_profile.py >> %LOG% 2>&1
"C:\Users\yezhe\AppData\Local\Programs\Python\Python310\python.exe" -X utf8 project_b\build_daily_insights.py >> %LOG% 2>&1

rem restart only the QQ music dashboard daemon (match full script name, never wildcard-all)
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'pythonw.exe' -and $_.CommandLine -like '*_GEO*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >> %LOG% 2>&1

schtasks /run /tn "wx409_dashboard_watchdog" >> %LOG% 2>&1
ping -n 60 127.0.0.1 >nul
"C:\Users\yezhe\AppData\Local\Programs\Python\Python310\python.exe" -X utf8 project_b\audit_git_sync.py >> %LOG% 2>&1
echo [%DATE% %TIME%] === insight daily end === >> %LOG%
exit /b 0
