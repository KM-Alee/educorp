# run-app.ps1
# EduCorp startup script for Windows
# Delegates to the orchestrated startup script.

$ErrorActionPreference = "Stop"
$Script:RootDir = $PSScriptRoot
Set-Location $RootDir

$cmd = Get-Command docker -ErrorAction SilentlyContinue
if (-not $cmd) { Write-Error "Missing required command: docker"; exit 1 }

& powershell -ExecutionPolicy Bypass -File "$RootDir\scripts\start-stack.ps1"
