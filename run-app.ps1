# run-app.ps1
# EduCorp startup script for Windows

$ErrorActionPreference = "Stop"
$Script:RootDir = $PSScriptRoot
Set-Location $RootDir

function Require-Command {
    param([string]$CommandName)
    $cmd = Get-Command $CommandName -ErrorAction SilentlyContinue
    if (-not $cmd) {
        Write-Error "Missing required command: $CommandName"
        exit 1
    }
}

# Check for required commands
Require-Command "docker"
Require-Command "make"

# Create .env if missing
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "Created .env from .env.example"
    }
}

Write-Host "Starting EduCorp stack..."
docker compose up -d

Write-Host ""
Write-Host "EduCorp is running"
Write-Host ""
Write-Host "+---------------------------------------------------------+"
Write-Host "| Service         | URL                                  |"
Write-Host "+-----------------+--------------------------------------+"
Write-Host "| Gateway         | http://localhost                      |"
Write-Host "| Frontend       | http://localhost:5173                 |"
Write-Host "| Traefik        | http://localhost:8081                 |"
Write-Host "| Grafana        | http://localhost:3000                 |"
Write-Host "| Temporal UI    | http://localhost:8088                 |"
Write-Host "| RabbitMQ       | http://localhost:15672                |"
Write-Host "| MinIO          | http://localhost:9001                 |"
Write-Host "| Jaeger         | http://localhost:16686                |"
Write-Host "| Prometheus     | http://localhost:9090                 |"
Write-Host "| Qdrant         | http://localhost:6333                 |"
Write-Host "| Schema Reg.    | http://localhost:8082                 |"
Write-Host "+---------------------------------------------------------+"
Write-Host ""
Write-Host "Run 'docker compose logs -f' to view logs."
Write-Host "Run 'make down' to stop all services."
