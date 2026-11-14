# Keep the recommender running, whatever happens: start it, and start it again if it ever exits.
#
#   powershell -ExecutionPolicy Bypass -File scripts\run_server.ps1            # answer live traffic
#   powershell -ExecutionPolicy Bypass -File scripts\run_server.ps1 -Standby   # load, then wait for the GO file
#
# Run it in its own PowerShell window and leave that window open: the server then does not depend on any
# other program (editor, assistant session) staying alive. Only ONE server may answer at a time: to replace a
# running one without a gap, start this with -Standby, wait for "standby: ready" in the log, stop the old
# window (Ctrl+C), and create the GO file it names.
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
$log = Join-Path $logs "serve.log"
$mode = if ($Standby) { "--standby" } else { "" }

Write-Host "recommender: $python -m reco.serve $mode   (log: $log)"
while ($true) {
    & $python -u -m reco.serve $mode *>> $log
    Add-Content $log "$(Get-Date -Format 'HH:mm:ss') server exited with code $LASTEXITCODE - restarting in 2 s"
    Write-Host "$(Get-Date -Format 'HH:mm:ss') server exited ($LASTEXITCODE): restarting"
    $mode = ""          # after a crash there is nobody to give the GO: answer straight away
    Start-Sleep -Seconds 2
}
