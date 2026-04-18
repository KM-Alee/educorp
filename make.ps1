# make.ps1 - EduCorp Developer Shortcuts for Windows
# PowerShell equivalent of the Makefile
#
# Usage:
#   .\make.ps1 help              Show available commands
#   .\make.ps1 up                Start core infrastructure
#   .\make.ps1 up-full           Start everything
#   .\make.ps1 start             Full orchestrated startup
#   .\make.ps1 logs -Service auth Tail auth service logs
#   .\make.ps1 test -Service auth Run auth tests
#   .\make.ps1 debug-service -Service auth  Debug with debugpy

param(
    [Parameter(Position = 0)]
    [string]$Command = "help",

    [Alias("s")]
    [string]$Service = "",

    [Alias("m")]
    [string]$Msg = "",

    [string]$Cmd = ""
)

$ErrorActionPreference = "Continue"
$Script:RootDir = $PSScriptRoot
Set-Location $RootDir

$COMPOSE = "docker compose"
$SERVICES = @("auth", "course", "enrollment", "progress", "publishing", "ai", "search", "notification", "analytics")
$MIGRATE_SERVICES = @("auth", "course", "enrollment", "progress", "publishing", "notification", "analytics")

function Write-Color {
    param([string]$Text, [string]$Color = "White")
    Write-Host $Text -ForegroundColor $Color
}

function Invoke-Docker {
    param([string[]]$Arguments)
    $process = Start-Process -FilePath "docker" -ArgumentList $Arguments -NoNewWindow -Wait -PassThru
    return $process.ExitCode
}

# ---- Commands --------------------------------------------

function Show-Help {
    Write-Host ""
    Write-Color "EduCorp Developer Commands (Windows)" "Cyan"
    Write-Host ("-" * 50) -ForegroundColor DarkGray
    Write-Host ""

    $commands = @(
        @{ Name = "up";              Desc = "Start core infrastructure only (fast)" }
        @{ Name = "up-messaging";    Desc = "Start core + messaging (Kafka, RabbitMQ)" }
        @{ Name = "up-workflow";     Desc = "Start core + messaging + workflow (Temporal)" }
        @{ Name = "up-observability"; Desc = "Start core + observability" }
        @{ Name = "up-app";          Desc = "Start core + messaging + workflow + app" }
        @{ Name = "up-full";         Desc = "Start everything" }
        @{ Name = "start";           Desc = "Full orchestrated startup (recommended)" }
        @{ Name = "down";            Desc = "Stop all services" }
        @{ Name = "restart";         Desc = "Restart all or -Service <name>" }
        @{ Name = "logs";            Desc = "Tail logs, -Service <name> for specific" }
        @{ Name = "build";           Desc = "Build all service images" }
        @{ Name = "build-service";   Desc = "Build single -Service <name>" }
        @{ Name = "ps";              Desc = "Show container status" }
        @{ Name = "health";          Desc = "Check health of all services" }
        @{ Name = "migrate";         Desc = "Run all migrations" }
        @{ Name = "migrate-service"; Desc = "Run migration for -Service <name>" }
        @{ Name = "migrate-create";  Desc = "Create migration -Service <name> -Msg '...'" }
        @{ Name = "kafka-topics";    Desc = "Create Kafka topics" }
        @{ Name = "kafka-list";      Desc = "List Kafka topics" }
        @{ Name = "test";            Desc = "Run all tests (or -Service <name>)" }
        @{ Name = "test-coverage";   Desc = "Run tests with coverage -Service <name>" }
        @{ Name = "lint";            Desc = "Run linting (ruff + mypy)" }
        @{ Name = "fmt";             Desc = "Format code" }
        @{ Name = "seed";            Desc = "Seed development data" }
        @{ Name = "shell";           Desc = "Shell into -Service <name> container" }
        @{ Name = "debug-service";   Desc = "Start -Service with debugpy on port 5678" }
        @{ Name = "clean";           Desc = "Remove all containers and volumes" }
        @{ Name = "reset";           Desc = "Full reset: clean + rebuild + start" }
    )

    foreach ($cmd in $commands) {
        $name = $cmd.Name.PadRight(22)
        Write-Host "  " -NoNewline
        Write-Color $name "Green" -NoNewline
        Write-Host " $($cmd.Desc)"
    }
    Write-Host ""
}

function Start-Up {
    & docker compose up -d
}

function Start-UpMessaging {
    & docker compose --profile messaging up -d
}

function Start-UpWorkflow {
    & docker compose --profile messaging --profile workflow up -d
}

function Start-UpObservability {
    & docker compose --profile observability up -d
}

function Start-UpApp {
    & docker compose --profile messaging --profile workflow --profile app up -d
}

function Start-UpFull {
    & docker compose --profile full up -d
}

function Start-Orchestrated {
    if (Test-Path "scripts\start-stack.ps1") {
        & powershell -ExecutionPolicy Bypass -File "scripts\start-stack.ps1"
    } else {
        Write-Color "Running start-stack.sh via WSL/Git Bash..." "Yellow"
        & bash scripts/start-stack.sh
    }
}

function Stop-All {
    & docker compose --profile full down
}

function Restart-Services {
    if ($Service) {
        & docker compose restart "$Service-service"
    } else {
        & docker compose --profile full restart
    }
}

function Show-Logs {
    if ($Service) {
        & docker compose logs -f --tail=100 "$Service-service"
    } else {
        & docker compose --profile full logs -f --tail=50
    }
}

function Build-All {
    $env:DOCKER_BUILDKIT = "1"
    & docker compose --profile full build
}

function Build-One {
    if (-not $Service) { Write-Color "Usage: .\make.ps1 build-service -Service auth" "Red"; return }
    $env:DOCKER_BUILDKIT = "1"
    & docker compose build "$Service-service"
}

function Show-Status {
    & docker compose --profile full ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
}

function Check-Health {
    Write-Host ""
    $header = "{0,-22} {1,-10} {2}" -f "SERVICE", "STATUS", "RESPONSE"
    Write-Color $header "White"
    Write-Host ("-" * 50) -ForegroundColor DarkGray

    foreach ($svc in $SERVICES) {
        $endpoint = $svc
        switch ($svc) {
            "course"       { $endpoint = "courses" }
            "enrollment"   { $endpoint = "enrollments" }
            "notification" { $endpoint = "notifications" }
        }

        try {
            $response = Invoke-WebRequest -Uri "http://localhost/api/v1/$endpoint/health/ready" `
                -TimeoutSec 3 -UseBasicParsing -ErrorAction SilentlyContinue
            $code = $response.StatusCode
        } catch {
            $code = 0
        }

        if ($code -eq 200) {
            $line = "  {0,-20} " -f $svc
            Write-Host $line -NoNewline
            Write-Color "healthy    HTTP $code" "Green"
        } else {
            $line = "  {0,-20} " -f $svc
            Write-Host $line -NoNewline
            Write-Color "down       HTTP $code" "Red"
        }
    }
    Write-Host ""
}

function Run-Migrate {
    foreach ($svc in $MIGRATE_SERVICES) {
        $count = & docker compose exec -T "$svc-service" sh -c "ls alembic/versions/*.py 2>/dev/null | wc -l" 2>$null
        if ([int]$count -gt 0) {
            Write-Host "=== Migrating $svc ($count files) ==="
            & docker compose exec -T "$svc-service" alembic upgrade head
        } else {
            Write-Host "=== $svc`: no migrations, skipping ==="
        }
    }
}

function Run-MigrateService {
    if (-not $Service) { Write-Color "Usage: .\make.ps1 migrate-service -Service auth" "Red"; return }
    & docker compose exec "$Service-service" alembic upgrade head
}

function Run-MigrateCreate {
    if (-not $Service -or -not $Msg) {
        Write-Color "Usage: .\make.ps1 migrate-create -Service auth -Msg 'add users table'" "Red"; return
    }
    & docker compose exec "$Service-service" alembic revision --autogenerate -m "$Msg"
}

function Run-KafkaTopics {
    & docker compose exec kafka bash /opt/kafka-topics.sh
}

function Run-KafkaList {
    & docker compose exec kafka kafka-topics --bootstrap-server localhost:29092 --list
}

function Run-Tests {
    if ($Service) {
        & docker compose exec "$Service-service" pytest tests/ -v
    } else {
        foreach ($svc in $SERVICES) {
            Write-Host "=== Testing $svc ==="
            & docker compose exec -T "$svc-service" pytest tests/ -v --tb=short
        }
    }
}

function Run-TestCoverage {
    if (-not $Service) { Write-Color "Usage: .\make.ps1 test-coverage -Service auth" "Red"; return }
    & docker compose exec "$Service-service" pytest tests/ -v --cov=app --cov-report=term-missing
}

function Run-Lint {
    & uv run ruff check .
    & uv run mypy .
}

function Run-Fmt {
    & uv run ruff format .
    & uv run ruff check --fix .
}

function Run-Seed {
    & docker compose exec auth-service python -m scripts.seed
}

function Open-Shell {
    if (-not $Service) { Write-Color "Usage: .\make.ps1 shell -Service auth" "Red"; return }
    & docker compose exec "$Service-service" /bin/bash
}

function Run-DebugService {
    if (-not $Service) { Write-Color "Usage: .\make.ps1 debug-service -Service auth" "Red"; return }
    & docker compose stop "$Service-service" 2>$null
    & docker compose run --rm -p 5678:5678 --name "$Service-debug" `
        "$Service-service" python -m debugpy --listen 0.0.0.0:5678 --wait-for-client `
        -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
}

function Clean-All {
    & docker compose --profile full down -v --remove-orphans
}

function Reset-All {
    Clean-All
    Build-All
    Start-Orchestrated
}

# ---- Command dispatch ------------------------------------
switch ($Command.ToLower()) {
    "help"             { Show-Help }
    "up"               { Start-Up }
    "up-messaging"     { Start-UpMessaging }
    "up-workflow"      { Start-UpWorkflow }
    "up-observability" { Start-UpObservability }
    "up-app"           { Start-UpApp }
    "up-full"          { Start-UpFull }
    "start"            { Start-Orchestrated }
    "down"             { Stop-All }
    "restart"          { Restart-Services }
    "logs"             { Show-Logs }
    "build"            { Build-All }
    "build-service"    { Build-One }
    "ps"               { Show-Status }
    "health"           { Check-Health }
    "migrate"          { Run-Migrate }
    "migrate-service"  { Run-MigrateService }
    "migrate-create"   { Run-MigrateCreate }
    "kafka-topics"     { Run-KafkaTopics }
    "kafka-list"       { Run-KafkaList }
    "test"             { Run-Tests }
    "test-coverage"    { Run-TestCoverage }
    "lint"             { Run-Lint }
    "fmt"              { Run-Fmt }
    "seed"             { Run-Seed }
    "shell"            { Open-Shell }
    "debug-service"    { Run-DebugService }
    "clean"            { Clean-All }
    "reset"            { Reset-All }
    default {
        Write-Color "Unknown command: $Command" "Red"
        Write-Host "Run '.\make.ps1 help' for available commands."
    }
}
