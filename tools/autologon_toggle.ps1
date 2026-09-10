# ============================================================
# autologon_toggle.ps1 —— 方案甲：配置"开机自动登录"，让重启后无人值守也能自动跑任务
#
# 背景（2026-09-09 事故）：
#   Windows 更新 19:29 自动重启后停在锁屏界面，整夜无人登录 →
#   两个关键任务都是 LogonType=InteractiveToken，没有交互式会话就不启动 →
#   大屏守护进程 20:30/21:00/21:30/23:15/23:55 批次全部错过。
#
# 本脚本提供两条路（推荐第一条）：
#   A. -Mode ToolInfo   ：用微软 Sysinternals **Autologon.exe**（把密码存成 LSA 机密，较安全）
#   B. -Mode Enable     ：直接写 Winlogon 注册表（密码为**明文**存在注册表，需 -IUnderstandRisk）
#      -Mode Disable    ：关闭自动登录并清除已存密码
#      -Mode Status     ：查看当前自动登录配置
#
# ⚠️ 风险须知（本机实测：C/D/E/F 四卷均未启用 BitLocker 加密）：
#   自动登录 = 任何人开机即可进入桌面。物理接触风险请自行评估。
#   若在意，请改用 tools\switch_tasks_s4u.ps1（任务不依赖登录），或先给系统盘启用加密。
#
# 用法（管理员 PowerShell，脚本会自提权；Status 不需要管理员）：
#   powershell -ExecutionPolicy Bypass -File tools\autologon_toggle.ps1 -Mode Status
#   powershell -ExecutionPolicy Bypass -File tools\autologon_toggle.ps1 -Mode ToolInfo
#   powershell -ExecutionPolicy Bypass -File tools\autologon_toggle.ps1 -Mode Enable -IUnderstandRisk
#   powershell -ExecutionPolicy Bypass -File tools\autologon_toggle.ps1 -Mode Disable
# ============================================================
param(
    [ValidateSet("Status", "ToolInfo", "Enable", "Disable")]
    [string]$Mode = "Status",
    [string]$UserName = "",
    [switch]$IUnderstandRisk
)

$ErrorActionPreference = "Stop"
$WL = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"

$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin -and $Mode -ne "Status") {
    Write-Host "[i] 需要管理员权限，正在自提权（会弹出 UAC）..." -ForegroundColor Yellow
    $argList = @("-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`"", "-Mode", $Mode)
    if ($UserName) { $argList += @("-UserName", $UserName) }
    if ($IUnderstandRisk) { $argList += "-IUnderstandRisk" }
    Start-Process -FilePath (Get-Process -Id $PID).Path -ArgumentList $argList -Verb RunAs
    exit 0
}

function Show-Status {
    Write-Host "`n=== 自动登录当前状态 ===" -ForegroundColor Cyan
    $w = Get-ItemProperty $WL -ErrorAction SilentlyContinue
    $on = ($w.AutoAdminLogon -eq "1")
    Write-Host ("AutoAdminLogon      : {0}" -f $w.AutoAdminLogon)
    Write-Host ("DefaultUserName     : {0}" -f $w.DefaultUserName)
    Write-Host ("DefaultDomainName   : {0}" -f $w.DefaultDomainName)
    $hasPwd = [bool]$w.DefaultPassword
    Write-Host ("DefaultPassword     : {0}" -f $(if ($hasPwd) { "已设置（明文，长度 %d）" -f $w.DefaultPassword.Length } else { "未设置" }))
    Write-Host ("判定                : {0}" -f $(if ($on -and $hasPwd) { "已启用自动登录（重启后自动进桌面，任务可自动运行）" } else { "未启用自动登录（重启后会停在锁屏界面，登录态任务不会启动）" })) -ForegroundColor $(if ($on -and $hasPwd) { "Green" } else { "Yellow" })
    $task = Get-ScheduledTask -TaskName "QQMusicDashboardAutoStart" -ErrorAction SilentlyContinue
    if ($task) { Write-Host ("守护进程任务登录类型: {0}" -f $task.Principal.LogonType) -ForegroundColor Gray }
    Write-Host ""
}

switch ($Mode) {
    "Status" { Show-Status }

    "ToolInfo" {
        Write-Host "`n=== 推荐做法：Sysinternals Autologon（密码存 LSA 机密，不在注册表明文） ===" -ForegroundColor Cyan
        Write-Host "1) 下载: https://learn.microsoft.com/sysinternals/downloads/autologon"
        Write-Host "2) 解压后以管理员运行 Autologon64.exe"
        Write-Host "3) 填 User name / Domain / Password → 点 Enable"
        Write-Host "4) 注销或重启验证一次：应直接进入桌面（不停在锁屏）"
        Write-Host "5) 复核: 重新运行本脚本 -Mode Status，应显示已启用；且注册表不出现 DefaultPassword"
        Write-Host "`n关闭：Autologon64.exe → Disable（或本脚本 -Mode Disable）" -ForegroundColor Yellow
    }

    "Enable" {
        if (-not $IUnderstandRisk) {
            Write-Host "[X] 该方式会把密码以明文写入注册表 HKLM\...\Winlogon\DefaultPassword。" -ForegroundColor Red
            Write-Host "    确认要这么做请加 -IUnderstandRisk；更安全的做法见 -Mode ToolInfo。" -ForegroundColor Yellow
            exit 1
        }
        Show-Status
        if (-not $UserName) { $UserName = $env:USERNAME }
        Write-Host "=== 启用自动登录（$env:COMPUTERNAME\$UserName）===" -ForegroundColor Cyan
        $sec = Read-Host -AsSecureString ("请输入 {0} 的登录密码" -f $UserName)
        $plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
            [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
        if (-not $plain) { Write-Host "[X] 密码为空，已中止（空密码请直接用没有密码的账户策略）" -ForegroundColor Red; exit 1 }
        Set-ItemProperty $WL -Name AutoAdminLogon -Value "1" -Type String
        Set-ItemProperty $WL -Name DefaultUserName -Value $UserName -Type String
        Set-ItemProperty $WL -Name DefaultDomainName -Value $env:COMPUTERNAME -Type String
        Set-ItemProperty $WL -Name DefaultPassword -Value $plain -Type String
        $plain = $null
        Write-Host "[OK] 已启用自动登录" -ForegroundColor Green
        Write-Host "[!] 密码已明文写入注册表：HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\DefaultPassword" -ForegroundColor Yellow
        Write-Host "[i] 建议：注销一次验证能自动进桌面；若失败请用 -Mode Disable 回滚" -ForegroundColor Yellow
        Show-Status
    }

    "Disable" {
        Show-Status
        Write-Host "=== 关闭自动登录 ===" -ForegroundColor Cyan
        Set-ItemProperty $WL -Name AutoAdminLogon -Value "0" -Type String
        Remove-ItemProperty $WL -Name DefaultPassword -ErrorAction SilentlyContinue
        Write-Host "[OK] 已关闭并清除已存密码（重启后将回到锁屏界面，需要手动登录）" -ForegroundColor Green
        Show-Status
    }
}
