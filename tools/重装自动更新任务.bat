@echo off
REM ============================================================
REM  WangXi archive auto-update task - CORRECT reinstall
REM  (ASCII-only on purpose: cmd mangles Chinese text in .bat)
REM
REM  Schedule installed: 09:00 / 14:00 / 17:00 / 21:00 / 00:03 (daily)
REM  Verified against tools\install_auto_update_task.ps1 on 2026-09-11
REM
REM  Superseded the old bat whose header claimed "14:00 + 00:05".
REM  The outdated copy is archived under temp\ (folder dated 2026-09-11).
REM ============================================================
title Reinstall WangXi auto-update task
echo ============================================================
echo   WangXi archive auto-update task - REINSTALL
echo   Schedule: 09:00 / 14:00 / 17:00 / 21:00 / 00:03  (daily)
echo ============================================================
echo.
echo   [current task]
schtasks /query /tn "WangXiArchiveAutoUpdate" /fo LIST 2>nul | findstr /i "TaskName Status Next"
echo.
echo   [re-registering - Administrator rights may be required]
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_auto_update_task.ps1"
echo.
echo   ------------------------------------------------------------
echo   NOTE: to also run after a REBOOT WITHOUT logging in,
echo   use the S4U variant instead (run as Administrator):
echo     powershell -ExecutionPolicy Bypass -File "%~dp0switch_tasks_s4u.ps1" -Mode Apply -IncludeAutoUpdate
echo   ------------------------------------------------------------
echo.
pause
