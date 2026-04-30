param(
    [string]$Url = $env:SUPABASE_URL,
    [string]$AnonKey = $(if ($env:SUPABASE_ANON_KEY) { $env:SUPABASE_ANON_KEY } else { $env:SUPABASE_KEY }),
    [string]$Endpoint = $(if ($env:SUPABASE_KEEPALIVE_ENDPOINT) { $env:SUPABASE_KEEPALIVE_ENDPOINT } else { "/auth/v1/health" }),
    [int]$Timeout = $(if ($env:SUPABASE_KEEPALIVE_TIMEOUT) { [int]$env:SUPABASE_KEEPALIVE_TIMEOUT } else { 10 }),
    [switch]$Json
)

$scriptPath = Join-Path $PSScriptRoot "supabase_keepalive.py"
$args = @(
    $scriptPath,
    "--url", $Url,
    "--anon-key", $AnonKey,
    "--endpoint", $Endpoint,
    "--timeout", $Timeout
)
if ($Json) {
    $args += "--json"
}

python @args
