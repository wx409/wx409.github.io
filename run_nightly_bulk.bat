@echo off
rem weekend bulk intake: 50 items (Sat/Sun 10:30). ASCII only to avoid codepage issues.
cd /d D:\wx409.github.io
set PY="C:\Users\yezhe\AppData\Local\Programs\Python\Python310\python.exe"
%PY% -X utf8 "E:\wx\论文素材_王晰作传\音域分析\轨迹\每晚增量.py" --limit 50 >> temp\nightly_bulk.log 2>&1
%PY% -X utf8 project_b\build_edit_list.py >> temp\nightly_bulk.log 2>&1
exit /b %ERRORLEVEL%
