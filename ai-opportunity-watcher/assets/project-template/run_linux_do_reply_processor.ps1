$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$logFile = Join-Path $scriptDir "reply_task.log"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"[$timestamp] starting reply processor" | Out-File -FilePath $logFile -Append -Encoding utf8

# Clear proxy variables that can hijack Python HTTP/IMAP requests into a dead local proxy.
foreach ($proxyVar in @("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "GIT_HTTP_PROXY", "GIT_HTTPS_PROXY", "http_proxy", "https_proxy", "all_proxy")) {
  Remove-Item -Path "Env:$proxyVar" -ErrorAction SilentlyContinue
}

try {
  $output = & python "$scriptDir\linux_do_watcher.py" --config "$scriptDir\config.json" --process-replies-only 2>&1
  $output | Out-File -FilePath $logFile -Append -Encoding utf8
}
catch {
  $_ | Out-File -FilePath $logFile -Append -Encoding utf8
  throw
}

"[$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")] reply processor finished" | Out-File -FilePath $logFile -Append -Encoding utf8
