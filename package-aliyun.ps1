$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

$output = Join-Path $ProjectRoot "zhiheng-aliyun-2c4g-20261108.zip"
$items = @(
    ".dockerignore",
    ".env.aliyun.example",
    "ALIYUN-DEPLOY.md",
    "Caddyfile",
    "Dockerfile",
    "README.md",
    "backend",
    "docker-compose.https.yml",
    "docker-compose.ip.yml",
    "docker-compose.prod.yml",
    "docker-compose.trial.yml",
    "docs",
    "frontend",
    "neo4j_backup",
    "requirements.txt",
    "scripts"
)

Remove-Item -LiteralPath $output -Force -ErrorAction SilentlyContinue
& tar.exe -a -c -f $output `
    --exclude=__pycache__ `
    --exclude=*.pyc `
    --exclude=*.log `
    --exclude=*.png `
    --exclude=*.zip `
    --exclude=.env `
    --exclude=*.db `
    --exclude=*.db-shm `
    --exclude=*.db-wal `
    --exclude=vector_cache.pkl `
    --exclude=node_modules `
    @items
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create Aliyun package."
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [IO.Compression.ZipFile]::OpenRead($output)
try {
    $names = @($archive.Entries | ForEach-Object { $_.FullName })
} finally {
    $archive.Dispose()
}

$forbidden = @(
    ".env",
    "/.env",
    "data/qihuang.db",
    "data/zhiheng.db",
    "backups/",
    "server.log",
    ".git/"
)
foreach ($pattern in $forbidden) {
    $match = $names | Where-Object {
        $_ -eq $pattern -or $_.EndsWith($pattern)
    } | Select-Object -First 1
    if ($match) {
        throw "Forbidden file in package: $match"
    }
}
if (-not ($names -contains "neo4j_backup/neo4j.dump")) {
    throw "Neo4j dump is missing from package."
}
if (-not ($names -contains ".env.aliyun.example")) {
    throw "Aliyun environment template is missing from package."
}

$hash = Get-FileHash -Algorithm SHA256 -LiteralPath $output
$sizeMb = [math]::Round((Get-Item -LiteralPath $output).Length / 1MB, 2)
Write-Host "Package: $output"
Write-Host "SizeMB: $sizeMb"
Write-Host "SHA256: $($hash.Hash)"
