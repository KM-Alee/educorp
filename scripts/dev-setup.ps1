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

# 2. Build containers
Write-Host "Building containers..."
Invoke-NativeCommand -Command "docker" -Arguments @("compose", "build")

# 3. Start infrastructure
Write-Host "Starting all services..."
Invoke-NativeCommand -Command "docker" -Arguments @("compose", "up", "-d")

# 4. Wait for core infrastructure only
Write-Host "Waiting for core infrastructure services to become healthy..."
$monitoredServices = @("postgres", "mongodb", "redis", "qdrant", "minio", "kafka", "rabbitmq", "temporal")
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

# 5. Create Kafka topics
Write-Host "Creating Kafka topics..."
try {
    Invoke-NativeCommand -Command "docker" -Arguments @(
        "compose", "exec", "-T", "kafka", "bash", "/opt/kafka-topics.sh"
    )
} catch {
    Write-Host "Topics may already exist"
}

Write-Host ""
Write-Host "=== Setup Complete ==="
Write-Host "Services:   http://localhost (via Traefik)"
Write-Host "Grafana:    http://localhost:3000 (admin/admin)"
Write-Host "Temporal:   http://localhost:8088"
Write-Host "RabbitMQ:   http://localhost:15672 (educorp/educorp_dev)"
Write-Host "MinIO:      http://localhost:9001 (educorp/educorp_dev)"
Write-Host "Jaeger:     http://localhost:16686"
Write-Host "Traefik:    http://localhost:8081"
Write-Host "Schema Registry: http://localhost:8082"
