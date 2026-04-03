$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Watcher doctor"
Write-Host "=============="

$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
  Write-Host "[OK] python found:" $python.Source
  python --version
} else {
  Write-Host "[ERR] python not found in PATH"
}

$requiredFiles = @(
  'linux_do_watcher.py',
  'config.example.json',
  'run_linux_do_watcher.ps1',
  'run_linux_do_reply_processor.ps1',
  'install_tasks.ps1'
)

foreach ($name in $requiredFiles) {
  $path = Join-Path $scriptDir $name
  if (Test-Path $path) {
    Write-Host "[OK]" $name
  } else {
    Write-Host "[ERR] Missing" $name
  }
}

$configPath = Join-Path $scriptDir 'config.json'
if (Test-Path $configPath) {
  Write-Host "[OK] config.json exists"
} else {
  Write-Host "[WARN] config.json missing. Copy config.example.json and fill credentials first."
}

foreach ($taskName in @('LinuxDoWatcher3H', 'LinuxDoReplyProcessor10M')) {
  $task = schtasks /Query /TN $taskName /V /FO LIST 2>$null
  if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] scheduled task exists:" $taskName
  } else {
    Write-Host "[WARN] scheduled task missing:" $taskName
  }
}
