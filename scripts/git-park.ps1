param(
    [Parameter(Position = 0)]
    [string]$Message = "parked work"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoRoot

$statusLines = git status --short
if ($LASTEXITCODE -ne 0) {
    throw "git status --short failed with exit code $LASTEXITCODE"
}

if (-not $statusLines) {
    Write-Host "Working tree is clean. Nothing to stash."
    exit 0
}

& git stash push -u -m $Message
if ($LASTEXITCODE -ne 0) {
    throw "git stash push failed with exit code $LASTEXITCODE"
}

Write-Host "[park] Stashed current work as: $Message"
