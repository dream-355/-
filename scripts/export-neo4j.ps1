param(
    [string]$ContainerName = "neo4j-new",
    [string]$Image = "neo4j:5.26"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$BackupDir = Join-Path $ProjectRoot "neo4j_backup"

$info = docker inspect $ContainerName | ConvertFrom-Json
if (-not $info) {
    throw "Container not found: $ContainerName"
}

$dataMount = $info.Mounts | Where-Object { $_.Destination -eq "/data" } | Select-Object -First 1
if (-not $dataMount) {
    throw "The Neo4j container has no /data mount."
}
$dataSource = $dataMount.Source

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
$resolvedRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$resolvedBackup = (Resolve-Path -LiteralPath $BackupDir).Path
if (-not $resolvedBackup.StartsWith($resolvedRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Backup directory must be inside the project."
}

$wasRunning = $info.State.Running
Write-Host "Stopping Neo4j for export. It will restart automatically." -ForegroundColor Yellow
try {
    if ($wasRunning) {
        docker stop $ContainerName | Out-Null
    }
    docker run --rm `
        --entrypoint neo4j-admin `
        -v "${dataSource}:/data" `
        -v "${resolvedBackup}:/backups" `
        $Image database dump neo4j --to-path=/backups --overwrite-destination=true
    if ($LASTEXITCODE -ne 0) {
        throw "Neo4j export failed."
    }
}
finally {
    if ($wasRunning) {
        docker start $ContainerName | Out-Null
    }
}

$dump = Join-Path $BackupDir "neo4j.dump"
if (-not (Test-Path -LiteralPath $dump)) {
    throw "neo4j.dump was not created."
}
Write-Host "Export complete: $dump" -ForegroundColor Green
Write-Host "Upload this file to neo4j_backup on the server." -ForegroundColor Cyan

