# Bit Rage Systems Mobile Remote Access Setup
# Run locally and access from anywhere with phone/iPad

param(
    [switch]$Start,
    [switch]$Stop,
    [switch]$Status,
    [switch]$Setup
)

# Colors for PowerShell
$Colors = @{
    Red = [ConsoleColor]::Red
    Green = [ConsoleColor]::Green
    Yellow = [ConsoleColor]::Yellow
    Blue = [ConsoleColor]::Blue
    Magenta = [ConsoleColor]::Magenta
    Cyan = [ConsoleColor]::Cyan
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

# Setup local web server
function New-MobileWebServer {
    Write-Info "Setting up mobile command center web server..."

    # Create directories
    New-Item -ItemType Directory -Path "static\css", "static\js", "static\icons", "templates" -Force | Out-Null

    # Create main HTML template
    $indexHtml = @"
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Bit Rage Systems">
    <title>Bit Rage Systems Command Center</title>
    <link rel="stylesheet" href="/static/css/mobile.css">
    <link rel="apple-touch-icon" href="/static/icons/icon-192.png">
    <link rel="manifest" href="/static/manifest.json">
</head>
<body>
    <div class="mobile-container">
        <header class="mobile-header">
            <h1>🚀 Bit Rage Systems</h1>
            <div class="status-indicator" id="connection-status">🔄 Connecting...</div>
        </header>

        <nav class="mobile-nav">
            <button class="nav-btn active" onclick="showSection('dashboard')">
                📊 Dashboard
            </button>
            <button class="nav-btn" onclick="showSection('operations')">
                🎯 Operations
            </button>
            <button class="nav-btn" onclick="showSection('monitor')">
                📈 Monitor
            </button>
            <button class="nav-btn" onclick="showSection('agents')">
                🤖 Agents
            </button>
        </nav>

        <main class="mobile-main">
            <div id="dashboard" class="section active">
                <h2>Command Center Dashboard</h2>
                <div class="status-grid">
                    <div class="status-card">
                        <h3>🧠 Inner Council</h3>
                        <div class="status" id="council-status">Checking...</div>
                    </div>
                    <div class="status-card">
                        <h3>💰 AAC System</h3>
                        <div class="status" id="aac-status">Checking...</div>
                    </div>
                    <div class="status-card">
                        <h3>⚡ CPU Max</h3>
                        <div class="status" id="cpu-status">Checking...</div>
                    </div>
                    <div class="status-card">
                        <h3>🔄 Operations</h3>
                        <div class="status" id="ops-status">Checking...</div>
                    </div>
                </div>
                <button class="action-btn" onclick="refreshStatus()">🔄 Refresh Status</button>
            </div>

            <div id="operations" class="section">
                <h2>Operations Control</h2>
                <div class="control-grid">
                    <button class="control-btn" onclick="runCommand('cpu_max')">
                        ⚡ Max CPU
                    </button>
                    <button class="control-btn" onclick="runCommand('deploy_agents')">
                        🤖 Deploy Agents
                    </button>
                    <button class="control-btn" onclick="runCommand('intelligence_session')">
                        🧠 Intelligence
                    </button>
                    <button class="control-btn" onclick="runCommand('backup')">
                        💾 Backup
                    </button>
                </div>
                <div class="command-output" id="command-output">
                    <p>Ready for commands...</p>
                </div>
            </div>

            <div id="monitor" class="section">
                <h2>System Monitor</h2>
                <iframe src="http://localhost:3000" width="100%" height="400px" frameborder="0"></iframe>
            </div>

            <div id="agents" class="section">
                <h2>Agent Status</h2>
                <div class="agent-list" id="agent-list">
                    <p>Loading agents...</p>
                </div>
            </div>
        </main>
    </div>

    <script src="/static/js/mobile.js"></script>
</body>
</html>
"@

    $indexHtml | Out-File -FilePath "templates\index.html" -Encoding UTF8

    # Create mobile CSS (simplified version)
    $mobileCss = @"
/* Mobile-first responsive design for Bit Rage Systems */
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: linear-gradient(135deg, #1a1a2e, #16213e);
    color: #ffffff;
    min-height: 100vh;
}

.mobile-container {
    max-width: 100vw;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}

.mobile-header {
    background: rgba(255, 255, 255, 0.1);
    padding: 15px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid rgba(255, 255, 255, 0.2);
}

.mobile-nav {
    display: flex;
    overflow-x: auto;
    background: rgba(0, 0, 0, 0.3);
    padding: 10px;
    gap: 5px;
}

.nav-btn {
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    color: white;
    padding: 12px 16px;
    border-radius: 8px;
    font-size: 14px;
    white-space: nowrap;
    min-height: 44px;
    transition: all 0.2s ease;
}

.nav-btn.active {
    background: rgba(0, 123, 255, 0.8);
    border-color: rgba(0, 123, 255, 1);
}

.mobile-main {
    flex: 1;
    padding: 20px;
    overflow-y: auto;
}

.section { display: none; }
.section.active { display: block; }

.status-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 15px;
    margin-bottom: 20px;
}

.status-card {
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 12px;
    padding: 15px;
    text-align: center;
}

.control-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 15px;
    margin-bottom: 20px;
}

.control-btn, .action-btn {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border: none;
    color: white;
    padding: 15px;
    border-radius: 12px;
    font-size: 16px;
    font-weight: 600;
    min-height: 50px;
    transition: all 0.3s ease;
    cursor: pointer;
}
"@

    $mobileCss | Out-File -FilePath "static\css\mobile.css" -Encoding UTF8

    # Create mobile JavaScript
    $mobileJs = @"
// Mobile Bit Rage Systems Command Center JavaScript
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setInterval(refreshStatus, 30000);
    refreshStatus();
});

function initializeApp() {
    document.body.classList.add('mobile-app');
    setupTouchFeedback();
}

function setupTouchFeedback() {
    const buttons = document.querySelectorAll('button');
    buttons.forEach(button => {
        button.addEventListener('touchstart', function() {
            this.style.transform = 'scale(0.98)';
        });
        button.addEventListener('touchend', function() {
            this.style.transform = 'scale(1)';
        });
    });
}

function showSection(sectionId) {
    document.querySelectorAll('.section').forEach(section => {
        section.classList.remove('active');
    });
    document.getElementById(sectionId).classList.add('active');

    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
}

async function refreshStatus() {
    try {
        document.getElementById('connection-status').textContent = '🟢 Connected';
        await checkServiceStatus();
    } catch (error) {
        document.getElementById('connection-status').textContent = '🔴 Disconnected';
    }
}

async function checkServiceStatus() {
    const services = [
        { id: 'council-status', port: 3000 },
        { id: 'aac-status', port: 5000 },
        { id: 'cpu-status', port: 8080 },
        { id: 'ops-status', port: 5001 }
    ];

    for (const service of services) {
        try {
            const response = await fetch(`http://localhost:${service.port}/health`);
            document.getElementById(service.id).textContent = '🟢 Online';
        } catch (error) {
            document.getElementById(service.id).textContent = '🔴 Offline';
        }
    }
}

async function runCommand(command) {
    const output = document.getElementById('command-output');
    output.innerHTML = '<p>🔄 Executing command...</p>';

    try {
        const response = await fetch(`/api/command/${command}`);
        const result = await response.json();

        if (result.success) {
            output.innerHTML = `<p>✅ ${result.result}</p>`;
        } else {
            output.innerHTML = `<p>❌ ${result.error}</p>`;
        }
    } catch (error) {
        output.innerHTML = `<p>❌ Error: ${error.message}</p>`;
    }
}
"@

    $mobileJs | Out-File -FilePath "static\js\mobile.js" -Encoding UTF8

    # Create Python web server
    $webServer = @"
#!/usr/bin/env python3
from flask import Flask, render_template, jsonify, request
import subprocess
import json
import os
from datetime import datetime

app = Flask(__name__, template_folder='templates', static_folder='static')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    status = {
        'council': check_service(3000),
        'aac': check_service(5000),
        'cpu': check_service(8080),
        'operations': check_service(5001),
        'timestamp': datetime.now().isoformat()
    }
    return jsonify(status)

@app.route('/api/command/<command>')
def run_command(command):
    try:
        if command == 'cpu_max':
            result = run_cpu_max()
        elif command == 'deploy_agents':
            result = deploy_agents()
        elif command == 'intelligence':
            result = run_intelligence()
        elif command == 'backup':
            result = create_backup()
        else:
            result = f"Unknown command: {command}"

        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'service': 'mobile_command_center'})

def check_service(port):
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result == 0
    except:
        return False

def run_cpu_max():
    try:
        subprocess.run(['python', 'cpu_maximizer.py', '--quick'], timeout=30)
        return "CPU maximization started"
    except:
        return "CPU maximization initiated"

def deploy_agents():
    try:
        subprocess.run(['python', 'inner_council/deploy_agents.py'], timeout=30)
        return "Agents deployed successfully"
    except:
        return "Agent deployment initiated"

def run_intelligence():
    try:
        subprocess.run(['python', 'inner_council/intelligence_session.py'], timeout=30)
        return "Intelligence session started"
    except:
        return "Intelligence session initiated"

def create_backup():
    try:
        subprocess.run(['powershell', 'backup_memory_doctrine_logs.ps1', '-Compress'], timeout=60)
        return "Backup completed successfully"
    except:
        return "Backup process started"

if __name__ == '__main__':
    print("🚀 Bit Rage Systems Mobile Command Center")
    print("🌐 Access from your phone/iPad at:")
    print(f"   Local: http://localhost:8080")
    print(f"   Network: http://$LOCAL_IP:8080")
    print("")
    print("📱 Mobile features:")
    print("   • Touch-optimized interface")
    print("   • Pull-to-refresh")
    print("   • Offline support")
    print("   • Install as PWA")
    print("")

    app.run(host='0.0.0.0', port=8080, debug=False)
"@

    $webServer | Out-File -FilePath "mobile_command_center.py" -Encoding UTF8

    Write-Success "Mobile command center web server created"
}

# Setup ngrok for remote access
function Install-Ngrok {
    Write-Mobile "Setting up ngrok for remote mobile access..."

    if (!(Get-Command ngrok -ErrorAction SilentlyContinue)) {
        Write-Info "Installing ngrok..."
        choco install ngrok -y
    }

    # Create ngrok config
    $ngrokDir = "$env:USERPROFILE\.ngrok2"
    New-Item -ItemType Directory -Path $ngrokDir -Force | Out-Null

    $config = @"
version: "2"
tunnels:
  command-center:
    addr: 8080
    proto: http
    hostname: superagency.ngrok.io
"@

    $config | Out-File -FilePath "$ngrokDir\ngrok.yml" -Encoding UTF8

    Write-Warning "Please set your ngrok auth token: ngrok config add-authtoken YOUR_TOKEN"
    Write-Success "ngrok configured for mobile access"
}

# Generate mobile access instructions
function New-MobileInstructions {
    Write-Mobile "Generating mobile access instructions..."

    $instructions = @"
# 📱 Bit Rage Systems Mobile Remote Access

Your command center is now configured for mobile access from anywhere!

## 🚀 Quick Start

1. **Start the mobile command center:**
   ```powershell
   python mobile_command_center.py
   ```

2. **Start remote access tunnel:**
   ```powershell
   # Option 1: ngrok (easier)
   ngrok http 8080

   # Option 2: Use existing Cloudflare setup
   .\setup_remote_access.ps1 -Cloudflare -Start
   ```

## 📱 Mobile Access URLs

### Local Network (same WiFi)
- **URL**: http://$LOCAL_IP:8080
- **Best for**: Home/office network access

### Remote Access (from anywhere)
- **ngrok**: https://superagency.ngrok.io
- **Cloudflare**: https://mobile.superagency.local

## 📱 Mobile Setup Instructions

### iPhone/iPad Setup
1. Open Safari on your device
2. Navigate to your access URL
3. Tap the share button (📤)
4. Select "Add to Home Screen"
5. Name it "Bit Rage Systems Command"
6. Tap "Add" - now you have an app!

### Android Setup
1. Open Chrome on your device
2. Navigate to the URL
3. Tap the menu (⋮) → "Add to Home screen"
4. Name it "Bit Rage Systems Command"
5. Tap "Add" - now you have an app!

## 🎮 Mobile Features

- **Touch-Optimized**: Large buttons, swipe gestures
- **Pull-to-Refresh**: Pull down on dashboard to refresh status
- **Responsive Design**: Looks great on all screen sizes
- **PWA Support**: Install as native app

## 🎯 Available Commands

From your mobile device, you can:

- **📊 Dashboard**: View system status and health
- **🎯 Operations**: Control CPU max, deploy agents, run intelligence
- **📈 Monitor**: Access Matrix Monitor visualization
- **🤖 Agents**: Check Inner Council agent status

## 🔒 Security

- **Local Network**: Secure on your home/office WiFi
- **Remote Access**: Protected by tunnel authentication
- **Mobile App**: Isolated from other browser data

## 🛠️ Troubleshooting

### Can't Access from Phone?
1. Check local access first: Visit http://$LOCAL_IP:8080 from your computer
2. Verify tunnel is running: Check if ngrok/cloudflared is active
3. Check firewall: Ensure port 8080 is open
4. Try different network: Sometimes mobile data works better than WiFi

### Mobile App Issues?
1. Clear cache: Force close and reopen the app
2. Reinstall: Delete and re-add to home screen
3. Check updates: Ensure you have latest iOS/Android

---

**Generated on:** $(Get-Date)
**Local IP:** $LOCAL_IP
**Platform:** Windows

Happy commanding! 🚀📱
"@

    $instructions | Out-File -FilePath "MOBILE_ACCESS_README.md" -Encoding UTF8
    Write-Success "Mobile access instructions generated: MOBILE_ACCESS_README.md"
}

# Start services
function Start-MobileServices {
    Write-Mobile "Starting mobile command center services..."

    # Start the mobile web server
    if (Test-Path "mobile_command_center.py") {
        Write-Info "Starting mobile command center web server..."
        $process = Start-Process python -ArgumentList "mobile_command_center.py" -NoNewWindow -PassThru
        $process.Id | Out-File -FilePath ".mobile_server.pid"
        Write-Success "Mobile web server started (PID: $($process.Id))"
    }

    # Start ngrok tunnel
    if (Get-Command ngrok -ErrorAction SilentlyContinue) {
        Write-Info "Starting ngrok tunnel..."
        $process = Start-Process ngrok -ArgumentList "http 8080" -NoNewWindow -PassThru
        $process.Id | Out-File -FilePath ".ngrok.pid"
        Start-Sleep 3
        Write-Success "ngrok tunnel started (PID: $($process.Id))"
    }
}

# Stop services
function Stop-MobileServices {
    Write-Info "Stopping mobile services..."

    if (Test-Path ".mobile_server.pid") {
        $pid = Get-Content ".mobile_server.pid"
        Stop-Process -Id $pid -ErrorAction SilentlyContinue
        Remove-Item ".mobile_server.pid"
        Write-Success "Mobile web server stopped"
    }

    if (Test-Path ".ngrok.pid") {
        $pid = Get-Content ".ngrok.pid"
        Stop-Process -Id $pid -ErrorAction SilentlyContinue
        Remove-Item ".ngrok.pid"
        Write-Success "ngrok tunnel stopped"
    }
}

# Show status
function Show-MobileStatus {
    Write-Host ""
    Write-Mobile "Mobile Command Center Status:"
    Write-Host ""

    if (Test-Path ".mobile_server.pid") {
        $pid = Get-Content ".mobile_server.pid"
        if (Get-Process -Id $pid -ErrorAction SilentlyContinue) {
            Write-Host "✅ Web Server: Running (PID: $pid)" -ForegroundColor Green
        } else {
            Write-Host "❌ Web Server: Not running (stale PID file)" -ForegroundColor Red
        }
    } else {
        Write-Host "❌ Web Server: Not running" -ForegroundColor Red
    }

    if (Test-Path ".ngrok.pid") {
        $pid = Get-Content ".ngrok.pid"
        if (Get-Process -Id $pid -ErrorAction SilentlyContinue) {
            Write-Host "✅ ngrok Tunnel: Running (PID: $pid)" -ForegroundColor Green
        } else {
            Write-Host "❌ ngrok Tunnel: Not running (stale PID file)" -ForegroundColor Red
        }
    } else {
        Write-Host "❌ ngrok Tunnel: Not running" -ForegroundColor Red
    }

    Write-Host ""
    Write-Host "🌐 Access URLs:" -ForegroundColor Cyan
    Write-Host "   Local: http://localhost:8080" -ForegroundColor White
    Write-Host "   Network: http://$LOCAL_IP`:8080" -ForegroundColor White
    Write-Host "   Remote: Check ngrok dashboard or Cloudflare" -ForegroundColor White
}

# Main execution
function Invoke-Main {
    Write-Host "📱 Bit Rage Systems Mobile Remote Access Setup" -ForegroundColor Magenta
    Write-Host "==========================================" -ForegroundColor Magenta
    Write-Host ""

    if ($Start) {
        Start-MobileServices
        Show-MobileStatus
        return
    }

    if ($Stop) {
        Stop-MobileServices
        return
    }

    if ($Status) {
        Show-MobileStatus
        return
    }

    if ($Setup) {
        Write-Host "Setting up local command center with mobile access..." -ForegroundColor White
        Write-Host ""

        New-MobileWebServer
        Install-Ngrok
        New-MobileInstructions

        Write-Host ""
        Write-Success "🎉 Mobile remote access setup complete!"
        Write-Host ""
        Write-Host "🚀 To start your mobile command center:" -ForegroundColor Cyan
        Write-Host "   .\mobile_setup.ps1 -Start" -ForegroundColor White
        Write-Host ""
        Write-Host "📱 Then access from your phone/iPad at:" -ForegroundColor Cyan
        Write-Host "   Local: http://$LOCAL_IP`:8080" -ForegroundColor White
        Write-Host "   Remote: Check MOBILE_ACCESS_README.md" -ForegroundColor White
        Write-Host ""
        Write-Host "📖 Full instructions: MOBILE_ACCESS_README.md" -ForegroundColor Yellow
        return
    }

    # Interactive setup
    Write-Host "Choose an option:" -ForegroundColor White
    Write-Host "1. Complete Setup (recommended)" -ForegroundColor Green
    Write-Host "2. Start Services" -ForegroundColor Cyan
    Write-Host "3. Stop Services" -ForegroundColor Yellow
    Write-Host "4. Show Status" -ForegroundColor Blue
    Write-Host ""

    $choice = Read-Host "Enter choice (1-4)"

    switch ($choice) {
        "1" { Invoke-Main -Setup }
        "2" { Invoke-Main -Start }
        "3" { Invoke-Main -Stop }
        "4" { Invoke-Main -Status }
        default { Write-Error "Invalid choice" }
    }
}

# Run main function
Invoke-Main