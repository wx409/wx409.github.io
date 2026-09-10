# ============================================================
# switch_tasks_s4u.ps1 —— 让关键计划任务"未登录也能运行"（S4U），
#                       解决"重启后必须解锁屏幕才会自动跑"的问题
#
# 背景（2026-09-09 事故）：
#   两个关键任务都是 LogonType=InteractiveToken（只在用户登录后运行）：
#     · QQMusicDashboardAutoStart  —— 登录触发，pythonw 跑大屏守护进程
#     · WangXiArchiveAutoUpdate    —— 09/14/17/21/00:03，python 跑 auto_update
#   9/9 19:29 Windows 更新自动重启后无人登录 → 两个任务全部不跑，整夜停摆。
#
# 本脚本把守护进程任务改成：开机触发 + 登录触发 + LogonType S4U（无需存密码）。
# 守护进程用 DrissionPage **headless** Edge（源码 co.headless(True)），
# 理论上不需要交互桌面，但必须在 S4U 下实测 —— 用 -Mode TestHeadless 验证。
#
# ⚠️ 已知限制（务必先读）：
#   1. S4U 会话没有加载用户配置文件 → %USERPROFILE%\.ssh 不可用，
#      **git push（origin 是 ssh://git@ssh.github.com:443）很可能失败**。
#      因此 WangXiArchiveAutoUpdate 默认不动；它的漏批由 watchdog 在下次登录时补。
#   2. DPAPI 加密的 secrets（secrets.bat.dpapi）在 S4U 下同样可能解不开。
#   3. 若 S4U 实测失败，改用"自动登录"方案（重启后自动进桌面，交互任务照常运行）。
#
# 用法（管理员 PowerShell，会自提权）：
#   powershell -ExecutionPolicy Bypass -File tools\switch_tasks_s4u.ps1 -Mode Status
#   powershell -ExecutionPolicy Bypass -File tools\switch_tasks_s4u.ps1 -Mode TestHeadless
#   powershell -ExecutionPolicy Bypass -File tools\switch_tasks_s4u.ps1 -Mode Apply
#   powershell -ExecutionPolicy Bypass -File tools\switch_tasks_s4u.ps1 -Mode Restore
# ============================================================
param(
    [ValidateSet("Status", "TestHeadless", "Apply", "Restore")]
    [string]$Mode = "Status",
    [switch]$IncludeAutoUpdate
)

$ErrorActionPreference = "Stop"

$DAEMON_TASK = "QQMusicDashboardAutoStart"
$AUTO_TASK   = "WangXiArchiveAutoUpdate"
$PYW  = "C:\Users\yezhe\AppData\Local\Programs\Python\Python310\pythonw.exe"
$PY   = "C:\Users\yezhe\AppData\Local\Programs\Python\Python310\python.exe"
$DAEMON_SRC = "E:\wx\QQ音乐大屏生成器_GEO优化版_源码.py"
$DAEMON_WD  = "E:\wx"
$REPO = "D:\wx409.github.io"
$USER_ID = "$env:COMPUTERNAME\$env:USERNAME"

$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin -and $Mode -ne "Status") {
    Write-Host "[i] 需要管理员权限，正在自提权（会弹出 UAC）..." -ForegroundColor Yellow
    $argList = @("-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`"", "-Mode", $Mode)
    if ($IncludeAutoUpdate) { $argList += "-IncludeAutoUpdate" }
    Start-Process -FilePath (Get-Process -Id $PID).Path -ArgumentList $argList -Verb RunAs
    exit 0
}

function Show-TaskInfo([string]$name) {
    $t = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if ($t) {
        $i = Get-ScheduledTaskInfo -TaskName $name -ErrorAction SilentlyContinue
        Write-Host ("  任务 {0} | 状态 {1} | 登录类型 {2} | 运行身份 {3}" -f `
            $name, $t.State, $t.Principal.LogonType, $t.Principal.UserId) -ForegroundColor Gray
        Write-Host ("    触发器: {0}" -f (($t.Triggers | ForEach-Object { $_.CimClass.CimClassName }) -join ", ")) -ForegroundColor DarkGray
        if ($i) { Write-Host ("    上次运行 {0} 结果 {1}" -f $i.LastRunTime, $i.LastTaskResult) -ForegroundColor DarkGray }
        return
    }
    # 回退：Get-ScheduledTask/CIM 不可用时直接读任务 XML
    $xmlPath = "C:\Windows\System32\Tasks\$name"
    if (Test-Path $xmlPath) {
        try {
            $x = [xml](Get-Content -Raw -LiteralPath $xmlPath)
            $trg = ($x.Task.Triggers.ChildNodes | ForEach-Object { $_.Name }) -join ", "
            $cmd = ($x.Task.Actions.Exec | ForEach-Object { "$($_.Command) $($_.Arguments)" }) -join " | "
            Write-Host ("  任务 {0} | 登录类型 {1} | 运行身份 {2}" -f `
                $name, $x.Task.Principals.Principal.LogonType, $x.Task.Principals.Principal.UserId) -ForegroundColor Gray
            Write-Host ("    触发器: {0}" -f $trg) -ForegroundColor DarkGray
            Write-Host ("    命令: {0}" -f $cmd) -ForegroundColor DarkGray
            Write-Host ("    (来源: 任务XML；Get-ScheduledTask 不可用)") -ForegroundColor DarkGray
            return
        } catch { }
    }
    Write-Host "  (任务不存在: $name)" -ForegroundColor DarkGray
}

switch ($Mode) {
    "Status" {
        Write-Host "`n=== 关键任务当前配置 ===" -ForegroundColor Cyan
        Show-TaskInfo $DAEMON_TASK
        Show-TaskInfo $AUTO_TASK
        Write-Host ""
    }

    "TestHeadless" {
        Write-Host "=== S4U 无会话实测（安全探针，双跑对照）===" -ForegroundColor Cyan
        Write-Host "探针只做: 起 headless Edge → 打开 QQ音乐页 → 取数；不写数据、不重建看板、不 push。" -ForegroundColor DarkGray
        $probe = Join-Path $REPO "tools\s4u_headless_probe.py"
        if (-not (Test-Path $probe)) { Write-Host "[X] 探针不存在: $probe" -ForegroundColor Red; exit 1 }
        $probeLog = Join-Path $REPO "logs\s4u_headless_probe.log"
        if (Test-Path $probeLog) { Remove-Item $probeLog -Force -ErrorAction SilentlyContinue }

        function Invoke-Probe([string]$taskName, [string]$logonType, [string]$label) {
            Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
            $action = New-ScheduledTaskAction -Execute $PY -Argument "`"$probe`"" -WorkingDirectory $REPO
            $principal = New-ScheduledTaskPrincipal -UserId $USER_ID -LogonType $logonType -RunLevel Limited
            $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
                -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -MultipleInstances IgnoreNew
            Register-ScheduledTask -TaskName $taskName -Action $action -Principal $principal `
                -Settings $settings -Description "S4U 探针（临时，可删除）" -Force | Out-Null
            Write-Host ("[i] {0}：以 {1} 运行探针…" -f $label, $logonType) -ForegroundColor Yellow
            Start-ScheduledTask -TaskName $taskName
            $deadline = (Get-Date).AddMinutes(4)
            do {
                Start-Sleep -Seconds 5
                $st = (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue).State
            } while ($st -eq "Running" -and (Get-Date) -lt $deadline)
            $info = Get-ScheduledTaskInfo -TaskName $taskName -ErrorAction SilentlyContinue
            $rc = if ($info) { $info.LastTaskResult } else { "?" }
            Write-Host ("    {0} 结束：LastTaskResult={1}（0=探针通过）" -f $label, $rc) -ForegroundColor Gray
            Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
            return $rc
        }

        $rcInteractive = Invoke-Probe "WX_Probe_Interactive" "InteractiveToken" "基线（交互式令牌）"
        $logA = if (Test-Path $probeLog) { (Get-Content $probeLog -Encoding UTF8 | Select-Object -Last 6) -join "`n    " } else { "（无日志）" }
        Write-Host "    基线日志尾部:`n    $logA" -ForegroundColor DarkGray

        $rcS4U = Invoke-Probe "WX_Probe_S4U" "S4U" "实测（S4U，无登录）"
        $logB = if (Test-Path $probeLog) { (Get-Content $probeLog -Encoding UTF8 | Select-Object -Last 10) -join "`n    " } else { "（无日志）" }
        Write-Host "    S4U 日志尾部:`n    $logB" -ForegroundColor DarkGray

        Write-Host "`n=== 判定 ===" -ForegroundColor Cyan
        if ($rcInteractive -ne 0 -and $rcS4U -ne 0) {
            Write-Host "[!] 两次都没通过 —— 探针本身可能有问题（或浏览器被占用），请把上面日志发我，先别切 S4U。" -ForegroundColor Yellow
        } elseif ($rcS4U -eq 0) {
            Write-Host "[OK] S4U 可跑通 → 重启后无需解锁即可自动运行。可执行: -Mode Apply" -ForegroundColor Green
        } else {
            Write-Host "[X] 交互式能跑、S4U 跑不通 → S4U 方案不可用，请改用自动登录方案：" -ForegroundColor Red
            Write-Host "    powershell -ExecutionPolicy Bypass -File tools\autologon_toggle.ps1 -Mode ToolInfo" -ForegroundColor Yellow
        }
        Write-Host "[i] 完整探针日志: $probeLog" -ForegroundColor DarkGray
    }

    "Apply" {
        Write-Host "=== 把守护进程任务改为 开机触发 + 登录触发 + S4U ===" -ForegroundColor Cyan
        Show-TaskInfo $DAEMON_TASK
        $action = New-ScheduledTaskAction -Execute $PYW -Argument "`"$DAEMON_SRC`"" -WorkingDirectory $DAEMON_WD
        $t1 = New-ScheduledTaskTrigger -AtStartup
        $t1.Delay = "PT2M"
        $t2 = New-ScheduledTaskTrigger -AtLogOn -User $USER_ID
        $principal = New-ScheduledTaskPrincipal -UserId $USER_ID -LogonType S4U -RunLevel Limited
        $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
            -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -MultipleInstances IgnoreNew
        Register-ScheduledTask -TaskName $DAEMON_TASK -Action $action -Trigger @($t1, $t2) `
            -Principal $principal -Settings $settings `
            -Description "开机/登录均启动QQ音乐监测大屏守护进程（S4U，无需解锁屏幕）" -Force | Out-Null
        Write-Host "[OK] 已重注册 $DAEMON_TASK" -ForegroundColor Green
        Show-TaskInfo $DAEMON_TASK

        if ($IncludeAutoUpdate) {
            Write-Host "=== 同步改造 $AUTO_TASK（⚠️ git push 可能因无 SSH 密钥而失败）===" -ForegroundColor Yellow
            $aAction = New-ScheduledTaskAction -Execute $PY -Argument "`"$REPO\project_b\auto_update.py`" --machine laptop --watch" -WorkingDirectory $REPO
            $aTrig = @(
                (New-ScheduledTaskTrigger -AtStartup),
                (New-ScheduledTaskTrigger -Daily -At 09:00),
                (New-ScheduledTaskTrigger -Daily -At 14:00),
                (New-ScheduledTaskTrigger -Daily -At 17:00),
                (New-ScheduledTaskTrigger -Daily -At 21:00),
                (New-ScheduledTaskTrigger -Daily -At 00:03)
            )
            $aSet = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
                -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -MultipleInstances IgnoreNew
            Register-ScheduledTask -TaskName $AUTO_TASK -Action $aAction -Trigger $aTrig `
                -Principal $principal -Settings $aSet `
                -Description "WangXi archive auto update (laptop, S4U)" -Force | Out-Null
            Write-Host "[OK] 已重注册 $AUTO_TASK（建议随后手动跑一次确认 git push 是否成功）" -ForegroundColor Green
            Show-TaskInfo $AUTO_TASK
        } else {
            Write-Host "[i] 未改动 $AUTO_TASK（默认不动；如确需一并改造，加 -IncludeAutoUpdate）" -ForegroundColor DarkGray
        }
        Write-Host "`n[i] 建议重启一次验证：不登录 → 等 3 分钟 → 看 E:\wx\qqmusic_dp_edge.log 是否出现启动横幅。" -ForegroundColor Yellow
    }

    "Restore" {
        Write-Host "=== 恢复为 登录触发 + InteractiveToken（原状）===" -ForegroundColor Cyan
        $action = New-ScheduledTaskAction -Execute $PYW -Argument "`"$DAEMON_SRC`"" -WorkingDirectory $DAEMON_WD
        $trig = New-ScheduledTaskTrigger -AtLogOn -User $USER_ID
        $principal = New-ScheduledTaskPrincipal -UserId $USER_ID -LogonType InteractiveToken -RunLevel Limited
        $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
            -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -MultipleInstances IgnoreNew
        Register-ScheduledTask -TaskName $DAEMON_TASK -Action $action -Trigger $trig `
            -Principal $principal -Settings $settings `
            -Description "登录后隐藏启动QQ音乐监测大屏常驻进程（替代启动文件夹VBS）" -Force | Out-Null
        Write-Host "[OK] 已恢复 $DAEMON_TASK" -ForegroundColor Green
        Show-TaskInfo $DAEMON_TASK
    }
}
