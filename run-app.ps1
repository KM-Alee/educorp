# run-app.ps1
# EduCorp startup script for Windows

$ErrorActionPreference = "Stop"
$Script:RootDir = $PSScriptRoot
Set-Location $RootDir

$WebPid = $null

function Require-Command {
    param([string]$CommandName)
    $cmd = Get-Command $CommandName -ErrorAction SilentlyContinue
    if (-not $cmd) {
        Write-Error "Missing required command: $CommandName"
        exit 1
    }
}

function Wait-ForUrl {
    param(
        [string]$Url,
        [string]$Label,
        [int]$Attempts = 60,
        [int]$DelaySeconds = 2
    )

    for ($i = 1; $i -le $Attempts; $i++) {
        try {
            $response = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec 5 -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                Write-Host "$Label is ready"
                return
            }
        } catch {
            # Connection failed, keep waiting
        }
        Write-Host "Waiting for $Label ($i/$Attempts)"
        Start-Sleep -Seconds $DelaySeconds
    }

    Write-Error "$Label did not become ready: $Url"
}

function Cleanup {
    if ($WebPid -and -not $WebPid.HasExited) {
        Stop-Process -Id $WebPid.Id -Force -ErrorAction SilentlyContinue
    }
}

$null = Register-EngineEvent -Identifier ([System.Management.Automation.PsEngineEvent]::Exiting) -Action { Cleanup }
$null = Register-EngineEvent -Identifier ([System.Management.Automation.PsEngineEvent]::Stop) -Action { Cleanup }

# Check for required commands
$requiredCommands = @("docker", "make", "npm")
foreach ($cmd in $requiredCommands) {
    Require-Command $cmd
}

# Create .env if missing
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "Created .env from .env.example"
    }
}

Write-Host "Starting backend stack"
& "$RootDir\scripts\dev-setup.ps1"

Write-Host "Running database migrations"
make migrate

Write-Host "Waiting for gateway routes"
Wait-ForUrl -Url "http://localhost/api/v1/auth/health/ready" -Label "auth service"
Wait-ForUrl -Url "http://localhost/api/v1/courses/health/ready" -Label "course service"

# Install web dependencies if needed
if (-not (Test-Path "apps\web\node_modules")) {
    Write-Host "Installing web dependencies"
    npm --prefix apps/web install
}

Write-Host "Starting frontend dev server"
$webProcess = Start-Process -FilePath "npm" -ArgumentList "--prefix", "apps/web", "run", "dev", "--", "--host", "0.0.0.0" -PassThru -NoNewWindow
$WebPid = $webProcess

Write-Host ""
Write-Host "EduCorp is running"
Write-Host "Gateway:   http://localhost"
Write-Host "Frontend:  http://localhost:5173"
Write-Host "Traefik:   http://localhost:8081"
Write-Host "Grafana:   http://localhost:3000"
Write-Host "Temporal:  http://localhost:8088"
Write-Host "RabbitMQ:  http://localhost:15672"
Write-Host "MinIO:     http://localhost:9001"
Write-Host "Jaeger:    http://localhost:16686"
Write-Host ""
Write-Host "Press Ctrl+C to stop the frontend dev server. Docker services stay running until you call 'make down'."

$webProcess.WaitForExit()
