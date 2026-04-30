param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Message,

    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

function Invoke-Git {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Args
    )

    & git @Args
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Args -join ' ') failed with exit code $LASTEXITCODE"
    }
}

function Invoke-TestCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Args
    )

    & py @Args
    if ($LASTEXITCODE -ne 0) {
        throw "py $($Args -join ' ') failed with exit code $LASTEXITCODE"
    }
}

Set-Location -LiteralPath $repoRoot

$statusLines = git status --short
if ($LASTEXITCODE -ne 0) {
    throw "git status --short failed with exit code $LASTEXITCODE"
}

if (-not $statusLines) {
    Write-Host "Working tree is clean. Nothing to checkpoint."
    exit 0
}

if (-not $SkipTests) {
    Write-Host "[checkpoint] Running tests/test_batch_regression.py ..."
    Invoke-TestCommand -Args @("-3.13", "-m", "pytest", "tests/test_batch_regression.py", "-v")

    Write-Host "[checkpoint] Running tests/test_format_checker.py ..."
    Invoke-TestCommand -Args @("-3.13", "-m", "pytest", "tests/test_format_checker.py", "-v")
}

Invoke-Git add -A

$stagedStatus = git diff --cached --name-only
if ($LASTEXITCODE -ne 0) {
    throw "git diff --cached --name-only failed with exit code $LASTEXITCODE"
}

if (-not $stagedStatus) {
    Write-Host "No staged changes after git add -A. Nothing to commit."
    exit 0
}

Invoke-Git commit -m $Message
Write-Host "[checkpoint] Commit created: $Message"
