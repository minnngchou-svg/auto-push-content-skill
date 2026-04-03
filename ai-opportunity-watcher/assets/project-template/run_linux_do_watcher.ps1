$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$logFile = Join-Path $scriptDir "watcher_task.log"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"[$timestamp] starting watcher" | Out-File -FilePath $logFile -Append -Encoding utf8

try {
  $output = & python "$scriptDir\linux_do_watcher.py" --config "$scriptDir\config.json" 2>&1
  $output | Out-File -FilePath $logFile -Append -Encoding utf8
}
catch {
  $_ | Out-File -FilePath $logFile -Append -Encoding utf8
  throw
}

"[$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")] watcher finished" | Out-File -FilePath $logFile -Append -Encoding utf8
