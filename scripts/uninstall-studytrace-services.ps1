#Requires -RunAsAdministrator

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "Please run PowerShell as Administrator!"
    exit 1
}

$nssm = "C:\tools\nssm\nssm.exe"
$services = @("StudyTraceCloudflared", "StudyTrace")

foreach ($s in $services) {
    $svc = Get-Service -Name $s -ErrorAction SilentlyContinue
    if ($svc) {
        Write-Host "Stopping service: $s ..." -ForegroundColor Yellow
        Stop-Service -Name $s -Force -ErrorAction SilentlyContinue
        Write-Host "Removing service: $s ..." -ForegroundColor Yellow
        & $nssm remove $s confirm | Out-Null
        Write-Host "Removed: $s" -ForegroundColor Green
    } else {
        Write-Host "Service not found, skipping: $s" -ForegroundColor Gray
    }
}

Write-Host "Uninstallation completed successfully." -ForegroundColor Green
