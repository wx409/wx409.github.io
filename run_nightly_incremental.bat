@echo off
rem nightly incremental: 12 audio items, then cumulative report
cd /d D:\wx409.github.io
set PY="C:\Users\yezhe\AppData\Local\Programs\Python\Python310\python.exe"
%PY% -X utf8 "E:\wx\论文素材_王晰作传\音域分析\轨迹\每晚增量.py" --limit 12 --video-limit 0 >> temp\vocal_nightly.log 2>&1
%PY% -X utf8 project_b\build_nightly_report.py >> temp\vocal_nightly.log 2>&1
exit /b %ERRORLEVEL%
