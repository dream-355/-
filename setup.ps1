$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

python -m pip install --upgrade -r requirements.txt

if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot ".env"))) {
    Copy-Item -LiteralPath (Join-Path $ProjectRoot ".env.example") -Destination (Join-Path $ProjectRoot ".env")
    Write-Host "Created .env. Set NEO4J_PASSWORD and DEEPSEEK_API_KEY." -ForegroundColor Yellow
}

Write-Host "Dependencies installed. Run .\start.ps1 to launch." -ForegroundColor Green

