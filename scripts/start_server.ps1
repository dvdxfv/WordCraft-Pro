# WordCraft Pro — 生产启动脚本（waitress）
# 用法：powershell -ExecutionPolicy Bypass -File .\scripts\start_server.ps1

$ProjectRoot = Split-Path $PSScriptRoot -Parent

# 加载 .env（如存在）
$envFile = Join-Path $ProjectRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#=]+?)\s*=\s*(.*)\s*$') {
            [System.Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], 'Process')
        }
    }
    Write-Output "[start] 已加载 .env"
}

$port = if ($env:PORT) { $env:PORT } else { "5000" }

Set-Location $ProjectRoot
Write-Output "[start] 启动 waitress，监听 127.0.0.1:$port ..."
waitress-serve --host=127.0.0.1 --port=$port web.flask_app:app
