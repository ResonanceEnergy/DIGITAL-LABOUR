#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Second Brain Pipeline - Windows PowerShell equivalent of Makefile
    Golden Path for YouTube Drop + Second Brain Integration

.DESCRIPTION
    Replaces the Unix-dependent Makefile with cross-platform PowerShell.
    Stages: ingest -> enrich -> commit -> brief

.PARAMETER Action
    Pipeline action: all, ingest, enrich, commit, brief, status, clean

.PARAMETER URL
    YouTube video URL

.PARAMETER Model
    Ollama model to use for enrichment (default: llama2)

.EXAMPLE
    .\secondbrain.ps1 -Action all -URL "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    .\secondbrain.ps1 -Action ingest -URL "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    .\secondbrain.ps1 -Action enrich
    .\secondbrain.ps1 -Action status
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("all", "ingest", "enrich", "commit", "brief", "status", "clean")]
    [string]$Action,

    [Parameter(Mandatory = $false)]
    [string]$URL = "https://www.youtube.com/watch?v=0TpON5T-Sw4",

    [Parameter(Mandatory = $false)]
    [string]$Model = $null
)

# ============================================================================
# Configuration
# ============================================================================

$ErrorActionPreference = "Stop"
$REPO_ROOT = Split-Path -Parent $PSScriptRoot
$TOOLS_DIR = $PSScriptRoot
$PYTHON = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { "python3" }

# Extract video ID from URL
function Get-VideoId {
    param([string]$VideoUrl)
    if ($VideoUrl -match '[?&]v=([^&]+)') {
        return $Matches[1]
    }
    elseif ($VideoUrl -match 'youtu\.be/([^?]+)') {
        return $Matches[1]
    }
    return "unknown"
}

$VID = Get-VideoId -VideoUrl $URL
$DATE_PATH = Get-Date -Format "yyyy/MM"
$BASE_DIR = Join-Path $REPO_ROOT "knowledge" "secondbrain" $DATE_PATH $VID

# Resolve model
if (-not $Model) {
    $Model = if ($env:LOCAL_LLM_MODEL) { $env:LOCAL_LLM_MODEL } else { "llama2" }
}

# ============================================================================
# Stage 1: INGEST
# ============================================================================

function Invoke-Ingest {
    Write-Host "=== INGEST: $URL ===" -ForegroundColor Cyan
    
    # Create output directory
    New-Item -ItemType Directory -Path $BASE_DIR -Force | Out-Null
    
    # Run fetch.py
    $fetchScript = Join-Path $TOOLS_DIR "youtubedrop" "fetch.py"
    if (-not (Test-Path $fetchScript)) {
        Write-Error "fetch.py not found at $fetchScript"
        return $false
    }
    
    & $PYTHON $fetchScript $URL --out $BASE_DIR
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Ingest failed with exit code $LASTEXITCODE"
        return $false
    }
    
    $rawFile = Join-Path $BASE_DIR "raw.txt"
    if (-not (Test-Path $rawFile)) {
        Write-Error "ERROR: Transcript missing at $rawFile"
        return $false
    }
    
    $size = (Get-Item $rawFile).Length
    Write-Host "✓ Ingest complete: $BASE_DIR ($size bytes)" -ForegroundColor Green
    return $true
}

# ============================================================================
# Stage 2: ENRICH
# ============================================================================

function Invoke-Enrich {
    Write-Host "=== ENRICH: $VID ===" -ForegroundColor Cyan
    
    $enrichScript = Join-Path $TOOLS_DIR "enrich.py"
    if (-not (Test-Path $enrichScript)) {
        Write-Error "enrich.py not found at $enrichScript"
        return $false
    }
    
    # Check Ollama is running
    try {
        $ollamaCheck = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -ErrorAction Stop
        $models = $ollamaCheck.models | ForEach-Object { $_.name }
        if ($models -notcontains $Model -and $models -notcontains "$Model`:latest") {
            Write-Warning "Model '$Model' not found in Ollama. Available: $($models -join ', ')"
            Write-Warning "Pull it with: ollama pull $Model"
            return $false
        }
    }
    catch {
        Write-Error "Ollama not responding on port 11434. Start it with: ollama serve"
        return $false
    }
    
    # Set env vars for enrich.py
    $env:LOCAL_LLM_MODEL = $Model
    $env:LOCAL_LLM_URL = if ($env:LOCAL_LLM_URL) { $env:LOCAL_LLM_URL } else { "http://localhost:11434/api/generate" }
    
    & $PYTHON $enrichScript $BASE_DIR $VID $URL
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Enrichment failed with exit code $LASTEXITCODE"
        return $false
    }
    
    $enrichFile = Join-Path $BASE_DIR "enrich.json"
    if (Test-Path $enrichFile) {
        Write-Host "✓ Enrichment complete: $enrichFile" -ForegroundColor Green
        return $true
    }
    else {
        Write-Warning "Enrichment ran but enrich.json not found"
        return $false
    }
}

# ============================================================================
# Stage 3: CATALOG COMMIT
# ============================================================================

function Invoke-Commit {
    Write-Host "=== CATALOG COMMIT: $VID ===" -ForegroundColor Cyan
    
    $enrichJson = Join-Path $BASE_DIR "enrich.json"
    if (-not (Test-Path $enrichJson)) {
        Write-Error "enrich.json not found. Run 'enrich' first."
        return $false
    }
    
    $catalogScript = Join-Path $REPO_ROOT "agents" "ncl_catalog.py"
    if (-not (Test-Path $catalogScript)) {
        Write-Warning "ncl_catalog.py not found at $catalogScript — skipping catalog commit"
        return $true
    }
    
    Push-Location $REPO_ROOT
    try {
        & $PYTHON $catalogScript $enrichJson
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Catalog commit returned non-zero exit code: $LASTEXITCODE"
            return $false
        }
        Write-Host "✓ Catalog commit complete" -ForegroundColor Green
        return $true
    }
    finally {
        Pop-Location
    }
}

# ============================================================================
# Stage 4: OPS BRIEF
# ============================================================================

function Invoke-Brief {
    Write-Host "=== OPS BRIEF: $VID ===" -ForegroundColor Cyan
    
    $enrichJson = Join-Path $BASE_DIR "enrich.json"
    if (-not (Test-Path $enrichJson)) {
        Write-Error "enrich.json not found. Run 'enrich' first."
        return $false
    }
    
    $queueScript = Join-Path $TOOLS_DIR "queue_brief.py"
    if (-not (Test-Path $queueScript)) {
        Write-Warning "queue_brief.py not found — skipping brief queue"
        return $true
    }
    
    Push-Location $REPO_ROOT
    try {
        & $PYTHON $queueScript $enrichJson
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Brief queue returned non-zero exit code: $LASTEXITCODE"
            return $false
        }
        Write-Host "✓ Brief queued" -ForegroundColor Green
        return $true
    }
    finally {
        Pop-Location
    }
}

# ============================================================================
# Status & Clean
# ============================================================================

function Show-Status {
    Write-Host "=== SECOND BRAIN STATUS ===" -ForegroundColor Cyan
    Write-Host "Video ID:  $VID"
    Write-Host "Base dir:  $BASE_DIR"
    Write-Host "Model:     $Model"
    Write-Host "Python:    $PYTHON"
    Write-Host ""
    
    if (Test-Path $BASE_DIR) {
        Write-Host "Files present:" -ForegroundColor Yellow
        Get-ChildItem -Path $BASE_DIR -File | ForEach-Object {
            $sizeKB = [math]::Round($_.Length / 1024, 1)
            Write-Host "  $($_.Name) ($sizeKB KB) - Modified: $($_.LastWriteTime.ToString('yyyy-MM-dd HH:mm'))"
        }
    }
    else {
        Write-Host "  (directory not created yet)" -ForegroundColor DarkGray
    }
    
    # Check Ollama
    Write-Host ""
    Write-Host "Ollama Status:" -ForegroundColor Yellow
    try {
        $tags = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 3 -ErrorAction Stop
        $tags.models | ForEach-Object {
            $sizeGB = [math]::Round($_.size / 1GB, 2)
            Write-Host "  $($_.name) ($sizeGB GB)"
        }
    }
    catch {
        Write-Host "  Ollama not responding" -ForegroundColor Red
    }
    
    # Check knowledge directory
    Write-Host ""
    Write-Host "Knowledge Store:" -ForegroundColor Yellow
    $kbDir = Join-Path $REPO_ROOT "knowledge" "secondbrain"
    if (Test-Path $kbDir) {
        $count = (Get-ChildItem -Path $kbDir -Recurse -File -Filter "enrich.json" -ErrorAction SilentlyContinue).Count
        Write-Host "  $kbDir — $count enriched entries"
    }
    else {
        Write-Host "  $kbDir — not created yet" -ForegroundColor DarkGray
    }
}

function Invoke-Clean {
    Write-Host "=== CLEAN: $VID ===" -ForegroundColor Cyan
    if (Test-Path $BASE_DIR) {
        Remove-Item -Recurse -Force $BASE_DIR
        Write-Host "✓ Cleaned $BASE_DIR" -ForegroundColor Green
    }
    else {
        Write-Host "  Nothing to clean" -ForegroundColor DarkGray
    }
}

# ============================================================================
# Main Dispatch
# ============================================================================

Write-Host "╔══════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "║   SECOND BRAIN PIPELINE (Windows)    ║" -ForegroundColor Magenta
Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Magenta
Write-Host ""

switch ($Action) {
    "all" {
        $ok = Invoke-Ingest
        if ($ok) { $ok = Invoke-Enrich }
        if ($ok) { $ok = Invoke-Commit }
        if ($ok) { $ok = Invoke-Brief }
        if ($ok) {
            Write-Host ""
            Write-Host "═══ PIPELINE COMPLETE ═══" -ForegroundColor Green
        }
        else {
            Write-Host ""
            Write-Host "═══ PIPELINE STOPPED (see errors above) ═══" -ForegroundColor Red
        }
    }
    "ingest" { Invoke-Ingest }
    "enrich" { Invoke-Enrich }
    "commit" { Invoke-Commit }
    "brief" { Invoke-Brief }
    "status" { Show-Status }
    "clean" { Invoke-Clean }
}
