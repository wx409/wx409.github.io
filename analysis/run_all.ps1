# 一键重算：build → 面板 → 事件研究 → 敏感性 → 曲线 → 唱功 → 页面数据
# 用法：pwsh -File D:\wx409.github.io\analysis\run_all.ps1
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$env:PYTHONIOENCODING = 'utf-8'
$env:MPLCONFIGDIR = 'D:\wx409.github.io\analysis\.mplcache'

$root = 'D:\wx409.github.io\analysis'
$py = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { throw "缺 venv：$py（先按 ANALYSIS.md 第五节创建）" }

$steps = @(
    'build.py',
    'build_panel_raw.py',
    'stats_did.py',
    'stats_sensitivity.py',
    'curve_did.py',
    'vocal_stats.py',
    'vocal_live.py',
    'vocal_build.py',
    'make_assets.py',
    'render_claims.py'
)

$sw = [Diagnostics.Stopwatch]::StartNew()
foreach ($s in $steps) {
    Write-Host "== $s" -ForegroundColor Cyan
    & $py (Join-Path $root $s)
    if ($LASTEXITCODE -ne 0) { throw "$s 失败（exit $LASTEXITCODE）" }
}

# python 进程写不进 dashboard/（ACL），由 PowerShell 复制产物
# python 进程写不进 dashboard/（ACL）：产物在 out/，由 PowerShell 复制
Copy-Item (Join-Path $root 'out\stats-v2.json')          'D:\wx409.github.io\dashboard\stats-v2.json' -Force
Copy-Item (Join-Path $root 'out\vocal_claims.min.json')  'D:\wx409.github.io\dashboard\vocal_claims.json' -Force
Copy-Item (Join-Path $root 'page_template.html')         'D:\wx409.github.io\dashboard\analysis-v2.html' -Force
$sw.Stop()
Write-Host ("完成，用时 {0:N1}s → dashboard\stats-v2.json" -f $sw.Elapsed.TotalSeconds) -ForegroundColor Green
