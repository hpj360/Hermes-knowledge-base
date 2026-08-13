<#
.SYNOPSIS
    每日本地同步：拉取 GitHub Actions 生成的 API 数据快照并导入本地知识库。
.DESCRIPTION
    配合 .github/workflows/sync-data-sources.yml 使用。
    GitHub Actions 每日在海外服务器拉取 API 数据并提交为 JSON 快照，
    本脚本在本地执行 git pull + 导入快照 + 验证。
.NOTES
    建议通过 Windows 任务计划程序每日定时执行（如北京时间 09:00）。
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

Write-Log "=== 每日数据源同步开始 ==="

# 1. 拉取最新快照
Write-Log "步骤 1: git pull..."
git pull origin main 2>&1 | ForEach-Object { Write-Log $_ }

# 2. 导入同步快照（GitHub Actions 拉取的 API 数据）
Write-Log "步骤 2: 导入同步快照..."
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
        Write-Log "  导入 $source ..."
        uv run python scripts/harvest_external_data.py --source $source 2>&1 |
            ForEach-Object { Write-Log "    $_" }
    } else {
        Write-Log "  跳过 $source（快照文件不存在，GitHub Actions 可能尚未运行）"
    }
}

# 3. 导入手工策划快照（检查更新）
Write-Log "步骤 3: 导入策划快照（幂等）..."
$curatedSources = @(
    "wikipedia_snapshot",
    "who_alcohol",
    "oiv_stats",
    "niaaa_alcohol",
    "iba_official",
    "iwsr_summary"
)

foreach ($source in $curatedSources) {
    Write-Log "  检查 $source ..."
    uv run python scripts/harvest_external_data.py --source $source 2>&1 |
        Select-String "imported|skipped|error" |
        ForEach-Object { Write-Log "    $_" }
}

# 4. 验证
Write-Log "步骤 4: 数据源质量验证..."
uv run python scripts/_verify_data_sources.py 2>&1 |
    ForEach-Object { Write-Log "  $_" }

Write-Log "=== 每日数据源同步完成 ==="
