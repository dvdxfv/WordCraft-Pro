param(
    [string]$Url = $env:SUPABASE_URL,
    [string]$Key = $(if ($env:SUPABASE_SERVICE_ROLE_KEY) { $env:SUPABASE_SERVICE_ROLE_KEY } elseif ($env:SUPABASE_ANON_KEY) { $env:SUPABASE_ANON_KEY } else { $env:SUPABASE_KEY }),
    [double]$WarnDays = $(if ($env:SUPABASE_INACTIVITY_WARN_DAYS) { [double]$env:SUPABASE_INACTIVITY_WARN_DAYS } else { 6.0 }),
    [double]$CriticalDays = $(if ($env:SUPABASE_INACTIVITY_CRITICAL_DAYS) { [double]$env:SUPABASE_INACTIVITY_CRITICAL_DAYS } else { 6.9 }),
    [int]$Timeout = $(if ($env:SUPABASE_INACTIVITY_TIMEOUT) { [int]$env:SUPABASE_INACTIVITY_TIMEOUT } else { 12 }),
    [string]$WebhookUrl = $env:ALERT_WEBHOOK_URL,
    [switch]$Json
)

$scriptPath = Join-Path $PSScriptRoot "supabase_inactivity_watch.py"
$args = @(
    $scriptPath,
    "--url", $Url,
    "--key", $Key,
    "--warn-days", $WarnDays,
    "--critical-days", $CriticalDays,
    "--timeout", $Timeout
)
if ($WebhookUrl) {
    $args += @("--webhook-url", $WebhookUrl)
}
if ($Json) {
    $args += "--json"
}

python @args
