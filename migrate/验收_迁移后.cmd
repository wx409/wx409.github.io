@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
set SITE=D:\wx409.github.io
echo ============================================
echo  迁移后验收（在新笔记本上运行）
echo ============================================
echo.

echo [1/6] 检查关键路径...
if not exist "%SITE%\project_b" ( echo   [X] 未找到 %SITE%\project_b  & goto :fail )
echo   [OK] %SITE%
if not exist "E:\wx" ( echo   [!] 未找到 E:\wx —— 若你的盘符不是 E:，脚本里的绝对路径会失效 ) else ( echo   [OK] E:\wx )

echo.
echo [2/6] 检查环境...
where python >nul 2>nul || ( echo   [X] 未找到 python  & goto :fail )
python -c "import sys;print('   Python',sys.version.split()[0])"
where ffmpeg >nul 2>nul && (echo   [OK] ffmpeg) || (echo   [!] 缺 ffmpeg —— 音视频处理会失败)
where git >nul 2>nul && (echo   [OK] git) || (echo   [!] 缺 git)

echo.
echo [3/6] 九项审计...
set BAD=0
for %%A in (audit_nav audit_jsonld audit_bat audit_ops_coverage check_index_integrity audit_caliber audit_pipeline audit_site_url audit_song_names) do (
  pushd "%SITE%"
  python -X utf8 "project_b\%%A.py" >nul 2>&1
  set RC=!ERRORLEVEL!
  popd
  if !RC! EQU 0 ( echo   [OK] %%A ) else ( echo   [X]  %%A  RC=!RC! & set BAD=1 )
)

echo.
echo [4/6] 计划任务...
for %%T in (wx409_night_shutdown wx409_social_daily wx409_hook_patrol_evening wx409_propagation_watch_daily wx409_show_intake wx409_music_index_daily wx409_holiday_skip_daily wx409_tour_pool_daily wx409_vocal_nightly wx409_prune_raw_archive) do (
  schtasks /Query /TN %%T >nul 2>&1 && ( echo   [OK] %%T ) || ( echo   [X]  缺任务 %%T —— 需在操作中心重建 )
)
schtasks /Query /TN QQMusicDashboardAutoStart >nul 2>&1 && ( echo   [OK] QQMusicDashboardAutoStart ) || ( echo   [X]  缺任务 QQMusicDashboardAutoStart )

echo.
echo [5/6] 关键数据文件...
for %%F in ("%SITE%\dashboard\dashboard_data.json" "%SITE%\data\archive_baseline.json" "E:\wx\wx_textmine_out\music_index_long.csv") do (
  if exist %%F ( echo   [OK] %%~fF ) else ( echo   [X]  缺 %%~F )
)
echo.
echo   抽样指纹（与旧机对比，应一致）:
powershell -NoProfile -Command "foreach($p in @('%SITE%\dashboard\dashboard_data.json','%SITE%\data\archive_baseline.json')){ if(Test-Path $p){ $h=(Get-FileHash $p -Algorithm SHA256).Hash; Write-Host ('   '+$p+'  '+$h.Substring(0,16)) } }"

echo.
echo [6/6] 线上核验（约需 2-3 分钟）...
pushd "%SITE%"
python -X utf8 project_b\audit_live.py --wait 180
set LIVE=!ERRORLEVEL!
popd
if !LIVE! EQU 0 ( echo   [OK] audit_live 通过 ) else ( echo   [X]  audit_live RC=!LIVE! )

echo.
echo ============================================
if !BAD! EQU 0 ( echo  结论：本地九项审计通过 ) else ( echo  结论：有审计未通过，见上表 )
echo  记得：cookie 需在新机重新抓取，勿两机共用同一份。
echo ============================================
pause
exit /b 0

:fail
echo.
echo 关键路径或环境缺失，先修好再跑验收。
pause
exit /b 1
