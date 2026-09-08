#Requires -RunAsAdministrator
param (
    [string]$Username = "LocalSystem"
)

$ErrorActionPreference = "Stop"

# 1. Admin check
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "Please run PowerShell as Administrator!"
    exit 1
}

# 2. Dynamic path resolution
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
if (-not $scriptDir) { $scriptDir = $PSScriptRoot }
$projectRoot = Split-Path -Parent $scriptDir

$nssm = "C:\tools\nssm\nssm.exe"
$cloudflared = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$configYml = Join-Path $projectRoot "config\cloudflared\config.yml"
$dataDir = Join-Path $projectRoot "data"

if (-not (Test-Path $nssm)) { throw "NSSM not found: $nssm" }
if (-not (Test-Path $cloudflared)) { throw "Cloudflared not found: $cloudflared" }
if (-not (Test-Path $python)) { throw "Python not found: $python" }
if (-not (Test-Path $configYml)) { throw "Config not found: $configYml" }

if (-not (Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
}

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host " Using LocalSystem service account (No Password Needed)" -ForegroundColor Yellow
Write-Host " Isolated config and python venv are fully self-contained." -ForegroundColor Gray
Write-Host "======================================================" -ForegroundColor Cyan

# 3. Helper function
function Setup-NssmService {
    param (
        [string]$ServiceName,
        [string]$AppPath,
        [string]$AppParams,
        [string]$AppDir,
        [string]$DisplayName,
        [string]$StdoutPath,
        [string]$StderrPath,
        [string]$ExtraEnv = ""
    )

    Write-Host "`n[+] Configuring service: $ServiceName ..." -ForegroundColor Green

    $existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($existing) {
        if ($existing.Status -eq "Running") {
            Write-Host "  -> Stopping existing service $ServiceName..." -ForegroundColor Gray
            Stop-Service -Name $ServiceName -Force
        }
        Write-Host "  -> Removing existing service definition..." -ForegroundColor Gray
        & $nssm remove $ServiceName confirm | Out-Null
    }

    & $nssm install $ServiceName $AppPath | Out-Null
    & $nssm set $ServiceName AppParameters $AppParams | Out-Null
    & $nssm set $ServiceName AppDirectory $AppDir | Out-Null
    & $nssm set $ServiceName DisplayName $DisplayName | Out-Null
    & $nssm set $ServiceName ObjectName $Username | Out-Null
    & $nssm set $ServiceName Start SERVICE_DELAYED_AUTO_START | Out-Null
    & $nssm set $ServiceName AppRestartDelay 5000 | Out-Null
    & $nssm set $ServiceName AppExit Default Restart | Out-Null
    & $nssm set $ServiceName AppStdout $StdoutPath | Out-Null
    & $nssm set $ServiceName AppStderr $StderrPath | Out-Null
    & $nssm set $ServiceName AppStdoutCreationDisposition 4 | Out-Null
    & $nssm set $ServiceName AppStderrCreationDisposition 4 | Out-Null

    if ($ExtraEnv) {
        & $nssm set $ServiceName AppEnvironmentExtra $ExtraEnv | Out-Null
    }

    Write-Host "  -> Service $ServiceName configured successfully." -ForegroundColor Green
}

# 4. StudyTraceCloudflared
Setup-NssmService `
    -ServiceName "StudyTraceCloudflared" `
    -AppPath $cloudflared `
    -AppParams "--config `"$configYml`" tunnel run study-trace" `
    -AppDir $projectRoot `
    -DisplayName "StudyTrace Cloudflare Tunnel" `
    -StdoutPath (Join-Path $dataDir "cloudflared-stdout.log") `
    -StderrPath (Join-Path $dataDir "cloudflared-stderr.log")

# 5. StudyTrace (Backend)
Setup-NssmService `
    -ServiceName "StudyTrace" `
    -AppPath $python `
    -AppParams "run.py" `
    -AppDir $projectRoot `
    -DisplayName "StudyTrace Backend Server" `
    -StdoutPath (Join-Path $dataDir "studytrace-stdout.log") `
    -StderrPath (Join-Path $dataDir "studytrace-stderr.log") `
    -ExtraEnv "PYTHONUTF8=1"

# 6. Start services
Write-Host "`n[+] Starting services..." -ForegroundColor Cyan
Start-Service -Name StudyTraceCloudflared
Start-Service -Name StudyTrace

Start-Sleep -Seconds 3

# 7. Verification
Write-Host "`n================== Service Status ==================" -ForegroundColor Cyan
Get-Service StudyTraceCloudflared, StudyTrace | Format-Table Name, DisplayName, Status, StartType -AutoSize

Write-Host "================== Port & Health Check ==================" -ForegroundColor Cyan
$conn = Get-NetTCPConnection -LocalPort 28000 -ErrorAction SilentlyContinue
if ($conn) {
    Write-Host "[OK] Port 28000 is listening." -ForegroundColor Green
} else {
    Write-Host "[INFO] Port 28000 warming up..." -ForegroundColor Yellow
}

try {
    $res = Invoke-RestMethod -Uri "http://127.0.0.1:28000/api/health" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "[OK] Local Health check: $($res | ConvertTo-Json -Compress)" -ForegroundColor Green
} catch {
    Write-Host "[INFO] Local Health check warming up: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host "`nInstallation completed successfully! Autostart on boot is enabled." -ForegroundColor Green
