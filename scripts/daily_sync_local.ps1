<#
.SYNOPSIS
    Daily local sync: pull GitHub Actions API snapshots and import into local KB.
.DESCRIPTION
    Works with .github/workflows/sync-data-sources.yml.
    GitHub Actions fetches API data daily on overseas servers and commits JSON snapshots.
    This script runs locally: git pull + import snapshots + verify.
.NOTES
    Schedule via Windows Task Scheduler (e.g. 09:00 daily).
#>

param(
    [string]$RepoDir = "D:\Hermes\hermes-kb\hermes-knowledge-base"
)

Set-Location $RepoDir
$ErrorActionPreference = "Continue"
$logFile = Join-Path $RepoDir "logs\daily_sync.log"
$logDir = Split-Path $logFile -Parent
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

function Write-Log {
    param([string]$msg)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $msg"
    Write-Host $line
    Add-Content -Path $logFile -Value $line -Encoding UTF8
}

Write-Log "=== Daily Data Source Sync Start ==="

# 1. Pull latest snapshots
Write-Log "Step 1: git pull..."
git pull origin main 2>&1 | ForEach-Object { Write-Log $_ }

# 2. Import API sync snapshots (fetched by GitHub Actions)
Write-Log "Step 2: Import sync snapshots..."
$syncSources = @(
    "wikipedia_sync",
    "openfoodfacts_sync",
    "usda_fooddata_sync",
    "dbpedia_sync",
    "wikidata_sync",
    "crossref_sync"
)

foreach ($source in $syncSources) {
    $snapshotFile = Join-Path $RepoDir "data\sources\$source.json"
    if (Test-Path $snapshotFile) {
        Write-Log "  Importing $source ..."
        uv run python scripts/harvest_external_data.py --source $source 2>&1 |
            ForEach-Object { Write-Log "    $_" }
    } else {
        Write-Log "  Skip $source (snapshot not found, GitHub Actions may not have run yet)"
    }
}

# 3. Import curated snapshots (idempotent check for updates)
Write-Log "Step 3: Import curated snapshots (idempotent)..."
$curatedSources = @(
    "wikipedia_snapshot",
    "who_alcohol",
    "oiv_stats",
    "niaaa_alcohol",
    "iba_official",
    "iwsr_summary"
)

foreach ($source in $curatedSources) {
    Write-Log "  Check $source ..."
    uv run python scripts/harvest_external_data.py --source $source 2>&1 |
        Select-String "imported|skipped|error" |
        ForEach-Object { Write-Log "    $_" }
}

# 4. Verify
Write-Log "Step 4: Data source quality verification..."
uv run python scripts/_verify_data_sources.py 2>&1 |
    ForEach-Object { Write-Log "  $_" }

Write-Log "=== Daily Data Source Sync Complete ==="
