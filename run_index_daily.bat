@echo off
rem ??????????? ? ???? ? ?? ? ??? ? ????
cd /d D:\wx409.github.io
set PY="C:\Users\yezhe\AppData\Local\Programs\Python\Python310\python.exe"
%PY% -X utf8 project_b\index_gap_check.py >> temp\index_daily.log 2>&1
%PY% -X utf8 project_b\index_backfill.py >> temp\index_daily.log 2>&1
%PY% -X utf8 "E:\wx\????_????\????\compute_baseline_v1.py" >> temp\index_daily.log 2>&1
%PY% -X utf8 "E:\wx\????_????\????\generate_year_cards.py" >> temp\index_daily.log 2>&1
%PY% -X utf8 project_b\build_calibers.py >> temp\index_daily.log 2>&1
%PY% -X utf8 project_b\index_daily_backup.py >> temp\index_daily.log 2>&1
exit /b %ERRORLEVEL%
