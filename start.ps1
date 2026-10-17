# ============================================================
# PlanetTerp Chatbot - Startup Script (PowerShell)
# Starts the API (port 8000), which also serves the MCP server at /mcp/
# Usage: .\start.ps1
# ============================================================

$backend = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "backend"

Write-Host ""
Write-Host "Starting PlanetTerp Chatbot..." -ForegroundColor Cyan
Write-Host "   Chat API   : http://127.0.0.1:8000/chat" -ForegroundColor Gray
Write-Host "   MCP server : http://127.0.0.1:8000/mcp/" -ForegroundColor Gray
Write-Host "   Frontend   : run 'npm run dev' in ./frontend" -ForegroundColor Gray
Write-Host ""

$env:PYTHONIOENCODING = "utf-8"
Push-Location $backend
try {
    py -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
} finally {
    Pop-Location
}
