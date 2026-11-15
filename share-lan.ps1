$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

$ipconfigText = ipconfig
$addresses = [regex]::Matches($ipconfigText, "IPv4[^:]*:\s*([0-9.]+)") |
    ForEach-Object { $_.Groups[1].Value } |
    Where-Object {
        $_ -notlike "127.*" -and
        $_ -notlike "169.254.*" -and
        $_ -ne "172.17.48.1"
    }
$lanIp = $addresses | Where-Object { $_ -match "^192\.168\." } | Select-Object -First 1
if (-not $lanIp) {
    $lanIp = $addresses | Where-Object { $_ -match "^(10\.|172\.(1[6-9]|2[0-9]|3[01])\.)" } | Select-Object -First 1
}
if (-not $lanIp) {
    $lanIp = $addresses | Select-Object -First 1
}

Write-Host ""
Write-Host "  Zhi Heng Care - LAN Sharing" -ForegroundColor Green
if ($lanIp) {
    Write-Host "  Share this URL: http://${lanIp}:8000/?demo=1" -ForegroundColor Cyan
} else {
    Write-Host "  LAN address not detected. Run ipconfig to find IPv4." -ForegroundColor Yellow
}
Write-Host "  Local URL: http://127.0.0.1:8000/?demo=1" -ForegroundColor DarkCyan
Write-Host "  Visitors must use the same Wi-Fi / LAN." -ForegroundColor Gray
Write-Host "  Allow Python on the private network if Windows Firewall asks." -ForegroundColor Gray
Write-Host ""

python -c "import fastapi, uvicorn, neo4j, pydantic"
if ($LASTEXITCODE -ne 0) {
    throw "Python dependencies are missing. Run .\setup.ps1 first."
}

python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

