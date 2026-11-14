# Replace the running recommender with a fresh one (new code, new ARMS, or just a clean process), without a gap:
#
#   powershell -ExecutionPolicy Bypass -File scripts\swap_server.ps1
#
# 1. starts a new server in standby in its own window (scripts\run_server.ps1 -Standby), created through
#    Windows itself so that it does not hang from whoever launched this script (a terminal, an editor, an
#    assistant session): closing those does not stop it
# 2. waits until it has loaded and checks its self-test: every arm must answer real requests with valid lists
# 3. only then stops the old server and gives the new one the GO; if anything is wrong the old one keeps answering
#
# Also the way to start the very first server: with none running, step 3 just gives the GO.
param([int]$WaitSeconds = 300)

$repo = Split-Path -Parent $PSScriptRoot
$settings = @{}
Get-Content (Join-Path $repo ".env") | Where-Object { $_ -match "^\s*[A-Z_]+=" } | ForEach-Object {
    $name, $value = $_ -split "=", 2
    $settings[$name.Trim()] = $value.Trim()
}
$logs = if ($settings["SKORE_LOGS_DIR"]) { $settings["SKORE_LOGS_DIR"] } else { Join-Path $repo "logs" }
$log = (Join-Path $logs "serve.log") -replace "/", "\"
$go = (Join-Path $logs "GO") -replace "/", "\"

function Servers { Get-CimInstance Win32_Process -Filter "Name like 'python%'" | Where-Object { $_.CommandLine -match 'reco\.serve' } }
function Wrappers { Get-CimInstance Win32_Process -Filter "Name like 'p%sh%.exe'" | Where-Object { $_.CommandLine -match 'run_server\.ps1' } }

$oldServers = @(Servers | ForEach-Object { $_.ProcessId })
$oldWrappers = @(Wrappers | ForEach-Object { $_.ProcessId })
$before = if (Test-Path $log) { (Get-Content $log).Count } else { 0 }

$command = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$(Join-Path $PSScriptRoot 'run_server.ps1')`" -Standby"
$created = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $command; CurrentDirectory = $repo }
if ($created.ReturnValue -ne 0) { Write-Host "could not start the new server (code $($created.ReturnValue)): nothing changed"; exit 1 }
Write-Host "new server starting in its own window (wrapper process $($created.ProcessId)); the old one keeps answering meanwhile"

$deadline = (Get-Date).AddSeconds($WaitSeconds)
$ready = $false
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 2
    $new = @(Get-Content $log | Select-Object -Skip $before)
    if ($new | Where-Object { $_ -match 'standby: ready' }) { $ready = $true; break }
}
$tests = @($new | Where-Object { $_ -match 'selftest \S+ .*: (\d+)/(\d+) valid' })
$wrong = @($tests | Where-Object { $_ -match ': (\d+)/(\d+) valid' -and $Matches[1] -ne $Matches[2] })
$failed = @($new | Where-Object { $_ -match 'selftest failed|Traceback|unavailable \(' })
if (-not $ready -or $tests.Count -eq 0 -or $wrong.Count -gt 0 -or $failed.Count -gt 0) {
    Write-Host "the new server is not fit to take over: stopping it, the old one keeps answering"
    $new | Where-Object { $_ -match 'selftest|Traceback|Error|unavailable' } | Select-Object -Last 12 | ForEach-Object { Write-Host "   $_" }
    Wrappers | Where-Object { $oldWrappers -notcontains $_.ProcessId } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Servers | Where-Object { $oldServers -notcontains $_.ProcessId } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    exit 1
}
Write-Host "new server ready, self-test clean ($($tests.Count) checks). Handing over."
# wrappers first: an old wrapper would restart the server we are about to stop
$oldWrappers | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
$oldServers | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
Start-Sleep -Milliseconds 300
$left = @(Servers | Where-Object { $oldServers -contains $_.ProcessId })
if ($left.Count -gt 0) { Write-Host "an old server is still alive ($($left.ProcessId -join ', ')): GO not given, stop it by hand and create $go"; exit 1 }
New-Item -ItemType File -Path $go -Force | Out-Null
Write-Host "GO given at $((Get-Date).ToUniversalTime().ToString('HH:mm:ss')) UTC. First minute of the new server:"
Start-Sleep -Seconds 65
Get-Content $log | Select-Object -Skip $before | Where-Object { $_ -match '^serving|answered=' } | Select-Object -Last 2 | ForEach-Object { Write-Host "   $($_.Substring(0, [Math]::Min(230, $_.Length)))" }
Write-Host "Healthy = answered grows by about 180 per minute, failed_polls and failed_inserts stay near 0."
