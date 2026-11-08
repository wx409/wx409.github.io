@echo off
rem ??????????? ? ???? ? ?? ? ??? ? ????
cd /d D:\wx409.github.io
set PY="C:\Users\yezhe\AppData\Local\Programs\Python\Python310\python.exe"
%PY% -X utf8 project_b\index_gap_check.py >> temp\index_daily.log 2>&1
%PY% -X utf8 project_b\index_backfill.py >> temp\index_daily.log 2>&1
%PY% -X utf8 "E:\wx\论文素材_王晰作传\基线口径\compute_baseline_v1.py" >> temp\index_daily.log 2>&1
%PY% -X utf8 "E:\wx\论文素材_王晰作传\基线口径\generate_year_cards.py" >> temp\index_daily.log 2>&1
%PY% -X utf8 project_b\build_calibers.py >> temp\index_daily.log 2>&1
%PY% -X utf8 project_b\index_daily_backup.py >> temp\index_daily.log 2>&1
rem analysis pipeline (event study + vocal claims + page data); failure must not block
set RC=%ERRORLEVEL%
set "PSEXE=powershell"
where pwsh >nul 2>&1 && set "PSEXE=pwsh"
%PSEXE% -NoProfile -ExecutionPolicy Bypass -File "D:\wx409.github.io\analysis\run_all.ps1" >> "D:\wx409.github.io\temp\analysis_daily.log" 2>&1
exit /b %RC%
