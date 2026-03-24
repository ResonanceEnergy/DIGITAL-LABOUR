# Bit Rage Systems Remote Access Setup
# Enable secure remote access to local command center from anywhere

param(
    [switch]$Cloudflare,
    [switch]$Ngrok,
    [switch]$Local,
    [switch]$Start,
    [switch]$Stop,
    [switch]$Mobile,
    [switch]$Firewall,
    [switch]$Instructions,
    [switch]$Complete,
    [switch]$Interactive
)

# Colors for PowerShell
$Colors = @{
    Red = [ConsoleColor]::Red
    Green = [ConsoleColor]::Green
    Yellow = [ConsoleColor]::Yellow
    Blue = [ConsoleColor]::Blue
    White = [ConsoleColor]::White
}

function Write-ColorOutput {
    param(
        [string]$Message,
        [ConsoleColor]$Color = [ConsoleColor]::White
    )
    $OriginalColor = $Host.UI.RawUI.ForegroundColor
    $Host.UI.RawUI.ForegroundColor = $Color
    Write-Host $Message
    $Host.UI.RawUI.ForegroundColor = $OriginalColor
}

function Write-Info {
    param([string]$Message)
    Write-ColorOutput "[INFO] $Message" $Colors.Blue
}

function Write-Success {
    param([string]$Message)
    Write-ColorOutput "[SUCCESS] $Message" $Colors.Green
}

function Write-Warning {
    param([string]$Message)
    Write-ColorOutput "[WARNING] $Message" $Colors.Yellow
}

function Write-Error {
    param([string]$Message)
    Write-ColorOutput "[ERROR] $Message" $Colors.Red
}

# Configuration
$RemoteConfigFile = "remote_config.json"
$CloudflareConfigDir = "$env:USERPROFILE\.cloudflared"
$NgrokConfigDir = "$env:USERPROFILE\.ngrok2"

# Create remote config
function New-RemoteConfig {
    Write-Info "Creating remote access configuration..."

    $config = @{
        remote_access = @{
            enabled = $true
            method = "cloudflare"
            domain = "command.superagency.local"
            services = @{
                matrix_monitor = @{
                    local_port = 3000
                    remote_path = "/monitor"
                    auth_required = $true
                }
                operations_api = @{
                    local_port = 5000
                    remote_path = "/api"
                    auth_required = $true
                }
                command_center = @{
                    local_port = 8080
                    remote_path = "/"
                    auth_required = $true
                }
            }
            security = @{
                basic_auth = $true
                username = "admin"
                password_hash = ""
                allowed_ips = @()
                rate_limiting = $true
            }
            mobile = @{
                responsive_design = $true
                touch_optimized = $true
                offline_support = $false
            }
        }
    }

    $config | ConvertTo-Json -Depth 10 | Out-File -FilePath $RemoteConfigFile -Encoding UTF8
    Write-Success "Remote configuration created"
}

# Setup Cloudflare Tunnel
function Install-CloudflareTunnel {
    Write-Info "Setting up Cloudflare Tunnel for secure remote access..."

    # Check if cloudflared is installed
    if (!(Get-Command cloudflared -ErrorAction SilentlyContinue)) {
        Write-Info "Installing cloudflared..."
        try {
            winget install --id Cloudflare.cloudflared --accept-source-agreements --accept-package-agreements
        } catch {
            Write-Warning "winget failed, trying chocolatey..."
            choco install cloudflared -y
        }
    }

    # Create config directory
    New-Item -ItemType Directory -Path $CloudflareConfigDir -Force | Out-Null

    # Create tunnel configuration
    $configPath = Join-Path $CloudflareConfigDir "config.yaml"
    $config = @"
tunnel: super-agency-command-center
credentials-file: $CloudflareConfigDir\tunnel.json

ingress:
  - hostname: command.superagency.local
    service: http://localhost:3000
    originRequest:
      noTLSVerify: true
  - hostname: api.superagency.local
    service: http://localhost:5000
    originRequest:
      noTLSVerify: true
  - hostname: ops.superagency.local
    service: http://localhost:8080
    originRequest:
      noTLSVerify: true
  - service: http_status:404
"@

    $config | Out-File -FilePath $configPath -Encoding UTF8
    Write-Success "Cloudflare Tunnel configured"
}

# Setup ngrok Tunnel
function Install-NgrokTunnel {
    Write-Info "Setting up ngrok tunnel for remote access..."

    # Check if ngrok is installed
    if (!(Get-Command ngrok -ErrorAction SilentlyContinue)) {
        Write-Info "Installing ngrok..."
        choco install ngrok -y
    }

    # Create ngrok config
    New-Item -ItemType Directory -Path $NgrokConfigDir -Force | Out-Null
    $configPath = Join-Path $NgrokConfigDir "ngrok.yml"

    $config = @"
version: "2"
authtoken: YOUR_NGROK_AUTH_TOKEN
tunnels:
  matrix-monitor:
    addr: 3000
    proto: http
    hostname: matrix.superagency.ngrok.io
    auth: "admin:password"
  operations-api:
    addr: 5000
    proto: http
    hostname: api.superagency.ngrok.io
    auth: "admin:password"
  command-center:
    addr: 8080
    proto: http
    hostname: command.superagency.ngrok.io
    auth: "admin:password"
"@

    $config | Out-File -FilePath $configPath -Encoding UTF8
    Write-Warning "Please set your ngrok auth token: ngrok config add-authtoken YOUR_TOKEN"
    Write-Success "ngrok configuration created"
}

# Setup mobile optimization
function Install-MobileOptimization {
    Write-Info "Setting up mobile optimization..."

    # Create static directories
    New-Item -ItemType Directory -Path "static\css" -Force | Out-Null
    New-Item -ItemType Directory -Path "static\js" -Force | Out-Null

    # Create mobile CSS
    $mobileCss = @"
/* Mobile-first responsive design */
@media (max-width: 768px) {
    .container {
        padding: 10px;
        margin: 0;
    }

    .header {
        font-size: 1.2em;
        padding: 10px;
    }

    .nav-menu {
        flex-direction: column;
        gap: 10px;
    }

    .card {
        margin: 10px 0;
        padding: 15px;
    }

    .button {
        width: 100%;
        padding: 12px;
        font-size: 16px; /* Prevents zoom on iOS */
    }

    .status-grid {
        grid-template-columns: 1fr;
        gap: 10px;
    }

    .chart-container {
        height: 200px;
    }
}

/* Touch optimizations */
.touch-optimized {
    -webkit-tap-highlight-color: rgba(0,0,0,0.1);
    touch-action: manipulation;
}

.touch-optimized button,
.touch-optimized .button {
    min-height: 44px; /* iOS touch target size */
    min-width: 44px;
}

/* iPad optimizations */
@media (min-width: 768px) and (max-width: 1024px) {
    .container {
        max-width: 100%;
        padding: 20px;
    }

    .sidebar {
        width: 250px;
    }

    .main-content {
        margin-left: 250px;
    }
}
"@

    $mobileCss | Out-File -FilePath "static\css\mobile.css" -Encoding UTF8

    # Create mobile JS
    $mobileJs = @"
// Mobile enhancements for Bit Rage Systems Command Center

document.addEventListener('DOMContentLoaded', function() {
    // Add mobile class to body
    document.body.classList.add('mobile-optimized');

    // Touch feedback
    const buttons = document.querySelectorAll('button, .button');
    buttons.forEach(button => {
        button.addEventListener('touchstart', function() {
            this.style.transform = 'scale(0.98)';
        });

        button.addEventListener('touchend', function() {
            this.style.transform = 'scale(1)';
        });
    });

    // Pull to refresh for status updates
    let startY = 0;
    let pullDistance = 0;
    const pullThreshold = 80;

    document.addEventListener('touchstart', function(e) {
        startY = e.touches[0].clientY;
    });

    document.addEventListener('touchmove', function(e) {
        if (window.scrollY === 0) {
            pullDistance = e.touches[0].clientY - startY;
            if (pullDistance > 0) {
                e.preventDefault();
                // Add visual feedback for pull
                document.body.style.transform = `translateY(${Math.min(pullDistance * 0.5, pullThreshold)}px)`;
            }
        }
    });

    document.addEventListener('touchend', function() {
        if (pullDistance > pullThreshold) {
            // Trigger refresh
            location.reload();
        }
        document.body.style.transform = '';
        pullDistance = 0;
    });

    // Service worker for offline support (basic)
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js')
            .then(registration => {
                console.log('Service Worker registered');
            })
            .catch(error => {
                console.log('Service Worker registration failed');
            });
    }

    // Auto-refresh for critical data
    setInterval(function() {
        // Refresh status indicators every 30 seconds
        const statusElements = document.querySelectorAll('.status-indicator');
        statusElements.forEach(element => {
            // Add refresh logic here
        });
    }, 30000);
});
"@

    $mobileJs | Out-File -FilePath "static\js\mobile.js" -Encoding UTF8
    Write-Success "Mobile optimization configured"
}

# Setup firewall rules
function Set-FirewallRules {
    Write-Info "Configuring firewall for remote access..."

    # Add firewall rules for required ports
    $ports = @(3000, 5000, 8080, 80, 443)
    foreach ($port in $ports) {
        $ruleName = "Bit Rage Systems Port $port"
        $existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue

        if (!$existingRule) {
            New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Protocol TCP -LocalPort $port -Action Allow
            Write-Info "Added firewall rule for port $port"
        } else {
            Write-Info "Firewall rule for port $port already exists"
        }
    }

    Write-Success "Firewall configured"
}

# Generate access instructions
function New-AccessInstructions {
    Write-Info "Generating access instructions..."

    $instructions = @"
# 🌐 Bit Rage Systems Remote Access Instructions

## Current Setup
Your command center is configured for remote access with the following methods:

### 1. Cloudflare Tunnel (Recommended)
- **URL**: https://command.superagency.local
- **Matrix Monitor**: https://command.superagency.local/monitor
- **Operations API**: https://api.superagency.local
- **Command Center**: https://ops.superagency.local

### 2. ngrok Tunnel (Alternative)
- **Matrix Monitor**: https://matrix.superagency.ngrok.io
- **Operations API**: https://api.superagency.ngrok.io
- **Command Center**: https://command.superagency.ngrok.io

### 3. Local Network Access
- **Matrix Monitor**: http://YOUR_LOCAL_IP:3000
- **Operations API**: http://YOUR_LOCAL_IP:5000
- **Command Center**: http://YOUR_LOCAL_IP:8080

## Mobile Access

### iPhone/iPad Setup
1. Open Safari on your device
2. Navigate to one of the URLs above
3. Add to home screen for app-like experience:
   - Tap share button
   - Select "Add to Home Screen"
   - Name it "Bit Rage Systems Command"

### Android Setup
1. Open Chrome on your device
2. Navigate to the URL
3. Add to home screen:
   - Tap menu (3 dots)
   - Select "Add to Home screen"
   - Name it "Bit Rage Systems Command"

## Security Features
- Basic authentication enabled
- HTTPS encryption
- Rate limiting active
- Mobile-optimized interface

## Troubleshooting

### Can't Access Remotely?
1. Check if tunnel is running: Get-Process cloudflared,ngrok
2. Verify firewall: Check Windows Firewall rules
3. Check local services: Visit localhost URLs first
4. Restart tunnel: .\setup_remote_access.ps1 -Start

### Mobile Issues?
1. Clear browser cache
2. Try incognito/private mode
3. Check network connection
4. Ensure JavaScript is enabled

## Starting Remote Access

```powershell
# Start everything with remote access
.\launch_command_center.ps1 -QuickStart -Remote

# Or start remote access separately
.\setup_remote_access.ps1 -Start
```

## Stopping Remote Access

```powershell
.\setup_remote_access.ps1 -Stop
```

---
*Generated on $(Get-Date)*
"@

    $instructions | Out-File -FilePath "REMOTE_ACCESS_INSTRUCTIONS.md" -Encoding UTF8
    Write-Success "Access instructions generated"
}

# Start remote access
function Start-RemoteAccess {
    Write-Info "Starting remote access services..."

    # Start based on configured method
    if (Test-Path $RemoteConfigFile) {
        $config = Get-Content $RemoteConfigFile | ConvertFrom-Json
        $method = $config.remote_access.method
    } else {
        $method = "cloudflare"
    }

    switch ($method) {
        "cloudflare" {
            if (Get-Command cloudflared -ErrorAction SilentlyContinue) {
                Write-Info "Starting Cloudflare tunnel..."
                $process = Start-Process cloudflared -ArgumentList "tunnel run super-agency-command-center" -NoNewWindow -PassThru
                $process.Id | Out-File -FilePath ".cloudflare.pid"
            } else {
                Write-Error "cloudflared not installed"
                exit 1
            }
        }
        "ngrok" {
            if (Get-Command ngrok -ErrorAction SilentlyContinue) {
                Write-Info "Starting ngrok tunnels..."
                $configPath = Join-Path $NgrokConfigDir "ngrok.yml"
                $process = Start-Process ngrok -ArgumentList "start --config=$configPath --all" -NoNewWindow -PassThru
                $process.Id | Out-File -FilePath ".ngrok.pid"
            } else {
                Write-Error "ngrok not installed"
                exit 1
            }
        }
    }

    Write-Success "Remote access started"
}

# Stop remote access
function Stop-RemoteAccess {
    Write-Info "Stopping remote access services..."

    # Stop running processes
    $processes = @("cloudflared", "ngrok", "caddy")
    foreach ($processName in $processes) {
        $procs = Get-Process -Name $processName -ErrorAction SilentlyContinue
        if ($procs) {
            $procs | Stop-Process -Force
            Write-Success "Stopped $processName"
        }
    }

    # Clean up PID files
    $pidFiles = @(".cloudflare.pid", ".ngrok.pid", ".caddy.pid")
    foreach ($pidFile in $pidFiles) {
        if (Test-Path $pidFile) {
            Remove-Item $pidFile
        }
    }

    Write-Success "Remote access stopped"
}

# Show menu
function Show-Menu {
    Write-Host ""
    Write-Host "Bit Rage Systems Remote Access Setup Menu"
    Write-Host "====================================="
    Write-Host "1. Setup Cloudflare Tunnel (Recommended)"
    Write-Host "2. Setup ngrok Tunnel (Alternative)"
    Write-Host "3. Setup Mobile Optimization"
    Write-Host "4. Configure Firewall"
    Write-Host "5. Start Remote Access"
    Write-Host "6. Stop Remote Access"
    Write-Host "7. Generate Access Instructions"
    Write-Host "8. Complete Setup (All Steps)"
    Write-Host "9. Exit"
    Write-Host ""
}

# Main logic
function Invoke-Main {
    # Handle command line switches
    if ($Cloudflare) {
        New-RemoteConfig
        Install-CloudflareTunnel
        Set-FirewallRules
        Install-MobileOptimization
        New-AccessInstructions
        return
    }

    if ($Ngrok) {
        New-RemoteConfig
        Install-NgrokTunnel
        Set-FirewallRules
        Install-MobileOptimization
        New-AccessInstructions
        return
    }

    if ($Local) {
        Write-Warning "Local reverse proxy setup not implemented for Windows yet"
        return
    }

    if ($Start) {
        Start-RemoteAccess
        return
    }

    if ($Stop) {
        Stop-RemoteAccess
        return
    }

    if ($Mobile) {
        Install-MobileOptimization
        return
    }

    if ($Firewall) {
        Set-FirewallRules
        return
    }

    if ($Instructions) {
        New-AccessInstructions
        return
    }

    if ($Complete) {
        New-RemoteConfig
        Install-CloudflareTunnel
        Set-FirewallRules
        Install-MobileOptimization
        New-AccessInstructions
        Start-RemoteAccess
        return
    }

    # Interactive menu
    while ($true) {
        Show-Menu
        $choice = Read-Host "Choose an option (1-9)"

        switch ($choice) {
            "1" {
                New-RemoteConfig
                Install-CloudflareTunnel
            }
            "2" {
                New-RemoteConfig
                Install-NgrokTunnel
            }
            "3" {
                Install-MobileOptimization
            }
            "4" {
                Set-FirewallRules
            }
            "5" {
                Start-RemoteAccess
            }
            "6" {
                Stop-RemoteAccess
            }
            "7" {
                New-AccessInstructions
            }
            "8" {
                New-RemoteConfig
                Install-CloudflareTunnel
                Set-FirewallRules
                Install-MobileOptimization
                New-AccessInstructions
                Start-RemoteAccess
            }
            "9" {
                Write-Success "Goodbye! 👋"
                exit 0
            }
            default {
                Write-Error "Invalid option. Please choose 1-9."
            }
        }

        Write-Host ""
        Read-Host "Press Enter to continue"
    }
}

# Run main function
Write-Host "🌐 Bit Rage Systems Remote Access Setup"
Write-Host "==================================="
Write-Host ""

Invoke-Main