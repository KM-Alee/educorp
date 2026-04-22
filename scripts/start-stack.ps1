# scripts/start-stack.ps1 — EduCorp Orchestrated Startup for Windows
# PowerShell equivalent of scripts/start-stack.sh
#
# Usage: .\scripts\start-stack.ps1

$ErrorActionPreference = "Continue"
$Script:RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

$StartTime = Get-Date

# ─── Helpers ─────────────────────────────────────────────
function Write-Info  { param([string]$Msg) Write-Host "[INFO]  $Msg" -ForegroundColor Blue }
function Write-Ok    { param([string]$Msg) Write-Host "[ OK ]  $Msg" -ForegroundColor Green }
function Write-Warn  { param([string]$Msg) Write-Host "[WARN]  $Msg" -ForegroundColor Yellow }
function Write-Fail  { param([string]$Msg) Write-Host "[FAIL]  $Msg" -ForegroundColor Red }

function Get-Elapsed {
    $elapsed = (Get-Date) - $StartTime
    return "{0:N0}s" -f $elapsed.TotalSeconds
}

function Wait-ForHealthy {
    param(
        [string]$ServiceName,
        [int]$MaxWait = 90,
        [int]$Interval = 2
    )
    $elapsed = 0
    while ($elapsed -lt $MaxWait) {
        $cid = & docker compose ps -q $ServiceName 2>$null
        if (-not [string]::IsNullOrWhiteSpace($cid)) {
            $health = & docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}running{{end}}' $cid 2>$null
            if ($health -eq "healthy" -or $health -eq "running") { return $true }
            if ($health -eq "unhealthy") { return $false }
        }
        Start-Sleep -Seconds $Interval
        $elapsed += $Interval
    }
    return $false
}

function Wait-ForServices {
    param(
        [string[]]$Services,
        [int]$Timeout = 90
    )
    $jobs = @()
    foreach ($svc in $Services) {
        $jobs += Start-Job -ScriptBlock {
            param($s, $t, $dir)
            Set-Location $dir
            $elapsed = 0
            while ($elapsed -lt $t) {
                $cid = & docker compose ps -q $s 2>$null
                if (-not [string]::IsNullOrWhiteSpace($cid)) {
                    $h = & docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}running{{end}}' $cid 2>$null
                    if ($h -eq "healthy" -or $h -eq "running") { return @{Service=$s; Ok=$true} }
                    if ($h -eq "unhealthy") { return @{Service=$s; Ok=$false} }
                }
                Start-Sleep -Seconds 2
                $elapsed += 2
            }
            return @{Service=$s; Ok=$false}
        } -ArgumentList $svc, $Timeout, $PWD
    }

    $results = $jobs | Wait-Job | Receive-Job
    $jobs | Remove-Job -Force

    foreach ($r in $results) {
        if ($r -is [hashtable]) {
            if ($r.Ok) { Write-Ok "  $($r.Service) ready" }
            else       { Write-Warn "  $($r.Service) may not be healthy" }
        }
    }
}

function Run-Migration {
    param([string]$ServiceName)
    $container = "$ServiceName-service"
    $count = & docker compose exec -T $container sh -c "ls alembic/versions/*.py 2>/dev/null | wc -l" 2>$null
    if ([int]$count -gt 0) {
        Write-Info "  Migrating $ServiceName ($count files)..."
        & docker compose exec -T $container alembic upgrade head 2>&1 | Select-Object -Last 2
        Write-Ok "  $ServiceName migrations applied"
    } else {
        Write-Info "  ${ServiceName}: no migrations, skipping"
    }
}

# ─── Prerequisite checks ────────────────────────────────
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerCmd) { Write-Fail "Missing: docker"; exit 1 }

& docker info 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Fail "Docker daemon not running"; exit 1 }

# ─── .env setup ─────────────────────────────────────────
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Info "Created .env from .env.example"
    } else {
        Write-Fail "No .env or .env.example found"; exit 1
    }
}

# ══════════════════════════════════════════════════════════
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor White
Write-Host "  EduCorp Stack Startup (Windows)" -ForegroundColor White
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor White
Write-Host ""

# ── Phase 1: Core infrastructure ─────────────────────────
Write-Info "Phase 1/6: Core infrastructure..."
& docker compose up -d postgres mongodb redis qdrant minio traefik

Write-Info "Waiting for core services..."
Wait-ForServices -Services @("postgres", "mongodb", "redis", "qdrant", "minio") -Timeout 60
Write-Ok "Core infrastructure ready ($(Get-Elapsed))"

# ── Phase 2: Messaging ──────────────────────────────────
Write-Info "Phase 2/6: Messaging services..."
& docker compose --profile messaging up -d

Write-Info "Waiting for messaging..."
Wait-ForServices -Services @("kafka", "rabbitmq") -Timeout 90
Write-Ok "Messaging ready ($(Get-Elapsed))"

# ── Phase 3: Workflow engine ─────────────────────────────
Write-Info "Phase 3/6: Workflow engine..."
& docker compose --profile workflow up -d

Write-Info "Waiting for Temporal..."
if (Wait-ForHealthy -ServiceName "temporal" -MaxWait 90) {
    Write-Ok "Temporal ready ($(Get-Elapsed))"
} else {
    Write-Warn "Temporal may still be starting"
}

# ── Phase 4: Application services ───────────────────────
Write-Info "Phase 4/6: Application services..."
& docker compose --profile app up -d

Write-Info "Waiting for services to initialize..."
Start-Sleep -Seconds 8

# ── Phase 5: Migrations ─────────────────────────────────
Write-Info "Phase 5/6: Database migrations..."
foreach ($svc in @("auth", "course", "enrollment", "progress", "publishing", "notification", "analytics")) {
    Run-Migration -ServiceName $svc
}

# ── Phase 6: Seed + health ──────────────────────────────
Write-Info "Phase 6/6: Seeding data..."
& docker compose exec -T auth-service python -m scripts.seed 2>&1 | Select-Object -Last 3
Write-Ok "Auth admin seed complete"
& uv run python scripts/seed_data.py
Write-Ok "Seed data loaded"

Write-Host ""
Write-Info "Running health checks..."
Start-Sleep -Seconds 3

$healthy = 0; $total = 0
foreach ($svc in @("auth", "course", "enrollment", "progress", "publishing", "ai", "search", "notification", "analytics")) {
    $total++
    $endpoint = $svc
    switch ($svc) {
        "course"       { $endpoint = "courses" }
        "enrollment"   { $endpoint = "enrollments" }
        "notification" { $endpoint = "notifications" }
    }
    try {
        $r = Invoke-WebRequest -Uri "http://localhost/api/v1/$endpoint/health/ready" -TimeoutSec 3 -UseBasicParsing -ErrorAction SilentlyContinue
        $code = $r.StatusCode
    } catch { $code = 0 }

    if ($code -eq 200) {
        Write-Ok "  ${svc}: healthy"
        $healthy++
    } else {
        Write-Warn "  ${svc}: HTTP $code"
    }
}

$totalTime = Get-Elapsed
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor White
if ($healthy -eq $total) {
    Write-Host "  All $total services healthy ($totalTime)" -ForegroundColor Green
} else {
    Write-Host "  $healthy/$total services healthy ($totalTime)" -ForegroundColor Yellow
    Write-Host "  Run: .\make.ps1 health" -ForegroundColor Yellow
}
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor White
Write-Host ""
Write-Host "┌──────────────────┬──────────────────────────────────┐"
Write-Host "│  Service         │  URL                             │"
Write-Host "├──────────────────┼──────────────────────────────────┤"
Write-Host "│  Gateway         │  http://localhost                 │"
Write-Host "│  Frontend        │  http://localhost:5173            │"
Write-Host "│  Traefik Dash    │  http://localhost:8081            │"
Write-Host "│  Grafana         │  http://localhost:3000            │"
Write-Host "│  Temporal UI     │  http://localhost:8088            │"
Write-Host "│  RabbitMQ Mgmt   │  http://localhost:15672           │"
Write-Host "│  MinIO Console   │  http://localhost:9001            │"
Write-Host "│  Jaeger          │  http://localhost:16686           │"
Write-Host "│  Prometheus      │  http://localhost:9090            │"
Write-Host "│  Qdrant          │  http://localhost:6333            │"
Write-Host "│  Schema Registry │  http://localhost:8082            │"
Write-Host "└──────────────────┴──────────────────────────────────┘"
Write-Host ""
Write-Host "Commands:"
Write-Host "  .\make.ps1 logs                      # Tail all logs"
Write-Host "  .\make.ps1 logs -Service auth         # Tail specific service"
Write-Host "  .\make.ps1 health                     # Check service health"
Write-Host "  .\make.ps1 shell -Service auth         # Shell into service"
Write-Host "  .\make.ps1 debug-service -Service auth # Debug with debugpy"
Write-Host "  .\make.ps1 down                       # Stop everything"
Write-Host ""
