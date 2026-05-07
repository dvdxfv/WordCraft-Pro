# WordCraft Pro — NSSM 服务注册脚本
# 前置条件：已安装 NSSM（https://nssm.cc/download），nssm.exe 在 PATH 中
# 用法（管理员 PowerShell）：powershell -ExecutionPolicy Bypass -File .\scripts\install_service.ps1

$ServiceName  = "WordCraftFlask"
$ProjectRoot  = Split-Path $PSScriptRoot -Parent
$PythonExe    = (Get-Command python -ErrorAction Stop).Source
$LogDir       = Join-Path $ProjectRoot "logs"

# 确保日志目录存在
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

# 如已存在旧服务，先停止并移除
$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Output "检测到旧服务，正在移除..."
    nssm stop  $ServiceName
    nssm remove $ServiceName confirm
}

# 注册服务
nssm install   $ServiceName $PythonExe
nssm set       $ServiceName AppParameters   "-m waitress --host=127.0.0.1 --port=5000 web.flask_app:app"
nssm set       $ServiceName AppDirectory    $ProjectRoot
nssm set       $ServiceName AppEnvironmentExtra "PYTHONPATH=$ProjectRoot"
nssm set       $ServiceName DisplayName     "WordCraft Pro Flask Service"
nssm set       $ServiceName Description     "WordCraft Pro 后端 API 服务"
nssm set       $ServiceName Start           SERVICE_AUTO_START
nssm set       $ServiceName AppStdout       (Join-Path $LogDir "flask_stdout.log")
nssm set       $ServiceName AppStderr       (Join-Path $LogDir "flask_stderr.log")
nssm set       $ServiceName AppRotateFiles  1
nssm set       $ServiceName AppRotateBytes  10485760

# 启动
nssm start $ServiceName
Write-Output "服务 [$ServiceName] 已注册并启动，日志目录：$LogDir"
Write-Output "查看状态：Get-Service $ServiceName"
Write-Output "停止服务：nssm stop $ServiceName"
