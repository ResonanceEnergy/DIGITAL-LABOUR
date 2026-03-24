# Bit Rage Systems Unified Mobile Launcher
# Run locally and access from anywhere with phone/iPad

param(
    [switch]$Start,
    [switch]$Launch,
    [switch]$Stop,
    [switch]$Status,
    [switch]$LocalOnly,
    [switch]$RemoteOnly,
    [switch]$Setup,
    [switch]$Help
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

function Write-Mobile {
    param([string]$Message)
    Write-Host "[$((Get-Date).ToString('HH:mm:ss'))] 📱 MOBILE: $Message" -ForegroundColor Magenta
}

function Write-Launch {
    param([string]$Message)
    Write-Host "[$((Get-Date).ToString('HH:mm:ss'))] 🚀 LAUNCH: $Message" -ForegroundColor Cyan
}

# Get local IP
function Get-LocalIP {
    try {
        $ip = (Get-NetIPAddress | Where-Object { $_.AddressFamily -eq 'IPv4' -and $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.*' } | Select-Object -First 1).IPAddress
        return $ip
    } catch {
        return "localhost"
    }
}

$LOCAL_IP = Get-LocalIP

# Check if mobile setup exists
function Test-MobileSetup {
    if (!(Test-Path "mobile_command_center.py")) {
        Write-Warning "Mobile command center not set up. Running setup..."
        & .\mobile_setup.ps1 -Setup
    }
}

# Start local services
function Start-LocalServices {
    Write-Launch "Starting local Bit Rage Systems services..."

    # Start Matrix Monitor
    if ((Test-Path "matrix_monitor.py") -or (Test-Path "matrix_monitor" -PathType Container)) {
        Write-Info "Starting Matrix Monitor..."
        try {
            if (Test-Path "matrix_monitor.py") {
                $process = Start-Process python -ArgumentList "matrix_monitor.py" -NoNewWindow -PassThru
            } else {
                $process = Start-Process python -ArgumentList "-m matrix_monitor" -NoNewWindow -PassThru
            }
            $process.Id | Out-File -FilePath ".matrix_monitor.pid"
            Write-Success "Matrix Monitor started (PID: $($process.Id))"
        } catch {
            Write-Warning "Matrix Monitor start attempted"
        }
    }

    # Start Operations Interface
    if (Test-Path "operations_launcher.py") {
        Write-Info "Starting Operations Interface..."
        $process = Start-Process python -ArgumentList "operations_launcher.py" -NoNewWindow -PassThru
        $process.Id | Out-File -FilePath ".operations.pid"
        Write-Success "Operations Interface started (PID: $($process.Id))"
    }

    # Start AAC System
    if ((Test-Path "repos\AAC") -and (Test-Path "repos\AAC\aac_dashboard.py")) {
        Write-Info "Starting AAC System..."
        Push-Location "repos\AAC"
        $process = Start-Process python -ArgumentList "aac_dashboard.py" -NoNewWindow -PassThru
        $process.Id | Out-File -FilePath "..\..\.aac.pid"
        Pop-Location
        Write-Success "AAC System started (PID: $(Get-Content '.aac.pid'))"
    }
}

# Start mobile command center
function Start-MobileCenter {
    Write-Mobile "Starting mobile command center..."

    if (Test-Path "mobile_command_center.py") {
        $process = Start-Process python -ArgumentList "mobile_command_center.py" -NoNewWindow -PassThru
        $process.Id | Out-File -FilePath ".mobile_server.pid"
        Write-Success "Mobile command center started (PID: $($process.Id))"
    } else {
        Write-Error "Mobile command center not found. Run setup first."
        exit 1
    }
}

# Start remote tunnel
function Start-RemoteTunnel {
    Write-Mobile "Starting remote access tunnel..."

    # Try ngrok first
    if (Get-Command ngrok -ErrorAction SilentlyContinue) {
        Write-Info "Starting ngrok tunnel..."
        $process = Start-Process ngrok -ArgumentList "http 8080" -NoNewWindow -PassThru
        $process.Id | Out-File -FilePath ".ngrok.pid"
        Start-Sleep 3
        Write-Success "ngrok tunnel started (PID: $($process.Id))"
        return
    }

    # Try cloudflared
    if (Get-Command cloudflared -ErrorAction SilentlyContinue) {
        Write-Info "Starting Cloudflare tunnel..."
        $process = Start-Process cloudflared -ArgumentList "tunnel run super-agency-mobile" -NoNewWindow -PassThru
        $process.Id | Out-File -FilePath ".cloudflare.pid"
        Start-Sleep 3
        Write-Success "Cloudflare tunnel started (PID: $($process.Id))"
        return
    }

    Write-Warning "No tunnel service found. Install ngrok or cloudflared for remote access."
    Write-Info "You can still access locally at http://$LOCAL_IP`:8080"
}

# Show access information
function Show-AccessInfo {
    Write-Host ""
    Write-Success "🎉 Bit Rage Systems Mobile Command Center is RUNNING!"
    Write-Host ""

    Write-Host "📱 ACCESS YOUR COMMAND CENTER FROM ANYWHERE:" -ForegroundColor Cyan
    Write-Host ""

    Write-Host "🏠 LOCAL ACCESS (same WiFi network):" -ForegroundColor White
    Write-Host "   http://$LOCAL_IP`:8080" -ForegroundColor Cyan
    Write-Host ""

    # Check for tunnel URLs
    if ((Test-Path ".ngrok.pid") -and (Get-Process -Id (Get-Content ".ngrok.pid") -ErrorAction SilentlyContinue)) {
        Write-Host "🌐 REMOTE ACCESS (from anywhere):" -ForegroundColor White
        try {
            $ngrokResponse = Invoke-WebRequest -Uri "http://localhost:4040/api/tunnels" -ErrorAction SilentlyContinue
            $tunnels = $ngrokResponse.Content | ConvertFrom-Json
            $publicUrl = $tunnels.tunnels[0].public_url
            if ($publicUrl) {
                Write-Host "   $publicUrl" -ForegroundColor Cyan
            }
        } catch {
            Write-Host "   https://superagency.ngrok.io (check ngrok dashboard)" -ForegroundColor Cyan
        }
        Write-Host ""
    } elseif ((Test-Path ".cloudflare.pid") -and (Get-Process -Id (Get-Content ".cloudflare.pid") -ErrorAction SilentlyContinue)) {
        Write-Host "🌐 REMOTE ACCESS (from anywhere):" -ForegroundColor White
        Write-Host "   https://mobile.superagency.local" -ForegroundColor Cyan
        Write-Host ""
    }

    Write-Host "📱 MOBILE SETUP INSTRUCTIONS:" -ForegroundColor Yellow
    Write-Host "1. Open Safari/Chrome on your phone/iPad" -ForegroundColor White
    Write-Host "2. Navigate to one of the URLs above" -ForegroundColor White
    Write-Host "3. Tap share button → Add to Home Screen" -ForegroundColor White
    Write-Host "4. Name it 'Bit Rage Systems Command'" -ForegroundColor White
    Write-Host ""

    Write-Host "🎮 MOBILE FEATURES:" -ForegroundColor Green
    Write-Host "   • Touch-optimized controls" -ForegroundColor White
    Write-Host "   • Pull-to-refresh dashboard" -ForegroundColor White
    Write-Host "   • Real-time system monitoring" -ForegroundColor White
    Write-Host "   • One-tap command execution" -ForegroundColor White
    Write-Host "   • Offline-capable interface" -ForegroundColor White
    Write-Host ""

    Write-Host "🛑 TO STOP: .\mobile_launcher.ps1 -Stop" -ForegroundColor Red
    Write-Host "📊 STATUS:  .\mobile_launcher.ps1 -Status" -ForegroundColor Blue
}

# Stop all services
function Stop-Services {
    Write-Info "Stopping all Bit Rage Systems services..."

    # Get all PID files
    $pidFiles = Get-ChildItem ".*.pid" -File

    foreach ($pidFile in $pidFiles) {
        if (Test-Path $pidFile) {
            $pid = Get-Content $pidFile
            $serviceName = $pidFile.BaseName.TrimStart('.')

            if (Get-Process -Id $pid -ErrorAction SilentlyContinue) {
                Stop-Process -Id $pid -Force
                Write-Success "$serviceName stopped"
            } else {
                Write-Warning "$serviceName not running (stale PID file)"
            }
            Remove-Item $pidFile
        }
    }

    Write-Success "All services stopped"
}

# Show status
function Show-Status {
    Write-Host ""
    Write-Mobile "Bit Rage Systems Mobile Command Center Status"
    Write-Host "==========================================" -ForegroundColor Magenta
    Write-Host ""

    Write-Host "Local Services:" -ForegroundColor White
    $pidFiles = Get-ChildItem ".*.pid" -File

    foreach ($pidFile in $pidFiles) {
        $pid = Get-Content $pidFile
        $serviceName = $pidFile.BaseName.TrimStart('.').Replace('_', ' ')

        if (Get-Process -Id $pid -ErrorAction SilentlyContinue) {
            Write-Host "  ✅ $serviceName`: Running (PID: $pid)" -ForegroundColor Green
        } else {
            Write-Host "  ❌ $serviceName`: Not running (stale PID)" -ForegroundColor Red
        }
    }

    Write-Host ""
    Write-Host "Network Access:" -ForegroundColor White
    Write-Host "  🏠 Local: http://$LOCAL_IP`:8080" -ForegroundColor Cyan

    if ((Test-Path ".ngrok.pid") -and (Get-Process -Id (Get-Content ".ngrok.pid") -ErrorAction SilentlyContinue)) {
        Write-Host "  🌐 Remote: Check ngrok dashboard (localhost:4040)" -ForegroundColor Cyan
    } elseif ((Test-Path ".cloudflare.pid") -and (Get-Process -Id (Get-Content ".cloudflare.pid") -ErrorAction SilentlyContinue)) {
        Write-Host "  🌐 Remote: https://mobile.superagency.local" -ForegroundColor Cyan
    } else {
        Write-Host "  ❌ Remote: No tunnel active" -ForegroundColor Red
    }

    Write-Host ""
    Write-Host "System Health:" -ForegroundColor White
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8080/health" -TimeoutSec 5 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "  ✅ Mobile Interface: Online" -ForegroundColor Green
        } else {
            Write-Host "  ❌ Mobile Interface: Offline" -ForegroundColor Red
        }
    } catch {
        Write-Host "  ❌ Mobile Interface: Offline" -ForegroundColor Red
    }
}

# Main execution
function Invoke-Main {
    Write-Host "🚀📱 Bit Rage Systems Unified Mobile Launcher" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Run your command center locally and access from anywhere!" -ForegroundColor White
    Write-Host ""

    if ($Start -or $Launch) {
        Test-MobileSetup
        Start-LocalServices
        Start-MobileCenter
        Start-RemoteTunnel
        Show-AccessInfo
        return
    }

    if ($Stop) {
        Stop-Services
        return
    }

    if ($Status) {
        Show-Status
        return
    }

    if ($LocalOnly) {
        Test-MobileSetup
        Start-LocalServices
        Start-MobileCenter
        Write-Host ""
        Write-Success "Local-only mode started!"
        Write-Host "Access at: http://$LOCAL_IP`:8080" -ForegroundColor Cyan
        return
    }

    if ($RemoteOnly) {
        Test-MobileSetup
        Start-MobileCenter
        Start-RemoteTunnel
        Show-AccessInfo
        return
    }

    if ($Setup) {
        & .\mobile_setup.ps1 -Setup
        return
    }

    if ($Help) {
        Show-Help
        return
    }

    # Interactive menu
    Write-Host "Choose an option:" -ForegroundColor White
    Write-Host "1. Start Everything (Local + Remote)" -ForegroundColor Green
    Write-Host "2. Start Local Only" -ForegroundColor Cyan
    Write-Host "3. Start Remote Only" -ForegroundColor Yellow
    Write-Host "4. Stop All Services" -ForegroundColor Red
    Write-Host "5. Show Status" -ForegroundColor Blue
    Write-Host "6. Run Setup" -ForegroundColor Magenta
    Write-Host "7. Help" -ForegroundColor Gray
    Write-Host ""

    $choice = Read-Host "Enter choice (1-7)"

    switch ($choice) {
        "1" { Invoke-Main -Start }
        "2" { Invoke-Main -LocalOnly }
        "3" { Invoke-Main -RemoteOnly }
        "4" { Invoke-Main -Stop }
        "5" { Invoke-Main -Status }
        "6" { Invoke-Main -Setup }
        "7" { Show-Help }
        default { Write-Error "Invalid choice. Run with -Help for options." }
    }
}

function Show-Help {
    Write-Host "Bit Rage Systems Mobile Launcher Help" -ForegroundColor Cyan
    Write-Host "=================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\mobile_launcher.ps1 [option]" -ForegroundColor White
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Yellow
    Write-Host "  -Start, -Launch     Start everything (local + remote)" -ForegroundColor White
    Write-Host "  -LocalOnly          Start local access only" -ForegroundColor White
    Write-Host "  -RemoteOnly         Start remote access only" -ForegroundColor White
    Write-Host "  -Stop               Stop all services" -ForegroundColor White
    Write-Host "  -Status             Show current status" -ForegroundColor White
    Write-Host "  -Setup              Run mobile setup" -ForegroundColor White
    Write-Host "  -Help               Show this help" -ForegroundColor White
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Green
    Write-Host "  .\mobile_launcher.ps1 -Start     # Start everything" -ForegroundColor White
    Write-Host "  .\mobile_launcher.ps1 -LocalOnly # Local access only" -ForegroundColor White
    Write-Host "  .\mobile_launcher.ps1 -Status    # Check status" -ForegroundColor White
    Write-Host "  .\mobile_launcher.ps1 -Stop      # Stop everything" -ForegroundColor White
    Write-Host ""
}

# Run main function
Invoke-Main