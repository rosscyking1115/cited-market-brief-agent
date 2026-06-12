$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$LogDir = Join-Path $RepoRoot ".data\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$Stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"
$LogFile = Join-Path $LogDir "scheduled-runner.log"

Add-Content -Path $LogFile -Value "[$Stamp] scheduled runner start"
Push-Location $RepoRoot
try {
  uv run --project backend python backend/scripts/run_scheduled.py 2>&1 |
    ForEach-Object { Add-Content -Path $LogFile -Encoding utf8 -Value $_ }
  Add-Content -Path $LogFile -Value "[$Stamp] scheduled runner complete"
} catch {
  Add-Content -Path $LogFile -Value "[$Stamp] scheduled runner failed: $($_.Exception.Message)"
  throw
} finally {
  Pop-Location
}
