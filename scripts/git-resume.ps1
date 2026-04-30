param(
    [switch]$ListOnly,
    [string]$StashRef
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoRoot

$stashList = git stash list
if ($LASTEXITCODE -ne 0) {
    throw "git stash list failed with exit code $LASTEXITCODE"
}

if (-not $stashList) {
    Write-Host "No stashes available."
    exit 0
}

if ($ListOnly) {
    $stashList
    exit 0
}

if (-not $StashRef) {
    $StashRef = "stash@{0}"
}

& git stash pop $StashRef
if ($LASTEXITCODE -ne 0) {
    throw "git stash pop $StashRef failed with exit code $LASTEXITCODE"
}

Write-Host "[resume] Restored: $StashRef"
