# 归档搬运：复制 → 逐目录校验(文件数+总字节) → 删源 → 原路径建 junction（脚本/批处理零改动）
# 用法: pwsh -File tools\archive_move.ps1 -Src 'E:\wx\四巡','E:\wx\声音素材库' -Dst 'G:\王晰巡演素材存档'
param(
  [Parameter(Mandatory)][string[]]$Src,
  [Parameter(Mandatory)][string]$Dst,
  [switch]$NoJunction,
  [switch]$KeepSource   # 只复制不删源（纯备份，不释放 E 盘）
)
$ErrorActionPreference = 'Stop'
$log = 'D:\wx409.github.io\temp\archive_move.log'
New-Item -ItemType Directory -Force -Path $Dst | Out-Null
foreach ($s in $Src) {
  $name = Split-Path $s -Leaf
  $t = Join-Path $Dst $name
  if (-not (Test-Path $s)) { Write-Output "skip(源不存在): $s"; continue }
  if ((Get-Item $s).LinkType) { Write-Output "skip(已是链接): $s"; continue }
  New-Item -ItemType Directory -Force -Path $t | Out-Null
  robocopy $s $t /E /R:2 /W:2 /NFL /NDL /NP /NJH /LOG+:$log | Out-Null
  if ($LASTEXITCODE -ge 8) { Write-Output "✗ robocopy 失败($LASTEXITCODE)，保留源: $s"; continue }
  $a = Get-ChildItem $s -Recurse -File; $b = Get-ChildItem $t -Recurse -File
  $sa = ($a | Measure-Object Length -Sum).Sum; $sb = ($b | Measure-Object Length -Sum).Sum
  if ($a.Count -ne $b.Count -or $sa -ne $sb) {
    Write-Output "✗ 校验不符（源 $($a.Count)/$([math]::Round($sa/1GB,2))GB vs 目标 $($b.Count)/$([math]::Round($sb/1GB,2))GB），保留源: $s"
    continue
  }
  if ($KeepSource) {
    Write-Output ("✓ {0}: {1} 个 / {2:N2} GB → {3}（保留源，仅复制）" -f $name, $b.Count, ($sb / 1GB), $t)
    continue
  }
  Remove-Item $s -Recurse -Force
  if (-not $NoJunction) { New-Item -ItemType Junction -Path $s -Target $t | Out-Null }
  Write-Output ("✓ {0}: {1} 个 / {2:N2} GB → {3}{4}" -f $name, $b.Count, ($sb / 1GB), $t, $(if ($NoJunction) { '' } else { ' (原路径已建 junction)' }))
}
