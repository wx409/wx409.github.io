@echo off
chcp 65001 >nul
REM 王晰数字档案自动更新任务 · 重装（14:00 + 次日 00:05）
echo ============================================
echo  王晰数字档案自动更新任务 - 重装
echo  触发：每日 14:00 + 次日 00:05
echo ============================================
echo.
echo  [提示] 如提示"拒绝访问"，请右键本文件 → 以管理员身份运行。
echo.

REM 先删除旧任务（若存在），再重建
powershell -NoProfile -Command "Unregister-ScheduledTask -TaskName 'WangXiArchiveAutoUpdate' -ErrorAction SilentlyContinue"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_auto_update_task.ps1"

echo.
echo  安装完成。可在"任务计划程序"里查看任务 WangXiArchiveAutoUpdate。
echo  触发时间应为：14:00 / 00:05
pause
