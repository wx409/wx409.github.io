# ============================================================
# 王晰数字档案 · 自动更新任务一键安装脚本
# 用法：
#   本机（笔记本）：右键"使用 PowerShell 运行"，或双击同目录 .bat
#   台式机：powershell -ExecutionPolicy Bypass -File .\install_auto_update_task.ps1 -Machine desktop
# 功能：注册计划任务 WangXiArchiveAutoUpdate（每日 14:00 + 次日 00:05 各一次）
# ============================================================
param(
    [string]$Machine = "laptop",      # laptop（工作日值班）/ desktop（周末值班）
    [string]$RepoPath = ""            # 仓库路径，默认取本脚本所在目录的上一级
)

$ErrorActionPreference = "Stop"

if (-not $RepoPath) {
    $RepoPath = Split-Path -Parent $PSScriptRoot
}
$Script = Join-Path $RepoPath "project_b\auto_update.py"
if (-not (Test-Path $Script)) {
    Write-Host "[X] 未找到 $Script" -ForegroundColor Red
    Write-Host "    请确认仓库路径（-RepoPath D:\wx409.github.io）" -ForegroundColor Yellow
    exit 1
}

# 定位 python
$Py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Py) {
    Write-Host "[X] 未找到 python，请先安装并加入 PATH" -ForegroundColor Red
    exit 1
}
Write-Host "[i] python: $Py"
Write-Host "[i] 脚本:   $Script"
Write-Host "[i] 机器:   $Machine（$([DateTime]::Now.DayOfWeek)）"

$TaskName = "WangXiArchiveAutoUpdate"
$Arg = "`"$Script`" --machine $Machine --watch"

try {
    $Action = New-ScheduledTaskAction -Execute $Py -Argument $Arg -WorkingDirectory $RepoPath
    $Triggers = @(
        (New-ScheduledTaskTrigger -Daily -At 14:00),
        (New-ScheduledTaskTrigger -Daily -At 00:05)
    )
    $Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Triggers `
        -Settings $Settings -Description "王晰数字档案自动聚合（采集->构建->发布->IndexNow），$Machine 值班" `
        -Force | Out-Null
    Write-Host "[OK] 任务已创建：$TaskName（每日 14:00 / 次日 00:05）" -ForegroundColor Green
} catch {
    Write-Host "[X] 创建失败：$($_.Exception.Message)" -ForegroundColor Red
    Write-Host "    请尝试：以管理员身份运行 PowerShell 后再执行本脚本" -ForegroundColor Yellow
    exit 1
}

# 验证
Start-Sleep -Milliseconds 500
$t = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($t) {
    Write-Host "[i] 状态: $($t.State)"
    ($t.Triggers | ForEach-Object { "    - 每日 $($_.StartBoundary.Substring(11,5))" }) | Write-Host
    Write-Host "[i] 手动测试：右键该任务 → 运行，然后查看 D:\wx409.github.io\logs\ 日志" -ForegroundColor Cyan
} else {
    Write-Host "[!] 任务未找到，请检查" -ForegroundColor Yellow
}
