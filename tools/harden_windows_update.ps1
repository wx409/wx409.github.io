# ============================================================
# harden_windows_update.ps1 —— 抑制 Windows 更新自动重启（2026-09-09 事故后加固）
#
# 事故：2026-09-09 19:29:09，MoUsoCoreWorker.exe（SYSTEM）以"操作系统: Service Pack
#       (计划内)"发起重启，19:31/19:32/19:33 又连续重启两次安装 KB5124008 等；
#       活动时间 08:00-19:00 刚结束 29 分钟，重启窗口正好打开。
#       重启后无人登录 → 守护进程/计划任务全部停摆。
#
# 本机系统：Windows 11 25H2 家庭中文版（build 26200.9445，EditionID=CoreCountrySpecific）
#           —— 家庭版没有 gpedit，但部分 WindowsUpdate 策略注册表键仍被读取。
#
# 用法（管理员 PowerShell，脚本会自提权）：
#   powershell -ExecutionPolicy Bypass -File tools\harden_windows_update.ps1 -Mode Status
#   powershell -ExecutionPolicy Bypass -File tools\harden_windows_update.ps1 -Mode Manual    # 推荐
#   powershell -ExecutionPolicy Bypass -File tools\harden_windows_update.ps1 -Mode HardOff   # 彻底关自动更新
#   powershell -ExecutionPolicy Bypass -File tools\harden_windows_update.ps1 -Mode Restore   # 恢复默认
#
# 三档说明：
#   Manual  ：活动时间 06:00-23:00（18h 上限）+ 暂停更新 35 天 + 重启前弹通知 + 已登录不自动重启。
#             仍需每月手动检查更新（设置→Windows 更新→检查更新）。
#   HardOff ：在 Manual 基础上再停用 wuauserv / UsoSvc / WaaSMedicSvc（WaaSMedic 会把设置改回去，
#             必须一起停）→ 完全不会自动下载/安装/重启，直到 -Mode Restore。
#   Restore ：恢复自动更新与默认活动时间 08:00-19:00。
# ============================================================
param(
    [ValidateSet("Status", "Manual", "HardOff", "Restore")]
    [string]$Mode = "Status"
)

$ErrorActionPreference = "Stop"

# ---------- 自提权（Status 只读，不需要管理员） ----------
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin -and $Mode -ne "Status") {
    Write-Host "[i] 需要管理员权限，正在自提权（会弹出 UAC）..." -ForegroundColor Yellow
    $argList = @("-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`"", "-Mode", $Mode)
    Start-Process -FilePath (Get-Process -Id $PID).Path -ArgumentList $argList -Verb RunAs
    exit 0
}

$UX   = "HKLM:\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings"
$AU   = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU"
$WU   = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate"

function Show-Status {
    Write-Host "`n=== 当前状态 ===" -ForegroundColor Cyan
    $uxv = Get-ItemProperty $UX -ErrorAction SilentlyContinue
    "活动时间(ActiveHoursStart/End) : {0} -> {1}" -f $uxv.ActiveHoursStart, $uxv.ActiveHoursEnd | Write-Host
    "暂停更新到期(PauseUpdatesExpiryTime) : {0}" -f $uxv.PauseUpdatesExpiryTime | Write-Host
    "重启通知(RestartNotificationsAllowed2) : {0}" -f $uxv.RestartNotificationsAllowed2 | Write-Host
    $auv = Get-ItemProperty $AU -ErrorAction SilentlyContinue
    "AUOptions : {0}  (2=通知下载 4=自动下载安装)" -f $auv.AUOptions | Write-Host
    "NoAutoRebootWithLoggedOnUsers : {0}" -f $auv.NoAutoRebootWithLoggedOnUsers | Write-Host
    foreach ($s in @("wuauserv", "UsoSvc", "WaaSMedicSvc")) {
        $svc = Get-Service $s -ErrorAction SilentlyContinue
        if ($svc) { "服务 {0,-14}: 状态={1,-8} 启动类型={2}" -f $s, $svc.Status, $svc.StartType | Write-Host }
    }
    Write-Host ""
}

switch ($Mode) {
    "Status" { Show-Status }

    "Manual" {
        Show-Status
        Write-Host "=== 应用 Manual（抑制自动重启，保留手动检查更新）===" -ForegroundColor Cyan
        New-Item -Path $UX -Force | Out-Null
        New-Item -Path $AU -Force | Out-Null
        # 活动时间 06:00-23:00 = 18 小时（Windows 允许的最大跨度）
        Set-ItemProperty -Path $UX -Name ActiveHoursStart -Value 6  -Type DWord
        Set-ItemProperty -Path $UX -Name ActiveHoursEnd   -Value 23 -Type DWord
        # 重启前弹通知，允许推迟
        Set-ItemProperty -Path $UX -Name RestartNotificationsAllowed2 -Value 1 -Type DWord
        # 传统 WU 策略：已登录用户不自动重启 + 通知后由用户决定下载安装
        Set-ItemProperty -Path $AU -Name NoAutoRebootWithLoggedOnUsers -Value 1 -Type DWord
        Set-ItemProperty -Path $AU -Name AUOptions -Value 2 -Type DWord
        # 暂停自动更新 35 天（家庭版上限 5 周）；到期后重新运行本脚本即可续期
        $expiry = (Get-Date).AddDays(35).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        Set-ItemProperty -Path $UX -Name PauseUpdatesExpiryTime -Value $expiry -Type String
        Set-ItemProperty -Path $UX -Name PauseFeatureUpdatesStartTime  -Value (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") -Type String
        Set-ItemProperty -Path $UX -Name PauseQualityUpdatesStartTime  -Value (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") -Type String
        Write-Host "[OK] 活动时间 06:00-23:00；自动更新已暂停至 $expiry（UTC）" -ForegroundColor Green
        Write-Host "[!] 到期前请手动检查更新：设置 → Windows 更新 → 检查更新（建议在你在场时安装）" -ForegroundColor Yellow
        Show-Status
    }

    "HardOff" {
        Show-Status
        Write-Host "=== 应用 HardOff（彻底关闭自动更新与自动重启）===" -ForegroundColor Cyan
        foreach ($s in @("wuauserv", "UsoSvc", "WaaSMedicSvc")) {
            try {
                Stop-Service $s -Force -ErrorAction SilentlyContinue
                Set-Service  $s -StartupType Disabled
                Write-Host "[OK] 已停用服务 $s" -ForegroundColor Green
            } catch { Write-Host "[!] $s 处理失败: $($_.Exception.Message)" -ForegroundColor Yellow }
        }
        & $PSCommandPath -Mode Manual | Out-Null
        Write-Host "[OK] 已同时应用 Manual 档设置" -ForegroundColor Green
        Write-Host "[!] 从此不会自动装安全更新。需要更新时执行：" -ForegroundColor Yellow
        Write-Host "    powershell -ExecutionPolicy Bypass -File tools\harden_windows_update.ps1 -Mode Restore" -ForegroundColor Yellow
        Write-Host "    → 设置里点检查更新 → 装完后再次 -Mode HardOff" -ForegroundColor Yellow
        Show-Status
    }

    "Restore" {
        Write-Host "=== 恢复默认（自动更新 + 活动时间 08:00-19:00）===" -ForegroundColor Cyan
        foreach ($s in @("wuauserv", "UsoSvc", "WaaSMedicSvc")) {
            try {
                Set-Service $s -StartupType Automatic
                Start-Service $s -ErrorAction SilentlyContinue
                Write-Host "[OK] 已恢复服务 $s" -ForegroundColor Green
            } catch { Write-Host "[!] $s 恢复失败: $($_.Exception.Message)" -ForegroundColor Yellow }
        }
        New-Item -Path $UX -Force | Out-Null
        Set-ItemProperty -Path $UX -Name ActiveHoursStart -Value 8  -Type DWord
        Set-ItemProperty -Path $UX -Name ActiveHoursEnd   -Value 19 -Type DWord
        Remove-ItemProperty -Path $UX -Name PauseUpdatesExpiryTime -ErrorAction SilentlyContinue
        Remove-ItemProperty -Path $UX -Name PauseFeatureUpdatesStartTime -ErrorAction SilentlyContinue
        Remove-ItemProperty -Path $UX -Name PauseQualityUpdatesStartTime -ErrorAction SilentlyContinue
        if (Test-Path $AU) { Set-ItemProperty -Path $AU -Name AUOptions -Value 4 -Type DWord }
        Write-Host "[OK] 已恢复" -ForegroundColor Green
        Show-Status
    }
}
