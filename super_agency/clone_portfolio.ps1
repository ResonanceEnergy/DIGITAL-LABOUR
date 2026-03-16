#!/usr/bin/env pwsh
# Clone all portfolio repos from GitHub, preserving local .ncl and reports dirs
# Usage: pwsh clone_portfolio.ps1

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$reposDir = Join-Path $root "repos"
$portfolio = Get-Content (Join-Path $root "portfolio.json") | ConvertFrom-Json
$owner = "ResonanceEnergy"

$success = 0; $fail = 0; $skip = 0

foreach ($entry in $portfolio.repositories) {
    $repo = $entry.name
    $repoDir = Join-Path $reposDir $repo
    
    # Skip if already a real git clone
    if (Test-Path (Join-Path $repoDir ".git")) {
        Write-Host "[SKIP] $repo (already cloned)"
        $skip++
        continue
    }
    
    # Save local artifacts (.ncl, reports) if stub exists
    $tempSave = Join-Path $reposDir "_save_$repo"
    if (Test-Path $repoDir) {
        New-Item -ItemType Directory -Path $tempSave -Force | Out-Null
        
        $nclSrc = Join-Path $repoDir ".ncl"
        if (Test-Path $nclSrc) {
            Copy-Item $nclSrc (Join-Path $tempSave ".ncl") -Recurse -Force
        }
        
        $reportsSrc = Join-Path $repoDir "reports"
        if (Test-Path $reportsSrc) {
            Copy-Item $reportsSrc (Join-Path $tempSave "reports") -Recurse -Force
        }
        
        Remove-Item $repoDir -Recurse -Force
    }
    
    # Clone from GitHub
    Write-Host "[CLONE] $repo ... " -NoNewline
    $output = gh repo clone "$owner/$repo" $repoDir 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK"
        $success++
        
        # Restore saved artifacts
        if (Test-Path $tempSave) {
            $savedNcl = Join-Path $tempSave ".ncl"
            if (Test-Path $savedNcl) {
                Copy-Item $savedNcl $repoDir -Recurse -Force
            }
            $savedReports = Join-Path $tempSave "reports"
            if (Test-Path $savedReports) {
                Copy-Item $savedReports $repoDir -Recurse -Force
            }
            Remove-Item $tempSave -Recurse -Force
        }
    }
    else {
        Write-Host "FAILED ($output)"
        $fail++
        
        # Restore stub if clone failed
        if (Test-Path $tempSave) {
            New-Item -ItemType Directory -Path $repoDir -Force | Out-Null
            Get-ChildItem $tempSave | Copy-Item -Destination $repoDir -Recurse -Force
            Remove-Item $tempSave -Recurse -Force
        }
    }
}

Write-Host ""
Write-Host "=== CLONE SUMMARY ==="
Write-Host "Success: $success | Failed: $fail | Skipped: $skip | Total: $($portfolio.repositories.Count)"
