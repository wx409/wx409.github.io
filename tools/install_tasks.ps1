# 自动生成：由 project_b/pipeline_registry.json 派生（勿手改；改登记表后重跑 build_pipeline_views.py）
# 生成时间：2026-10-31 21:09
$ErrorActionPreference = 'Stop'
$py = 'C:\Users\yezhe\AppData\Local\Programs\Python\Python310\python.exe'

# --- wx409_vocal_nightly ---
$a = New-ScheduledTaskAction -Execute $py -Argument '-X utf8 "E:\wx\论文素材_王晰作传\音域分析\轨迹\每晚增量.py" --limit 6' -WorkingDirectory 'E:\wx\论文素材_王晰作传\音域分析\轨迹'
$t = New-ScheduledTaskTrigger -Daily -At 22:00
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName 'wx409_vocal_nightly' -Action $a -Trigger $t -Settings $s -Force | Out-Null
Write-Host '[OK] wx409_vocal_nightly'

# --- wx409_prune_raw_archive ---
$a = New-ScheduledTaskAction -Execute $py -Argument '-X utf8 "D:\wx409.github.io\project_b\prune_raw_archive.py" --apply' -WorkingDirectory 'D:\wx409.github.io\project_b'
$t = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 10:00
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
Register-ScheduledTask -TaskName 'wx409_prune_raw_archive' -Action $a -Trigger $t -Settings $s -Force | Out-Null
Write-Host '[OK] wx409_prune_raw_archive'

# --- wx409_tour_pool_daily ---
$a = New-ScheduledTaskAction -Execute $py -Argument '-X utf8 "E:\wx\论文素材_王晰作传\音域分析\轨迹\补搜巡演曲目.py"' -WorkingDirectory 'E:\wx\论文素材_王晰作传\音域分析\轨迹'
$t = New-ScheduledTaskTrigger -Daily -At 09:00
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName 'wx409_tour_pool_daily' -Action $a -Trigger $t -Settings $s -Force | Out-Null
Write-Host '[OK] wx409_tour_pool_daily'

# --- wx409_holiday_skip_daily ---
$a = New-ScheduledTaskAction -Execute $py -Argument '-X utf8 "D:\wx409.github.io\project_b\holiday_skip_sync.py"' -WorkingDirectory 'D:\wx409.github.io\project_b'
$t = New-ScheduledTaskTrigger -Daily -At 09:00
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName 'wx409_holiday_skip_daily' -Action $a -Trigger $t -Settings $s -Force | Out-Null
Write-Host '[OK] wx409_holiday_skip_daily'

# --- wx409_show_intake ---
$a = New-ScheduledTaskAction -Execute $py -Argument '-X utf8 "D:\wx409.github.io\project_b\night_show_intake.py"' -WorkingDirectory 'D:\wx409.github.io\project_b'
$t = New-ScheduledTaskTrigger -Daily -At 09:00
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName 'wx409_show_intake' -Action $a -Trigger $t -Settings $s -Force | Out-Null
Write-Host '[OK] wx409_show_intake'

# --- wx409_propagation_watch_daily ---
$a = New-ScheduledTaskAction -Execute $py -Argument '-X utf8 "D:\wx409.github.io\project_b\propagation_watch.py"' -WorkingDirectory 'D:\wx409.github.io\project_b'
$t = New-ScheduledTaskTrigger -Daily -At 23:40
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName 'wx409_propagation_watch_daily' -Action $a -Trigger $t -Settings $s -Force | Out-Null
Write-Host '[OK] wx409_propagation_watch_daily'

# --- wx409_index_freshness ---
$a = New-ScheduledTaskAction -Execute $py -Argument '-X utf8 "D:\wx409.github.io\project_b\check_index_freshness.py"' -WorkingDirectory 'D:\wx409.github.io\project_b'
$t = New-ScheduledTaskTrigger -Daily -At 09:00
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName 'wx409_index_freshness' -Action $a -Trigger $t -Settings $s -Force | Out-Null
Write-Host '[OK] wx409_index_freshness'

# --- wx409_interview_daily ---
$a = New-ScheduledTaskAction -Execute $py -Argument '-X utf8 "D:\wx409.github.io\project_b\interview_daily.py"' -WorkingDirectory 'D:\wx409.github.io\project_b'
$t = New-ScheduledTaskTrigger -Daily -At 09:00
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName 'wx409_interview_daily' -Action $a -Trigger $t -Settings $s -Force | Out-Null
Write-Host '[OK] wx409_interview_daily'

# --- QQMusicDashboardAutoStart ---
$a = New-ScheduledTaskAction -Execute $py -Argument '-X utf8 "D:\wx409.github.io\project_b\QQ音乐大屏生成器_GEO优化版_源码.py"' -WorkingDirectory 'D:\wx409.github.io\project_b'
$t = New-ScheduledTaskTrigger -AtLogOn
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName 'QQMusicDashboardAutoStart' -Action $a -Trigger $t -Settings $s -Force | Out-Null
Write-Host '[OK] QQMusicDashboardAutoStart'

# --- wx409_music_index_daily ---
$a = New-ScheduledTaskAction -Execute $py -Argument '-X utf8 "D:\wx409.github.io\project_b\build_music_index.py"' -WorkingDirectory 'D:\wx409.github.io\project_b'
$t = New-ScheduledTaskTrigger -Daily -At 23:58
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName 'wx409_music_index_daily' -Action $a -Trigger $t -Settings $s -Force | Out-Null
Write-Host '[OK] wx409_music_index_daily'

# --- wx409_index_backfill_late ---
$a = New-ScheduledTaskAction -Execute $py -Argument '-X utf8 "D:\wx409.github.io\project_b\index_auto_repair.py"' -WorkingDirectory 'D:\wx409.github.io\project_b'
$t = New-ScheduledTaskTrigger -Daily -At 09:00
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName 'wx409_index_backfill_late' -Action $a -Trigger $t -Settings $s -Force | Out-Null
Write-Host '[OK] wx409_index_backfill_late'

# --- wx409_dashboard_watchdog ---
$a = New-ScheduledTaskAction -Execute $py -Argument '-X utf8 ""' -WorkingDirectory 'D:\wx409.github.io'
$t = New-ScheduledTaskTrigger -Daily -At 09:00
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName 'wx409_dashboard_watchdog' -Action $a -Trigger $t -Settings $s -Force | Out-Null
Write-Host '[OK] wx409_dashboard_watchdog'

# --- wx409_hook_patrol_evening ---
$a = New-ScheduledTaskAction -Execute $py -Argument '-X utf8 ""' -WorkingDirectory 'D:\wx409.github.io'
$t = New-ScheduledTaskTrigger -Daily -At 09:00
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName 'wx409_hook_patrol_evening' -Action $a -Trigger $t -Settings $s -Force | Out-Null
Write-Host '[OK] wx409_hook_patrol_evening'

# --- wx409_index_daily ---
$a = New-ScheduledTaskAction -Execute $py -Argument '-X utf8 ""' -WorkingDirectory 'D:\wx409.github.io'
$t = New-ScheduledTaskTrigger -Daily -At 09:00
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName 'wx409_index_daily' -Action $a -Trigger $t -Settings $s -Force | Out-Null
Write-Host '[OK] wx409_index_daily'

# --- wx409_insight_daily ---
$a = New-ScheduledTaskAction -Execute $py -Argument '-X utf8 ""' -WorkingDirectory 'D:\wx409.github.io'
$t = New-ScheduledTaskTrigger -Daily -At 09:00
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName 'wx409_insight_daily' -Action $a -Trigger $t -Settings $s -Force | Out-Null
Write-Host '[OK] wx409_insight_daily'

# --- wx409_night_shutdown ---
$a = New-ScheduledTaskAction -Execute $py -Argument '-X utf8 ""' -WorkingDirectory 'D:\wx409.github.io'
$t = New-ScheduledTaskTrigger -Daily -At 09:00
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName 'wx409_night_shutdown' -Action $a -Trigger $t -Settings $s -Force | Out-Null
Write-Host '[OK] wx409_night_shutdown'

# --- wx409_shutdown_after_batch_1 ---
$a = New-ScheduledTaskAction -Execute $py -Argument '-X utf8 ""' -WorkingDirectory 'D:\wx409.github.io'
$t = New-ScheduledTaskTrigger -Daily -At 09:00
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName 'wx409_shutdown_after_batch_1' -Action $a -Trigger $t -Settings $s -Force | Out-Null
Write-Host '[OK] wx409_shutdown_after_batch_1'

# --- wx409_shutdown_after_batch_2 ---
$a = New-ScheduledTaskAction -Execute $py -Argument '-X utf8 ""' -WorkingDirectory 'D:\wx409.github.io'
$t = New-ScheduledTaskTrigger -Daily -At 09:00
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName 'wx409_shutdown_after_batch_2' -Action $a -Trigger $t -Settings $s -Force | Out-Null
Write-Host '[OK] wx409_shutdown_after_batch_2'

# --- wx409_social_daily ---
$a = New-ScheduledTaskAction -Execute $py -Argument '-X utf8 ""' -WorkingDirectory 'D:\wx409.github.io'
$t = New-ScheduledTaskTrigger -Daily -At 09:00
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName 'wx409_social_daily' -Action $a -Trigger $t -Settings $s -Force | Out-Null
Write-Host '[OK] wx409_social_daily'

# --- wx409_weibo_pipeline_daily ---
$a = New-ScheduledTaskAction -Execute $py -Argument '-X utf8 ""' -WorkingDirectory 'D:\wx409.github.io'
$t = New-ScheduledTaskTrigger -Daily -At 09:00
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName 'wx409_weibo_pipeline_daily' -Action $a -Trigger $t -Settings $s -Force | Out-Null
Write-Host '[OK] wx409_weibo_pipeline_daily'
