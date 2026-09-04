# 一键设置：本地模型 + DSH 办公/编程
# 运行: powershell -ExecutionPolicy Bypass -File "D:\wx409.github.io\设置本地模型_DSH办公编程.ps1"
$ErrorActionPreference = 'Stop'

Write-Host "== 1/4 设置模型常驻内存（省加载时间） ==" -ForegroundColor Cyan
[Environment]::SetEnvironmentVariable('OLLAMA_KEEP_ALIVE', '4h', 'User')
$env:OLLAMA_KEEP_ALIVE = '4h'

Write-Host "== 2/4 拉取模型（已装的会自动跳过） ==" -ForegroundColor Cyan
ollama pull qwen2.5:7b
ollama pull qwen2.5-coder:7b
ollama pull qwen3:14b
ollama pull nomic-embed-text

Write-Host "== 3/4 创建 DSH 专用模型（短系统提示，省 token） ==" -ForegroundColor Cyan
$mf = @"
FROM qwen2.5:7b
PARAMETER num_ctx 8192
PARAMETER temperature 0.3
SYSTEM 你是DSH办公助手。中文回答，简洁准确。
"@
$mf | ollama create dsh-office -f -

$mf = @"
FROM qwen2.5-coder:7b
PARAMETER num_ctx 8192
PARAMETER temperature 0.2
SYSTEM 你是资深Python开发者。给可运行代码，中文注释，Windows兼容，用pathlib。
"@
$mf | ollama create dsh-code -f -

$mf = @"
FROM qwen3:14b
PARAMETER num_ctx 8192
PARAMETER temperature 0.6
SYSTEM 你是DSH高级助手。中文回答，深度准确。
"@
$mf | ollama create dsh-deep -f -

Write-Host "== 4/4 测试 ==" -ForegroundColor Cyan
ollama run dsh-office "用一句话介绍王晰"
ollama run dsh-code "用Python读取文件夹所有mp4并打印文件名"

Write-Host ""
Write-Host "== 完成 ==" -ForegroundColor Green
Write-Host "DSH 接口地址: http://127.0.0.1:11434/v1"
Write-Host "办公模型: dsh-office"
Write-Host "编程模型: dsh-code"
Write-Host "深度模型: dsh-deep"
Write-Host "嵌入模型: nomic-embed-text"
Write-Host ""
Write-Host "提示: 调用这些 dsh-* 模型时不要再发 system 提示词，系统提示已内置，省 token。"
