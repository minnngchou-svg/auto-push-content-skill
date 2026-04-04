param(
  [string]$WatcherTaskName = "LinuxDoWatcher3H",
  [string]$ReplyTaskName = "LinuxDoReplyProcessor1H",
  [string]$WatcherStartTime = "09:00",
  [string]$WatcherEndTime = "23:00",
  [int]$WatcherIntervalHours = 3,
  [string]$ReplyStartTime = "09:00",
  [string]$ReplyEndTime = "23:00",
  [int]$ReplyIntervalHours = 1
)

function Set-AcOnlyTaskSettings {
  param(
    [string]$TaskName
  )

  try {
    # Default power settings mean "do not start on battery" and
    # "stop if the machine switches to battery".
    $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 72)
    Set-ScheduledTask -TaskName $TaskName -Settings $settings | Out-Null
    Write-Host "Updated power settings for $TaskName"
  }
  catch {
    Write-Warning "Unable to update battery settings for ${TaskName}: $($_.Exception.Message)"
  }
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$watcherRunner = Join-Path $scriptDir "run_linux_do_watcher.ps1"
$replyRunner = Join-Path $scriptDir "run_linux_do_reply_processor.ps1"

Write-Host "Codex automations are now the default scheduler."
Write-Host "This script is kept as a legacy Windows fallback."
Write-Host ""

$watcherIntervalMinutes = $WatcherIntervalHours * 60
$replyIntervalMinutes = $ReplyIntervalHours * 60

schtasks /Create /SC MINUTE /MO $watcherIntervalMinutes /ST $WatcherStartTime /ET $WatcherEndTime /TN $WatcherTaskName /TR "powershell -WindowStyle Hidden -NonInteractive -ExecutionPolicy Bypass -File `"$watcherRunner`"" /F | Out-Host
schtasks /Create /SC MINUTE /MO $replyIntervalMinutes /ST $ReplyStartTime /ET $ReplyEndTime /TN $ReplyTaskName /TR "powershell -WindowStyle Hidden -NonInteractive -ExecutionPolicy Bypass -File `"$replyRunner`"" /F | Out-Host
Set-AcOnlyTaskSettings -TaskName $WatcherTaskName
Set-AcOnlyTaskSettings -TaskName $ReplyTaskName

Write-Host ""
Write-Host "Current task status:"
Write-Host "--------------------"
schtasks /Query /TN $WatcherTaskName /V /FO LIST | Out-Host
Write-Host ""
schtasks /Query /TN $ReplyTaskName /V /FO LIST | Out-Host
