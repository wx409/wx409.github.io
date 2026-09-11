# 自动生成：由 project_b/pipeline_registry.json 派生（勿手改；改登记表后重跑 build_pipeline_views.py）
# 生成时间：2026-09-11 14:05
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

# --- wx409_music_index_daily ---
$a = New-ScheduledTaskAction -Execute $py -Argument '-X utf8 "D:\wx409.github.io\project_b\build_music_index.py"' -WorkingDirectory 'D:\wx409.github.io\project_b'
$t = New-ScheduledTaskTrigger -Daily -At 23:58
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName 'wx409_music_index_daily' -Action $a -Trigger $t -Settings $s -Force | Out-Null
Write-Host '[OK] wx409_music_index_daily'

# --- wx409_weibo_pipeline_daily ---
$a = New-ScheduledTaskAction -Execute $py -Argument '-X utf8 ""' -WorkingDirectory 'D:\wx409.github.io'
$t = New-ScheduledTaskTrigger -Daily -At 09:00
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName 'wx409_weibo_pipeline_daily' -Action $a -Trigger $t -Settings $s -Force | Out-Null
Write-Host '[OK] wx409_weibo_pipeline_daily'
