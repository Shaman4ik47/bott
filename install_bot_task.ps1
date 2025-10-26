param(
  [string]$TaskName = "TelegramImageBot",
  [switch]$RunNow
)

Write-Host "Installing Scheduled Task '$TaskName' for autostart..."

$projectDir = Split-Path -Parent $PSCommandPath
$batPath = Join-Path $projectDir 'run_bot.bat'

if (-not (Test-Path $batPath)) {
  Write-Error "Launcher not found: $batPath"
  exit 1
}

$tokenPath = Join-Path $projectDir 'BOT_TOKEN.txt'
if (-not (Test-Path $tokenPath)) {
  Write-Warning "BOT_TOKEN.txt not found. Create it with your Telegram bot token (single line)."
}

# Create action with working directory so logs write to project folder
$action   = New-ScheduledTaskAction -Execute $batPath -WorkingDirectory $projectDir
$trigger  = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet `
  -StartWhenAvailable `
  -MultipleInstances IgnoreNew `
  -RestartCount 3 `
  -RestartInterval (New-TimeSpan -Minutes 1)

# Run as SYSTEM with highest privileges so it starts without login
$principal = New-ScheduledTaskPrincipal -UserId 'NT AUTHORITY\SYSTEM' -RunLevel Highest

try {
  Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
  Write-Host "Task '$TaskName' installed."
  if ($RunNow.IsPresent) {
    Start-ScheduledTask -TaskName $TaskName
    Write-Host "Task '$TaskName' started."
  }
}
catch {
  Write-Error $_
  exit 1
}

