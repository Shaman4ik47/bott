param(
  [string]$TaskName = "TelegramImageBot"
)

Write-Host "Removing Scheduled Task '$TaskName'..."

try {
  if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue | Out-Null
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false | Out-Null
    Write-Host "Task '$TaskName' removed."
  }
  else {
    Write-Host "Task '$TaskName' not found."
  }
}
catch {
  Write-Error $_
  exit 1
}

