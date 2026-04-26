# ============================================================
# PlanetTerp Navigator - Startup Script (PowerShell)
# Starts both the MCP sidecar (port 8001) and main API (port 8000)
# Usage: .\start.ps1
# ============================================================

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"

Write-Host ""
Write-Host "Starting PlanetTerp Navigator..." -ForegroundColor Cyan
Write-Host ""

# --- Start MCP HTTP sidecar on port 8001 ---
Write-Host "Starting MCP sidecar (port 8001)..." -ForegroundColor Yellow
$mcpJob = Start-Process -FilePath "py" `
    -ArgumentList "-m", "uvicorn", "planetterp_mcp.mcp_http_server:app", "--host", "127.0.0.1", "--port", "8001", "--reload" `
    -WorkingDirectory $backend `
    -PassThru `
    -NoNewWindow

Start-Sleep -Seconds 2

# --- Start main FastAPI backend on port 8000 ---
Write-Host "Starting main backend (port 8000)..." -ForegroundColor Yellow
$apiJob = Start-Process -FilePath "py" `
    -ArgumentList "-m", "uvicorn", "app.main_fast:app", "--host", "127.0.0.1", "--port", "8000", "--reload" `
    -WorkingDirectory $backend `
    -PassThru `
    -NoNewWindow

Write-Host ""
Write-Host "Both servers started!" -ForegroundColor Green
Write-Host "   MCP sidecar : http://127.0.0.1:8001" -ForegroundColor Gray
Write-Host "   Main API    : http://127.0.0.1:8000" -ForegroundColor Gray
Write-Host "   Frontend    : run 'npm run dev' in ./frontend" -ForegroundColor Gray
Write-Host ""
Write-Host "Press Ctrl+C to stop both servers." -ForegroundColor DarkGray
Write-Host ""

try {
    while ($true) { Start-Sleep -Seconds 5 }
} finally {
    Write-Host ""
    Write-Host "Shutting down servers..." -ForegroundColor Red
    if ($mcpJob -and !$mcpJob.HasExited) { Stop-Process -Id $mcpJob.Id -Force }
    if ($apiJob -and !$apiJob.HasExited) { Stop-Process -Id $apiJob.Id -Force }
}
