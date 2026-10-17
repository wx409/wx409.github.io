<#
  install_admin_tasks.ps1 —— 需**管理员权限**运行一次（本项目默认非提权，故单独提供）

  目的（2026-10-17 用户裁决，方案 A + 根治停更）：
    1) 大屏 daemon 改为 SYSTEM + AtStartup（不依赖登录；Windows Update 23:29 那种重启后无需人登录即恢复）
    2) 看门狗 wx409_dashboard_watchdog 同样 SYSTEM + AtStartup（每 10 分钟查一次）
    3) 停用 QQMusicDashboardAutoStart（登录触发），避免两实例互抢
    4) 所有 wx409_* 任务的电池限制关闭（DisallowStartIfOnBatteries=false）

  用法（管理员 PowerShell）：
    powershell -NoProfile -ExecutionPolicy Bypass -File D:\wx409.github.io\tools\install_admin_tasks.ps1
  回滚：
    powershell -NoProfile -ExecutionPolicy Bypass -File D:\wx409.github.io\tools\install_admin_tasks.ps1 -Rollback
#>
param([switch]$Rollback)

$ErrorActionPreference = "Stop"
$site   = "D:\wx409.github.io"
$py     = "C:\Users\yezhe\AppData\Local\Programs\Python\Python310\python.exe"
$pyw    = "C:\Users\yezhe\AppData\Local\Programs\Python\Python310\pythonw.exe"
$gen    = "E:\wx\QQ音乐大屏生成器_GEO优化版_源码.py"
$bak    = Join-Path $site "temp\_task_backup_20261017"

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
        ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  Write-Host "✗ 需要管理员权限。请右键「以管理员身份运行 PowerShell」后重试。" -ForegroundColor Red
  exit 1
}

if ($Rollback) {
  foreach ($f in Get-ChildItem $bak -Filter *.xml -ErrorAction SilentlyContinue) {
    $n = [IO.Path]::GetFileNameWithoutExtension($f.Name)
    Write-Host "回滚 $n ..."
    schtasks /create /tn $n /xml $f.FullName /f | Out-Null
  }
  Start-ScheduledTask -TaskName "QQMusicDashboardAutoStart" -ErrorAction SilentlyContinue
  Write-Host "✓ 已按备份 XML 回滚；并已重启登录触发任务" -ForegroundColor Green
  exit 0
}

# ── 1) daemon：SYSTEM + AtStartup ──
$a1 = New-ScheduledTaskAction -Execute $pyw -Argument ('"{0}"' -f $gen) -WorkingDirectory "E:\wx"
$t1 = New-ScheduledTaskTrigger -AtStartup
$p1 = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$s1 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
      -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) `
      -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName "wx409_dashboard_daemon" -Action $a1 -Trigger $t1 `
  -Principal $p1 -Settings $s1 -Description "王晰大屏 daemon（SYSTEM/AtStartup，不依赖登录）" -Force | Out-Null
Write-Host "✓ wx409_dashboard_daemon（SYSTEM + AtStartup）" -ForegroundColor Green
Start-ScheduledTask -TaskName "wx409_dashboard_daemon"
Start-Sleep -Seconds 5

# ── 2) 看门狗：SYSTEM + AtStartup + 每 10 分钟 ──
$a2 = New-ScheduledTaskAction -Execute $py -Argument ('-X utf8 "{0}\project_b\dashboard_watchdog.py"' -f $site) `
      -WorkingDirectory $site
$t2a = New-ScheduledTaskTrigger -AtStartup
$t2b = New-ScheduledTaskTrigger -Once -At (Get-Date).Date.AddMinutes(2) `
       -RepetitionInterval (New-TimeSpan -Minutes 10) -RepetitionDuration ([TimeSpan]::MaxValue)
$p2 = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$s2 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
      -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
Register-ScheduledTask -TaskName "wx409_dashboard_watchdog" -Action $a2 -Trigger @($t2a, $t2b) `
  -Principal $p2 -Settings $s2 -Description "大屏 daemon 看门狗（进程消失即拉起 + 站内通知）" -Force | Out-Null
Write-Host "✓ wx409_dashboard_watchdog（SYSTEM + AtStartup + 每10分钟）" -ForegroundColor Green

# ── 3) 停用登录触发旧任务（避免双实例）──
Disable-ScheduledTask -TaskName "QQMusicDashboardAutoStart" -ErrorAction SilentlyContinue | Out-Null
Write-Host "✓ 已停用 QQMusicDashboardAutoStart（登录触发），避免两个 daemon 互抢" -ForegroundColor Yellow

# ── 4) 全部 wx409_* 关掉电池限制 ──
Get-ScheduledTask | Where-Object { $_.TaskName -like "wx409_*" } | ForEach-Object {
  try {
    $s = $_.Settings
    $s.DisallowStartIfOnBatteries = $false
    $s.StopIfGoingOnBatteries = $false
    Set-ScheduledTask -TaskName $_.TaskName -Settings $s | Out-Null
    Write-Host ("  · {0} 电池限制已关" -f $_.TaskName)
  } catch { Write-Host ("  ✗ {0}: {1}" -f $_.TaskName, $_.Exception.Message) -ForegroundColor Red }
}

Write-Host ""
Write-Host "验证：" -ForegroundColor Cyan
Write-Host '  (Get-ScheduledTask -TaskName wx409_dashboard_daemon).Principal'
Write-Host '  (Get-ScheduledTask -TaskName wx409_dashboard_watchdog).Triggers'
Write-Host '  python -X utf8 D:\wx409.github.io\project_b\dashboard_watchdog.py --dry'
Write-Host "回滚：本脚本 -Rollback"
