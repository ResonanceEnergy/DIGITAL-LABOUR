# Digital Labour Repository Setup and Build Script
# Clones and builds all portfolio repositories

param(
    [switch]$Force,
    [switch]$SkipBuild,
    [string]$Org = "ResonanceEnergy"
)

$BaseDir = "repos"
$LogFile = "repo_setup_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $LogEntry = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [$Level] $Message"
    Add-Content -Path $LogFile -Value $LogEntry
    Write-Host $LogEntry
}

function Test-GitRepo {
    param([string]$Path)
    return Test-Path (Join-Path $Path ".git")
}

function Clone-Repository {
    param([string]$Name, [string]$Visibility)

    $RepoPath = Join-Path $BaseDir $Name
    $RepoUrl = "https://github.com/$Org/$Name.git"

    Write-Log "Processing repository: $Name"

    if (Test-Path $RepoPath) {
        if ($Force) {
            Write-Log "Removing existing directory: $RepoPath" "WARN"
            Remove-Item -Recurse -Force $RepoPath
        }
        else {
            Write-Log "Repository already exists: $Name" "SKIP"
            return $true
        }
    }

    Write-Log "Cloning $Name from $RepoUrl"
    try {
        $cloneResult = git clone $RepoUrl $RepoPath 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Successfully cloned: $Name" "SUCCESS"
            return $true
        }
        else {
            Write-Log "Failed to clone $Name : $cloneResult" "ERROR"
            return $false
        }
    }
    catch {
        Write-Log "Exception cloning $Name : $($_.Exception.Message)" "ERROR"
        return $false
    }
}

function Build-Repository {
    param([string]$Name, [string]$RepoPath)

    Write-Log "Building repository: $Name"

    Push-Location $RepoPath

    try {
        # Check for build files
        $hasRequirements = Test-Path "requirements.txt"
        $hasSetupPy = Test-Path "setup.py"
        $hasPyproject = Test-Path "pyproject.toml"
        $hasPackageJson = Test-Path "package.json"
        $hasMakefile = Test-Path "Makefile"
        $hasCargoToml = Test-Path "Cargo.toml"
        $hasGoMod = Test-Path "go.mod"

        if ($hasRequirements -or $hasSetupPy -or $hasPyproject) {
            Write-Log "Detected Python project, installing dependencies"
            if (Test-Path "requirements.txt") {
                pip install -r requirements.txt
                if ($LASTEXITCODE -eq 0) {
                    Write-Log "Python dependencies installed for $Name" "SUCCESS"
                }
                else {
                    Write-Log "Failed to install Python dependencies for $Name" "WARN"
                }
            }
            if (Test-Path "setup.py") {
                python setup.py develop
                Write-Log "Python package installed in development mode for $Name" "SUCCESS"
            }
        }
        elseif ($hasPackageJson) {
            Write-Log "Detected Node.js project, installing dependencies"
            npm install
            if ($LASTEXITCODE -eq 0) {
                Write-Log "Node.js dependencies installed for $Name" "SUCCESS"
            }
            else {
                Write-Log "Failed to install Node.js dependencies for $Name" "WARN"
            }
        }
        elseif ($hasCargoToml) {
            Write-Log "Detected Rust project, building"
            cargo build --release
            if ($LASTEXITCODE -eq 0) {
                Write-Log "Rust project built for $Name" "SUCCESS"
            }
            else {
                Write-Log "Failed to build Rust project for $Name" "WARN"
            }
        }
        elseif ($hasGoMod) {
            Write-Log "Detected Go project, building"
            go build
            if ($LASTEXITCODE -eq 0) {
                Write-Log "Go project built for $Name" "SUCCESS"
            }
            else {
                Write-Log "Failed to build Go project for $Name" "WARN"
            }
        }
        elseif ($hasMakefile) {
            Write-Log "Detected Makefile, running build"
            make
            if ($LASTEXITCODE -eq 0) {
                Write-Log "Makefile build completed for $Name" "SUCCESS"
            }
            else {
                Write-Log "Failed to build with Makefile for $Name" "WARN"
            }
        }
        else {
            Write-Log "No build system detected for $Name" "INFO"
        }
    }
    catch {
        Write-Log "Exception during build of $Name : $($_.Exception.Message)" "ERROR"
    }
    finally {
        Pop-Location
    }
}

# Main execution
Write-Log "=== Digital Labour Repository Setup Started ==="
Write-Log "Organization: $Org"
Write-Log "Base Directory: $BaseDir"
Write-Log "Force Re-clone: $Force"
Write-Log "Skip Build: $SkipBuild"

# Create base directory
if (!(Test-Path $BaseDir)) {
    New-Item -ItemType Directory -Path $BaseDir | Out-Null
    Write-Log "Created base directory: $BaseDir"
}

# Read portfolio
$PortfolioPath = "portfolio.json"
if (!(Test-Path $PortfolioPath)) {
    Write-Log "Portfolio file not found: $PortfolioPath" "ERROR"
    exit 1
}

$Portfolio = Get-Content $PortfolioPath | ConvertFrom-Json
$TotalRepos = $Portfolio.repositories.Count
$ClonedCount = 0
$BuiltCount = 0

Write-Log "Found $TotalRepos repositories to process"

foreach ($repo in $Portfolio.repositories) {
    $name = $repo.name
    $visibility = $repo.visibility

    Write-Log "Processing $name (visibility: $visibility)"

    $cloned = Clone-Repository -Name $name -Visibility $visibility
    if ($cloned) {
        $ClonedCount++
        $repoPath = Join-Path $BaseDir $name

        if (!$SkipBuild) {
            Build-Repository -Name $name -RepoPath $repoPath
            $BuiltCount++
        }
    }
}

Write-Log "=== Repository Setup Complete ==="
Write-Log "Total Repositories: $TotalRepos"
Write-Log "Successfully Cloned: $ClonedCount"
Write-Log "Successfully Built: $BuiltCount"
Write-Log "Log file: $LogFile"

Write-Host ""
Write-Host "🎯 Repository Setup Summary:"
Write-Host "  • Total Repositories: $TotalRepos"
Write-Host "  • Successfully Cloned: $ClonedCount"
Write-Host "  • Successfully Built: $BuiltCount"
Write-Host "  • Log File: $LogFile"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Review the log file for any errors"
Write-Host "  2. Check individual repository directories in $BaseDir"
Write-Host "  3. Run the Digital Labour orchestration to monitor repositories"
