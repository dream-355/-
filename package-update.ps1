$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

$envPath = Join-Path $ProjectRoot ".env"
$deepseekLines = @()
if (Test-Path -LiteralPath $envPath) {
    $deepseekLines = Get-Content -Encoding UTF8 -LiteralPath $envPath |
        Where-Object { $_ -match '^DEEPSEEK_[A-Z0-9_]+=.+$' }
}
if ($deepseekLines.Count -eq 0) {
    throw "DeepSeek configuration was not found in .env."
}

$updateReadme = @(
    "# Update package",
    "",
    "This package does not contain or overwrite the server .env.",
    "",
    "- SMTP, Neo4j password, APP_SECRET, and public IP remain in the server .env.",
    "- DeepSeek settings are in server-config.env.fragment.",
    "- Extracting this package does not change email delivery.",
    "- Back up .env before replacing existing DEEPSEEK_* settings."
) -join "`r`n"

$configFile = Join-Path $ProjectRoot "server-config.env.fragment"
$readmeFile = Join-Path $ProjectRoot "UPDATE-README.md"
$output = Join-Path $ProjectRoot "zhiheng-app-update.zip"
$items = @(
    ".dockerignore",
    ".env.production.example",
    ".mcp.json.example",
    "UPDATE-README.md",
    "server-config.env.fragment",
    "backend",
    "frontend",
    "scripts",
    "Dockerfile",
    "requirements.txt",
    "docker-compose.prod.yml",
    "docker-compose.trial.yml",
    "docker-compose.ip.yml",
    "docker-compose.https.yml",
    "Caddyfile"
)

try {
    $utf8NoBom = [Text.UTF8Encoding]::new($false)
    [IO.File]::WriteAllText(
        $configFile,
        (($deepseekLines -join "`r`n") + "`r`n"),
        $utf8NoBom
    )
    [IO.File]::WriteAllText(
        $readmeFile,
        ($updateReadme + "`r`n"),
        $utf8NoBom
    )

    Remove-Item -LiteralPath $output -Force -ErrorAction SilentlyContinue
    & tar.exe -a -c -f $output `
        --exclude=__pycache__ `
        --exclude=*.pyc `
        --exclude=backend/data/vector_cache.pkl `
        @items
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create update package."
    }
} finally {
    Remove-Item -LiteralPath $configFile -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $readmeFile -Force -ErrorAction SilentlyContinue
}

$hash = Get-FileHash -Algorithm SHA256 -LiteralPath $output
$sizeMb = [math]::Round((Get-Item -LiteralPath $output).Length / 1MB, 2)

Write-Host "Update package: $output" -ForegroundColor Green
Write-Host "SizeMB: $sizeMb" -ForegroundColor Green
Write-Host "SHA256: $($hash.Hash)" -ForegroundColor Cyan

