# Digital Labour Mobile Test Script
# Verify PWA functionality and mobile interface

param(
    [string]$MacIP = "localhost",
    [switch]$FullTest,
    [switch]$PWATest,
    [switch]$PerformanceTest
)

# Colors for PowerShell
$Colors = @{
    Red = [ConsoleColor]::Red
    Green = [ConsoleColor]::Green
    Yellow = [ConsoleColor]::Yellow
    Blue = [ConsoleColor]::Blue
    Magenta = [ConsoleColor]::Magenta
    Cyan = [ConsoleColor]::Cyan
    White = [ConsoleColor]::White
}

function Write-Info {
    param([string]$Message)
    Write-Host "[$((Get-Date).ToString('HH:mm:ss'))] INFO: $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[$((Get-Date).ToString('HH:mm:ss'))] SUCCESS: $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[$((Get-Date).ToString('HH:mm:ss'))] WARNING: $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[$((Get-Date).ToString('HH:mm:ss'))] ERROR: $Message" -ForegroundColor Red
}

function Test-WebEndpoint {
    param([string]$Url, [string]$Name)

    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec 10 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Success "$Name accessible"
            return $true
        } else {
            Write-Warning "$Name returned status $($response.StatusCode)"
            return $false
        }
    } catch {
        Write-Error "$Name unreachable: $($_.Exception.Message)"
        return $false
    }
}

function Test-APIEndpoint {
    param([string]$Url, [string]$Name)

    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec 10 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $content = $response.Content | ConvertFrom-Json
            Write-Success "$Name API functional"
            return $content
        } else {
            Write-Warning "$Name API returned status $($response.StatusCode)"
            return $null
        }
    } catch {
        Write-Error "$Name API error: $($_.Exception.Message)"
        return $null
    }
}

function Test-PWAFeatures {
    param([string]$BaseUrl)

    Write-Info "Testing PWA features..."

    # Test manifest
    $manifestUrl = "$BaseUrl/static/manifest.json"
    try {
        $response = Invoke-WebRequest -Uri $manifestUrl -TimeoutSec 5
        $manifest = $response.Content | ConvertFrom-Json
        Write-Success "PWA manifest valid"
        Write-Info "  App name: $($manifest.name)"
        Write-Info "  Theme color: $($manifest.theme_color)"
    } catch {
        Write-Error "PWA manifest error: $($_.Exception.Message)"
    }

    # Test service worker
    $swUrl = "$BaseUrl/static/sw.js"
    try {
        $response = Invoke-WebRequest -Uri $swUrl -TimeoutSec 5
        Write-Success "Service worker accessible"
    } catch {
        Write-Error "Service worker error: $($_.Exception.Message)"
    }

    # Test main interface
    $mainUrl = "$BaseUrl/"
    try {
        $response = Invoke-WebRequest -Uri $mainUrl -TimeoutSec 10
        if ($response.Content -match "Digital Labour Command") {
            Write-Success "Mobile interface loaded"
        } else {
            Write-Warning "Mobile interface content unexpected"
        }
    } catch {
        Write-Error "Mobile interface error: $($_.Exception.Message)"
    }
}

function Test-MobileCommands {
    param([string]$BaseUrl)

    Write-Info "Testing mobile commands..."

    $commands = @(
        "max_cpu_light",
        "deploy_agents_light",
        "intelligence_light",
        "backup_light"
    )

    foreach ($command in $commands) {
        $url = "$BaseUrl/api/command/$command"
        try {
            $response = Invoke-WebRequest -Uri $url -Method GET -TimeoutSec 15
            $result = $response.Content | ConvertFrom-Json
            if ($result.status -eq "executed") {
                Write-Success "Command '$command' executed"
            } else {
                Write-Warning "Command '$command' failed: $($result.error)"
            }
        } catch {
            Write-Error "Command '$command' error: $($_.Exception.Message)"
        }
    }
}

function Test-Performance {
    param([string]$BaseUrl)

    Write-Info "Testing performance..."

    # Test page load time
    $startTime = Get-Date
    try {
        $response = Invoke-WebRequest -Uri "$BaseUrl/" -TimeoutSec 30
        $loadTime = ((Get-Date) - $startTime).TotalSeconds
        if ($loadTime -lt 5) {
            Write-Success "Page load time: $([math]::Round($loadTime, 2))s (excellent)"
        } elseif ($loadTime -lt 10) {
            Write-Success "Page load time: $([math]::Round($loadTime, 2))s (good)"
        } else {
            Write-Warning "Page load time: $([math]::Round($loadTime, 2))s (slow)"
        }
    } catch {
        Write-Error "Performance test failed: $($_.Exception.Message)"
    }

    # Test API response time
    $startTime = Get-Date
    try {
        $response = Invoke-WebRequest -Uri "$BaseUrl/api/status" -TimeoutSec 10
        $apiTime = ((Get-Date) - $startTime).TotalSeconds
        if ($apiTime -lt 1) {
            Write-Success "API response time: $([math]::Round($apiTime, 2))s (excellent)"
        } elseif ($apiTime -lt 3) {
            Write-Success "API response time: $([math]::Round($apiTime, 2))s (good)"
        } else {
            Write-Warning "API response time: $([math]::Round($apiTime, 2))s (slow)"
        }
    } catch {
        Write-Error "API performance test failed: $($_.Exception.Message)"
    }
}

function Show-MobileInstructions {
    Write-Host ""
    Write-Host "📱 MOBILE TESTING INSTRUCTIONS:" -ForegroundColor Cyan
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "iPhone/iPad Setup:" -ForegroundColor White
    Write-Host "1. Open Safari on your device" -ForegroundColor White
    Write-Host "2. Go to: http://$MacIP`:8080" -ForegroundColor White
    Write-Host "3. Tap the share button (📤)" -ForegroundColor White
    Write-Host "4. Select 'Add to Home Screen'" -ForegroundColor White
    Write-Host "5. Name it 'Digital Labour Command'" -ForegroundColor White
    Write-Host "6. Tap 'Add' - now you have a native app!" -ForegroundColor White
    Write-Host ""
    Write-Host "Android Setup:" -ForegroundColor White
    Write-Host "1. Open Chrome on your device" -ForegroundColor White
    Write-Host "2. Go to: http://$MacIP`:8080" -ForegroundColor White
    Write-Host "3. Tap the menu (⋮) → 'Add to Home screen'" -ForegroundColor White
    Write-Host "4. Name it 'Digital Labour Command'" -ForegroundColor White
    Write-Host "5. Tap 'Add' - now you have a native app!" -ForegroundColor White
    Write-Host ""
    Write-Host "Testing Features:" -ForegroundColor Yellow
    Write-Host "- Pull down to refresh status" -ForegroundColor White
    Write-Host "- Tap command buttons to execute operations" -ForegroundColor White
    Write-Host "- Check memory usage stays under 4GB" -ForegroundColor White
    Write-Host "- Verify real-time status updates" -ForegroundColor White
}

# Main test logic
Write-Host "📱 Digital Labour MOBILE TEST" -ForegroundColor Cyan
Write-Host "===========================" -ForegroundColor Cyan
Write-Host ""

$baseUrl = "http://$MacIP`:8080"

# Basic connectivity test
Write-Info "Testing connectivity to $baseUrl..."
if (-not (Test-WebEndpoint $baseUrl "Mobile Interface")) {
    Write-Error "Cannot connect to mobile interface. Make sure Mac services are running."
    exit 1
}

# API status test
Write-Info "Testing API endpoints..."
$status = Test-APIEndpoint "$baseUrl/api/status" "Status"
if ($status) {
    Write-Info "System status: $($status.system.platform)"
    Write-Info "Memory usage: $($status.system.memory_usage)"
}

# PWA features test
if ($PWATest -or $FullTest) {
    Test-PWAFeatures $baseUrl
}

# Mobile commands test
if ($FullTest) {
    Test-MobileCommands $baseUrl
}

# Performance test
if ($PerformanceTest -or $FullTest) {
    Test-Performance $baseUrl
}

# Show mobile instructions
Show-MobileInstructions

Write-Host ""
Write-Success "Mobile test complete!"
Write-Info "Use -FullTest for comprehensive testing"
Write-Info "Use -PWATest for PWA-specific tests"
Write-Info "Use -PerformanceTest for speed tests"</content>
<parameter name="filePath">C:/Dev/DIGITAL LABOUR-Shared/test_mobile.ps1