$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

Write-Host ""
Write-Host "  Zhi Heng Care Medical Intelligence" -ForegroundColor Green
Write-Host "  Web: http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "  Demo: http://127.0.0.1:8000/?demo=1" -ForegroundColor Cyan
Write-Host "  API: http://127.0.0.1:8000/docs" -ForegroundColor DarkCyan
Write-Host ""

python -c "import fastapi, uvicorn, neo4j, pydantic"
if ($LASTEXITCODE -ne 0) {
    throw "Python dependencies are missing. Run .\setup.ps1 first."
}

python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

