Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "=== EduCorp Development Setup ==="

function Invoke-NativeCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Command,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        $joined = $Arguments -join " "
        throw "Command failed: $Command $joined"
    }
}

# 1. Copy .env if not exists
if (-not (Test-Path -Path ".env" -PathType Leaf)) {
    Copy-Item -Path ".env.example" -Destination ".env"
    Write-Host "Created .env from .env.example"
} else {
    Write-Host ".env already exists, skipping"
}

# 2. Build containers (with BuildKit)
Write-Host "Building containers..."
$env:DOCKER_BUILDKIT = "1"
Invoke-NativeCommand -Command "docker" -Arguments @("compose", "--profile", "full", "build")

# 3. Start full stack
Write-Host "Starting all services..."
Invoke-NativeCommand -Command "docker" -Arguments @("compose", "--profile", "full", "up", "-d")

# 4. Wait for core infrastructure only
Write-Host "Waiting for core infrastructure services to become healthy..."
$monitoredServices = @("postgres", "mongodb", "redis", "qdrant", "minio")
for ($i = 1; $i -le 60; $i++) {
    $healthy = 0
    $total = 0

    foreach ($service in $monitoredServices) {
        $total++
        $containerId = & docker compose ps -q $service 2>$null
        if ([string]::IsNullOrWhiteSpace($containerId)) {
            continue
        }

        $status = & docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' $containerId 2>$null
        if ($status -eq "healthy" -or $status -eq "running") {
            $healthy++
        }
    }

    Write-Host ("  Health check {0}/60: ~{1}/{2} healthy" -f $i, $healthy, $total)
    if ($healthy -ge $total -and $total -gt 0) {
        break
    }

    Start-Sleep -Seconds 5
}

Write-Host ""
Write-Host "=== Setup Complete ==="
Write-Host "Frontend:   http://localhost:5173"
Write-Host "API:        http://localhost (via Traefik)"
Write-Host "Grafana:    http://localhost:3000 (admin/admin)"
Write-Host "Temporal:   http://localhost:8088"
Write-Host "RabbitMQ:   http://localhost:15672 (educorp/educorp_dev)"
Write-Host "MinIO:      http://localhost:9001 (educorp/educorp_dev)"
Write-Host "Jaeger:     http://localhost:16686"
Write-Host "Traefik:    http://localhost:8081"
Write-Host "Schema Reg: http://localhost:8082"
Write-Host ""
Write-Host "Tip: Run '.\make.ps1 health' to check all service endpoints"
