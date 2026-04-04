$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
$automationRoot = Join-Path $codexHome 'automations'

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

$escapedWorkspace = $scriptDir -replace '\\', '\\\\'
$watcherAutomationFound = $false
$replyAutomationFound = $false

if (Test-Path $automationRoot) {
  $automationFiles = Get-ChildItem -Path $automationRoot -Recurse -Filter 'automation.toml' -ErrorAction SilentlyContinue
  foreach ($automationFile in $automationFiles) {
    $content = Get-Content $automationFile.FullName -Raw -ErrorAction SilentlyContinue
    if (-not $content) {
      continue
    }
    if ($content.Contains($escapedWorkspace) -and $content.Contains('run_linux_do_watcher.ps1')) {
      $watcherAutomationFound = $true
    }
    if ($content.Contains($escapedWorkspace) -and $content.Contains('run_linux_do_reply_processor.ps1')) {
      $replyAutomationFound = $true
    }
  }
}

if ($watcherAutomationFound) {
  Write-Host "[OK] Codex watcher automation exists for this workspace"
} else {
  Write-Host "[WARN] Codex watcher automation missing for this workspace"
}

if ($replyAutomationFound) {
  Write-Host "[OK] Codex reply automation exists for this workspace"
} else {
  Write-Host "[WARN] Codex reply automation missing for this workspace"
}

Write-Host ""
Write-Host "Legacy Windows fallback:"
foreach ($taskName in @('LinuxDoWatcher3H', 'LinuxDoReplyProcessor1H', 'LinuxDoReplyProcessor10M')) {
  $task = schtasks /Query /TN $taskName /V /FO LIST 2>$null
  if ($LASTEXITCODE -eq 0) {
    Write-Host "[INFO] Windows task exists:" $taskName
  }
}
