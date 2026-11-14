# Keep the recommender running, whatever happens: start it, and start it again if it ever exits.
#
#   powershell -ExecutionPolicy Bypass -File scripts\run_server.ps1            # answer live traffic
#   powershell -ExecutionPolicy Bypass -File scripts\run_server.ps1 -Standby   # load, then wait for the GO file
#
# Run it in its own window and leave that window open: the server then does not depend on any other program
# (editor, assistant session) staying alive. Only ONE server may answer at a time: to replace a running one
# without a gap use scripts\swap_server.ps1, which starts this with -Standby in a new window, waits until it
# is ready and hands over.
#
# Settings come from .env (TEAM_ID, RAWTREE_API_KEY, SKORE_DATA_DIR, SKORE_LOGS_DIR). The Python to use is
# $env:SKORE_PYTHON if set, else the venv next to the data directory, else "python".
param([switch]$Standby)

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo
$settings = @{}
Get-Content (Join-Path $repo ".env") | Where-Object { $_ -match "^\s*[A-Z_]+=" } | ForEach-Object {
    $name, $value = $_ -split "=", 2
    $settings[$name.Trim()] = $value.Trim()
}
$logs = if ($settings["SKORE_LOGS_DIR"]) { $settings["SKORE_LOGS_DIR"] } else { Join-Path $repo "logs" }
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$python = $env:SKORE_PYTHON
if (-not $python -and $settings["SKORE_DATA_DIR"]) {
    $candidate = Join-Path (Split-Path -Parent $settings["SKORE_DATA_DIR"]) "venv\Scripts\python.exe"
    if (Test-Path $candidate) { $python = $candidate }
}
if (-not $python) { $python = "python" }
$log = (Join-Path $logs "serve.log") -replace "/", "\"
$python = $python -replace "/", "\"
# the server writes its own log (--log): no shell redirection, so the file is plain UTF-8 on any PowerShell
$arguments = @("-u", "-m", "reco.serve", "--log", $log)
if ($Standby) { $arguments += "--standby" }

try { $Host.UI.RawUI.WindowTitle = "Skore Money recommender - leave this window open" } catch {}
Write-Host "recommender: $python $($arguments -join ' ')"
Write-Host "Leave this window open. To replace the server without a gap: scripts\swap_server.ps1"
while ($true) {
    & $python @arguments
    $code = $LASTEXITCODE
    Add-Content -Path $log -Encoding UTF8 -Value "$(Get-Date -Format 'HH:mm:ss') server exited with code $code - restarting in 2 s"
    Write-Host "$(Get-Date -Format 'HH:mm:ss') server exited ($code): restarting"
    $arguments = $arguments | Where-Object { $_ -ne "--standby" }   # after a crash nobody is there to give the GO
    Start-Sleep -Seconds 2
}
