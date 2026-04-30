$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$webDir = Join-Path $repoRoot "web"
$logDir = Join-Path $repoRoot "artifacts\dev-start"
$backendStdout = Join-Path $logDir "backend.stdout.log"
$backendStderr = Join-Path $logDir "backend.stderr.log"
$frontendStdout = Join-Path $logDir "frontend.stdout.log"
$frontendStderr = Join-Path $logDir "frontend.stderr.log"

function Stop-PortProcess {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $connections) {
        return
    }

    $processIds = $connections | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($processId in $processIds) {
        if ($processId -gt 0) {
            try {
                Stop-Process -Id $processId -Force -ErrorAction Stop
                Write-Host "Freed port $Port by stopping PID $processId"
            } catch {
                Write-Warning "Failed to stop PID $processId on port ${Port}: $($_.Exception.Message)"
            }
        }
    }
}

function Test-PortListening {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return [bool]$conn
}

function Wait-ForPort {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port,
        [int]$TimeoutSeconds = 20
    )

    for ($i = 0; $i -lt $TimeoutSeconds; $i++) {
        if (Test-PortListening -Port $Port) {
            return $true
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Test-HttpReady {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [int]$TimeoutSeconds = 5
    )

    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec $TimeoutSeconds -UseBasicParsing -Proxy $null
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    } catch {
        return $false
    }
}

function Wait-ForHttp {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [int]$TimeoutSeconds = 20
    )

    for ($i = 0; $i -lt $TimeoutSeconds; $i++) {
        if (Test-HttpReady -Url $Url) {
            return $true
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Resolve-PythonLauncher {
    $candidates = @(
        @{ Label = "python"; ProbeExe = "python"; ProbeArgs = @() },
        @{ Label = "py -3.13"; ProbeExe = "py"; ProbeArgs = @("-3.13") },
        @{ Label = "py"; ProbeExe = "py"; ProbeArgs = @() }
    )

    foreach ($candidate in $candidates) {
        if (-not (Get-Command $candidate.ProbeExe -ErrorAction SilentlyContinue)) {
            continue
        }

        $previousErrorActionPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = "Continue"
            $output = & $candidate.ProbeExe @($candidate.ProbeArgs + @("-c", "import flask, sys; print(sys.executable)")) 2>$null
            if ($LASTEXITCODE -eq 0) {
                $pythonExe = ($output | Select-Object -Last 1).Trim()
                if ($pythonExe -and (Test-Path $pythonExe)) {
                    return [pscustomobject]@{
                        Display = $candidate.Label
                        FilePath = $pythonExe
                    }
                }
            }
        } finally {
            $ErrorActionPreference = $previousErrorActionPreference
        }
    }

    throw "No usable Python environment found with Flask installed. Please install Flask for python or py -3.13."
}

function Reset-LogFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (Test-Path $Path) {
        Remove-Item -LiteralPath $Path -Force
    }
    New-Item -ItemType File -Path $Path -Force | Out-Null
}

function Start-LoggedProcess {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [Parameter(Mandatory = $true)]
        [string]$WorkingDirectory,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,
        [Parameter(Mandatory = $true)]
        [string]$StdoutPath,
        [Parameter(Mandatory = $true)]
        [string]$StderrPath
    )

    $quotedFilePath = '"' + $FilePath + '"'
    $quotedWorkingDirectory = '"' + $WorkingDirectory + '"'
    $quotedStdoutPath = '"' + $StdoutPath + '"'
    $quotedStderrPath = '"' + $StderrPath + '"'
    $quotedArguments = $Arguments | ForEach-Object {
        if ($_ -match '\s') { '"' + $_ + '"' } else { $_ }
    }
    $commandLine = @(
        'cd /d', $quotedWorkingDirectory,
        '&& start "" /b', $quotedFilePath,
        ($quotedArguments -join ' '),
        "1>>$quotedStdoutPath",
        "2>>$quotedStderrPath"
    ) -join ' '

    $process = Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", $commandLine) -PassThru

    return [pscustomobject]@{
        Process = $process
    }
}

if (-not (Test-Path $webDir)) {
    throw "Cannot find web directory: $webDir"
}

New-Item -ItemType Directory -Path $logDir -Force | Out-Null
Reset-LogFile -Path $backendStdout
Reset-LogFile -Path $backendStderr
Reset-LogFile -Path $frontendStdout
Reset-LogFile -Path $frontendStderr

Stop-PortProcess -Port 5000
Stop-PortProcess -Port 8081

$launcher = Resolve-PythonLauncher

Write-Host "Using launcher: $($launcher.Display)"

$backendHandle = Start-LoggedProcess `
    -FilePath $launcher.FilePath `
    -WorkingDirectory $webDir `
    -Arguments @(".\flask_app.py") `
    -StdoutPath $backendStdout `
    -StderrPath $backendStderr

Start-Sleep -Seconds 1

$frontendHandle = Start-LoggedProcess `
    -FilePath $launcher.FilePath `
    -WorkingDirectory $webDir `
    -Arguments @(".\run_web.py") `
    -StdoutPath $frontendStdout `
    -StderrPath $frontendStderr

$backendReady = (Wait-ForPort -Port 5000 -TimeoutSeconds 20) -and (Wait-ForHttp -Url "http://127.0.0.1:5000/api/getSystemInfo" -TimeoutSeconds 20)
$frontendReady = (Wait-ForPort -Port 8081 -TimeoutSeconds 20) -and (Wait-ForHttp -Url "http://127.0.0.1:8081/" -TimeoutSeconds 20)

if (-not $backendReady -or -not $frontendReady) {
    $backendErrTail = (Get-Content -Path $backendStderr -Tail 20 -ErrorAction SilentlyContinue) -join "`n"
    $frontendErrTail = (Get-Content -Path $frontendStderr -Tail 20 -ErrorAction SilentlyContinue) -join "`n"
    throw @"
Startup incomplete: backend(5000)=$backendReady, frontend(8081)=$frontendReady
Backend PID: $($backendHandle.Process.Id)
Frontend PID: $($frontendHandle.Process.Id)
Backend stderr: $backendStderr
Frontend stderr: $frontendStderr
Backend stderr tail:
$backendErrTail
Frontend stderr tail:
$frontendErrTail
"@
}

Write-Host "Backend and frontend are ready."
Write-Host "Backend:  http://127.0.0.1:5000"
Write-Host "Frontend: http://127.0.0.1:8081/"
Write-Host "Backend PID: $($backendHandle.Process.Id)"
Write-Host "Frontend PID: $($frontendHandle.Process.Id)"
Write-Host "Logs: $logDir"
