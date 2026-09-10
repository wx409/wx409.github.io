# ============================================================
# export_bitlocker_key.ps1 —— 导出本机 BitLocker/设备加密恢复密钥到 D:\Bitlocer.txt
#
# 用户要求（2026-09-10）：本机的 BitLocker 恢复密钥直接写入 D:\Bitlocer.txt
#
# 用法（普通 PowerShell 即可，脚本会自提权并弹 UAC）：
#   powershell -ExecutionPolicy Bypass -File tools\export_bitlocker_key.ps1
#
# 说明：
#   · Windows 11 家庭中文版没有完整 BitLocker 管理界面，但若开启了"设备加密"，
#     恢复密钥同样可以用 manage-bde 读出（需要管理员）。
#   · 若本机未加密，脚本会明确写出"未启用"，不会伪造内容。
#   · ⚠️ 恢复密钥是敏感信息：D:\Bitlocer.txt 请勿提交 git、勿上传网盘。
# ============================================================
param(
    [string]$OutFile = "D:\Bitlocer.txt"
)

$ErrorActionPreference = "Continue"

$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[i] 需要管理员权限，正在自提权（会弹出 UAC）..." -ForegroundColor Yellow
    $argList = @("-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`"", "-OutFile", "`"$OutFile`"")
    Start-Process -FilePath (Get-Process -Id $PID).Path -ArgumentList $argList -Verb RunAs
    exit 0
}

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add("# BitLocker / 设备加密恢复密钥导出")
$lines.Add("# 机器: $env:COMPUTERNAME   用户: $env:USERNAME")
$lines.Add("# 导出时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
$lines.Add("# 系统: " + (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion').ProductName +
            " " + (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion').DisplayVersion +
            " build " + (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion').CurrentBuild +
            "." + (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion').UBR)
$lines.Add("# 敏感文件：勿提交 git / 勿上传网盘。")
$lines.Add("")

Write-Host "=== 卷加密状态 ===" -ForegroundColor Cyan
$status = (manage-bde -status 2>&1 | Out-String)
$lines.Add("## manage-bde -status")
$lines.Add($status.TrimEnd())
$lines.Add("")

$found = $false
foreach ($vol in @("C:", "D:", "E:", "F:")) {
    Write-Host "--- 保护器 $vol ---" -ForegroundColor Cyan
    $prot = (manage-bde -protectors -get $vol 2>&1 | Out-String)
    if ($prot -match "找不到|not found|错误|ERROR" -and $prot -notmatch "数字密码|Numerical Password|恢复密码|Recovery Password") {
        Write-Host "  (无可用信息)" -ForegroundColor DarkGray
        continue
    }
    $lines.Add("## $vol 保护器")
    $lines.Add($prot.TrimEnd())
    $lines.Add("")
    if ($prot -match "恢复密码|Recovery Password") { $found = $true }
}

# Get-BitLockerVolume 作为补充（家庭版设备加密同样可用）
try {
    $blv = Get-BitLockerVolume -ErrorAction Stop
    $lines.Add("## Get-BitLockerVolume")
    foreach ($v in $blv) {
        $lines.Add(("卷 {0} | 保护状态 {1} | 加密进度 {2}% | 加密方式 {3}" -f `
            $v.MountPoint, $v.ProtectionStatus, $v.EncryptionPercentage, $v.EncryptionMethod))
        foreach ($p in $v.KeyProtector) {
            $lines.Add(("  保护器 {0} | ID {1}" -f $p.KeyProtectorType, $p.KeyProtectorId))
            if ($p.RecoveryPassword) {
                $lines.Add(("  恢复密钥: {0}" -f $p.RecoveryPassword))
                $found = $true
            }
        }
    }
} catch {
    $lines.Add("## Get-BitLockerVolume 不可用: $($_.Exception.Message)")
}
$lines.Add("")

if (-not $found) {
    $lines.Add("## 结论：未发现恢复密码保护器（本机很可能未启用 BitLocker / 设备加密）。")
    $lines.Add("## 若已启用但此处为空，请到 https://account.microsoft.com/devices/recoverykey 查看（设备加密密钥随微软账户）。")
    Write-Host "[i] 未发现恢复密码保护器（本机可能未加密）" -ForegroundColor Yellow
} else {
    Write-Host "[OK] 已找到恢复密钥" -ForegroundColor Green
}

$dir = Split-Path -Parent $OutFile
if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
[System.IO.File]::WriteAllLines($OutFile, $lines, [System.Text.UTF8Encoding]::new($true))
Write-Host "[OK] 已写入 $OutFile（$($lines.Count) 行）" -ForegroundColor Green
Write-Host "[!] 该文件含敏感密钥，请勿提交 git / 勿上传网盘" -ForegroundColor Yellow
