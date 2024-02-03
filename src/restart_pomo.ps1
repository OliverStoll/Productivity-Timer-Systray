$process = Get-Process Pomo -ErrorAction SilentlyContinue
if ($process -eq $null) {
    Start-Process "C:\CODE\pomodoro-windows\dist\Pomo.exe"
}
