# ============================================================
# WangXi Archive Auto Update Task - one-key install
# Usage:
#   Local: right-click "Run with PowerShell", or double-click the .bat
#   Desktop: powershell -ExecutionPolicy Bypass -File .\install_auto_update_task.ps1 -Machine desktop
# Schedule: 09:00 / 14:00 / 17:00 / 21:00 / 00:03 daily
# ============================================================
param(
    [string]$Machine = "laptop",
    [string]$RepoPath = ""
)

$ErrorActionPreference = "Stop"

if (-not $RepoPath) {
    $RepoPath = Split-Path -Parent $PSScriptRoot
}
$Script = Join-Path $RepoPath "project_b\auto_update.py"
if (-not (Test-Path $Script)) {
    Write-Host "[X] script not found: $Script" -ForegroundColor Red
    Write-Host "    Please check -RepoPath (e.g. D:\wx409.github.io)" -ForegroundColor Yellow
    exit 1
}

$Py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Py) {
    Write-Host "[X] python not found. Please install Python and add it to PATH." -ForegroundColor Red
    exit 1
}
Write-Host "[i] python: $Py"
Write-Host "[i] script: $Script"
Write-Host "[i] machine: $Machine ($([DateTime]::Now.DayOfWeek))"

$TaskName = "WangXiArchiveAutoUpdate"
$Arg = "`"$Script`" --machine $Machine --watch"

try {
    $Action = New-ScheduledTaskAction -Execute $Py -Argument $Arg -WorkingDirectory $RepoPath
    $Triggers = @(
        (New-ScheduledTaskTrigger -Daily -At 09:00),
        (New-ScheduledTaskTrigger -Daily -At 14:00),
        (New-ScheduledTaskTrigger -Daily -At 17:00),
        (New-ScheduledTaskTrigger -Daily -At 21:00),
        (New-ScheduledTaskTrigger -Daily -At 00:03)
    )
    $Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Triggers `
        -Settings $Settings -Description "WangXi archive auto update ($Machine)" `
        -Force | Out-Null
    Write-Host "[OK] task created: $TaskName (09:00 / 14:00 / 17:00 / 21:00 / 00:03)" -ForegroundColor Green
} catch {
    Write-Host "[X] create failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "    Please run this script as Administrator." -ForegroundColor Yellow
    exit 1
}

Start-Sleep -Milliseconds 500
$t = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($t) {
    Write-Host "[i] state: $($t.State)"
    ($t.Triggers | ForEach-Object { "    - daily $($_.StartBoundary.Substring(11,5))" }) | Write-Host
    Write-Host "[i] manual test: right-click the task -> Run, then check D:\wx409.github.io\logs\" -ForegroundColor Cyan
} else {
    Write-Host "[!] task not found. Please check." -ForegroundColor Yellow
}
