param(
  [string]$WatcherTaskName = "LinuxDoWatcher3H",
  [string]$ReplyTaskName = "LinuxDoReplyProcessor10M",
  [string]$WatcherStartTime = "14:10",
  [int]$WatcherIntervalHours = 3,
  [int]$ReplyIntervalMinutes = 10
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$watcherRunner = Join-Path $scriptDir "run_linux_do_watcher.ps1"
$replyRunner = Join-Path $scriptDir "run_linux_do_reply_processor.ps1"

schtasks /Create /SC HOURLY /MO $WatcherIntervalHours /ST $WatcherStartTime /TN $WatcherTaskName /TR "powershell -ExecutionPolicy Bypass -File `"$watcherRunner`"" /F | Out-Host
schtasks /Create /SC MINUTE /MO $ReplyIntervalMinutes /ST 00:00 /TN $ReplyTaskName /TR "powershell -ExecutionPolicy Bypass -File `"$replyRunner`"" /F | Out-Host

Write-Host ""
Write-Host "Current task status:"
Write-Host "--------------------"
schtasks /Query /TN $WatcherTaskName /V /FO LIST | Out-Host
Write-Host ""
schtasks /Query /TN $ReplyTaskName /V /FO LIST | Out-Host
