# Windows Sync Script for MacBook Operations
# Heavy lifting on Windows, operations on Mac
# Implements Bit Rage Systems Share Protocol (SASP)

param(
    [string]$MacIP = "auto-detect",
    [switch]$StartServices,
    [switch]$StopServices,
    [switch]$Status
)

# SASP Protocol Configuration
$SASP_CONFIG = @{
    Version = "1.0"
    Protocol = "SASP"
    WindowsId = "windows-node-$(Get-Random)"
    SharedSecret = "super-agency-shared-key-2026"  # Should be configured securely
    HeartbeatInterval = 30
    MaxRetries = 5
    RetryDelay = 1
}

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

# SASP Message Functions
function New-SASPMessage {
    param(
        [string]$MessageType,
        [object]$Payload,
        [string]$RecipientType = "mac",
        [string]$RecipientId = "mac-hub"
    )

    $timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    $messageId = [guid]::NewGuid().ToString()

    $message = @{
        protocol = $SASP_CONFIG.Protocol
        version = $SASP_CONFIG.Version
        timestamp = $timestamp
        message_id = $messageId
        sender = @{
            type = "windows"
            id = $SASP_CONFIG.WindowsId
            ip = (Get-NetIPAddress | Where-Object { $_.AddressFamily -eq "IPv4" -and $_.IPAddress -notlike "127.*" } | Select-Object -First 1).IPAddress
        }
        recipient = @{
            type = $RecipientType
            id = $RecipientId
        }
        message_type = $MessageType
        payload = $Payload
    }

    # Add HMAC signature
    $message.signature = Get-SASPSignature $message

    return $message
}

function Get-SASPSignature {
    param([object]$Message)

    # Remove signature field for signing
    $messageCopy = $Message.PSObject.Copy()
    $messageCopy.PSObject.Properties.Remove('signature')

    # Create string to sign
    $jsonString = $messageCopy | ConvertTo-Json -Depth 10 -Compress

    # Create HMAC-SHA256 signature
    $hmac = New-Object System.Security.Cryptography.HMACSHA256
    $hmac.Key = [System.Text.Encoding]::UTF8.GetBytes($SASP_CONFIG.SharedSecret)
    $signature = $hmac.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($jsonString))
    $signatureString = [BitConverter]::ToString($signature).Replace("-", "").ToLower()

    return $signatureString
}

function Send-SASPMessage {
    param(
        [object]$Message,
        [string]$Endpoint,
        [int]$Retries = $SASP_CONFIG.MaxRetries
    )

    $url = "http://$MacIP`:8080/sasp/$Endpoint"
    $jsonMessage = $Message | ConvertTo-Json -Depth 10 -Compress

    for ($attempt = 1; $attempt -le $Retries; $attempt++) {
        try {
            $response = Invoke-WebRequest -Uri $url -Method POST -Body $jsonMessage -ContentType "application/json" -TimeoutSec 10
            return $response
        } catch {
            if ($attempt -eq $Retries) {
                Write-Error "Failed to send SASP message after $Retries attempts: $($_.Exception.Message)"
                return $null
            }

            $delay = $SASP_CONFIG.RetryDelay * [math]::Pow(2, $attempt - 1)
            Write-Warning "SASP message attempt $attempt failed, retrying in $delay seconds..."
            Start-Sleep -Seconds $delay
        }
    }
}

function Send-SASPStatus {
    param([string]$MacIP)

    $systemInfo = Get-SystemInfo
    $statusMessage = New-SASPMessage -MessageType "status" -Payload $systemInfo
    $response = Send-SASPMessage -Message $statusMessage -Endpoint "status"

    if ($response) {
        Write-Success "Status sent to Mac hub"
    }
}

function Get-SystemInfo {
    # Get CPU usage
    $cpuUsage = (Get-Counter '\Processor(_Total)\% Processor Time' -ErrorAction SilentlyContinue).CounterSamples.CookedValue
    if (-not $cpuUsage) { $cpuUsage = 0 }

    # Get memory usage
    $memory = Get-CimInstance Win32_OperatingSystem
    $totalMemory = [math]::Round($memory.TotalVisibleMemorySize / 1MB, 2)
    $freeMemory = [math]::Round($memory.FreePhysicalMemory / 1MB, 2)
    $usedMemory = $totalMemory - $freeMemory

    # Get disk space
    $disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
    $freeDisk = [math]::Round($disk.FreeSpace / 1GB, 2)

    # Check running services
    $services = @{
        aac_system = if (Test-Path ".aac_pid.txt") { "running" } else { "stopped" }
        cpu_maximizer = if (Test-Path ".cpu_pid.txt") { "running" } else { "stopped" }
        intelligence = if (Test-Path ".intel_pid.txt") { "running" } else { "stopped" }
        inner_council = if (Test-Path ".council_pid.txt") { "running" } else { "stopped" }
    }

    return @{
        system_status = "operational"
        services = $services
        resources = @{
            cpu_percent = [math]::Round($cpuUsage, 1)
            memory_total_gb = $totalMemory
            memory_used_gb = $usedMemory
            disk_free_gb = $freeDisk
        }
        timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    }
}

function Start-SASPHeartbeat {
    param([string]$MacIP)

    Write-Info "Starting SASP heartbeat (every $($SASP_CONFIG.HeartbeatInterval)s)"

    $scriptBlock = {
        param($MacIP, $Config)

        while ($true) {
            try {
                $systemInfo = Get-SystemInfo
                $heartbeatMessage = New-SASPMessage -MessageType "status" -Payload $systemInfo
                Send-SASPMessage -Message $heartbeatMessage -Endpoint "status" -Retries 1 | Out-Null
            } catch {
                # Silently continue on heartbeat failures
            }

            Start-Sleep -Seconds $Config.HeartbeatInterval
        }
    }

    # Start heartbeat in background job
    Start-Job -ScriptBlock $scriptBlock -ArgumentList $MacIP, $SASP_CONFIG -Name "SASPHeartbeat" | Out-Null
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

# Auto-detect Mac IP
function Get-MacIP {
    # Try common local network ranges
    $networks = @("192.168.1", "192.168.0", "10.0.0", "172.16.0")

    foreach ($network in $networks) {
        for ($i = 1; $i -le 254; $i++) {
            $ip = "$network.$i"
            try {
                $tcpClient = New-Object System.Net.Sockets.TcpClient
                $tcpClient.Connect($ip, 8080)
                $tcpClient.Close()
                Write-Success "Found Mac at: $ip"
                return $ip
            } catch {
                # Continue scanning
            }
        }
    }

    Write-Warning "Mac not auto-detected. Using default IP."
    return "192.168.1.100"  # Default - user should update
}

# Test Mac connectivity
function Test-MacConnection {
    param([string]$IP)

    $endpoints = @{
        "Mobile Center" = "http://$IP`:8080"
        "Operations" = "http://$IP`:5000"
        "Matrix Monitor" = "http://$IP`:3000"
    }

    Write-Info "Testing Mac connectivity..."

    foreach ($service in $endpoints.Keys) {
        try {
            $response = Invoke-WebRequest -Uri $endpoints[$service] -TimeoutSec 5 -ErrorAction Stop
            Write-Success "$service connected"
        } catch {
            Write-Warning "$service unreachable at $($endpoints[$service])"
        }
    }
}

# Start Windows heavy services
function Start-WindowsServices {
    Write-Info "Starting Windows heavy computation services..."

    # Start AAC System (memory intensive)
    if (Test-Path "repos\AAC\aac_dashboard.py") {
        Write-Info "Starting AAC Financial System..."
        $aacProcess = Start-Process python -ArgumentList "repos\AAC\aac_dashboard.py" -NoNewWindow -PassThru
        $aacProcess.Id | Out-File -FilePath ".aac_pid.txt"
        Write-Success "AAC System started (PID: $($aacProcess.Id))"
    }

    # Start CPU Maximizer
    if (Test-Path "cpu_maximizer.py") {
        Write-Info "Starting CPU Maximizer..."
        $cpuProcess = Start-Process python -ArgumentList "cpu_maximizer.py" -NoNewWindow -PassThru
        $cpuProcess.Id | Out-File -FilePath ".cpu_pid.txt"
        Write-Success "CPU Maximizer started (PID: $($cpuProcess.Id))"
    }

    # Start Intelligence Gathering
    if (Test-Path "youtube_intelligence_monitor.py") {
        Write-Info "Starting Intelligence Monitor..."
        $intelProcess = Start-Process python -ArgumentList "youtube_intelligence_monitor.py" -NoNewWindow -PassThru
        $intelProcess.Id | Out-File -FilePath ".intel_pid.txt"
        Write-Success "Intelligence Monitor started (PID: $($intelProcess.Id))"
    }

    # Start Inner Council (limited agents for Windows)
    if (Test-Path "inner_council\deploy_agents.py") {
        Write-Info "Starting Inner Council agents (Windows capacity)..."
        $councilProcess = Start-Process python -ArgumentList "inner_council\deploy_agents.py --mode deploy --duration 0 --max-agents 4" -NoNewWindow -PassThru
        $councilProcess.Id | Out-File -FilePath ".council_pid.txt"
        Write-Success "Inner Council started (PID: $($councilProcess.Id))"
    }
}

# Stop Windows services
function Stop-WindowsServices {
    Write-Info "Stopping Windows services..."

    $pids = @(".aac_pid.txt", ".cpu_pid.txt", ".intel_pid.txt", ".council_pid.txt")

    foreach ($pidFile in $pids) {
        if (Test-Path $pidFile) {
            $pid = Get-Content $pidFile
            try {
                Stop-Process -Id $pid -Force -ErrorAction Stop
                Write-Success "Stopped process $pid"
            } catch {
                Write-Warning "Could not stop process $pid"
            }
            Remove-Item $pidFile
        }
    }
}

# Show status
function Show-Status {
    Write-Info "Bit Rage Systems Distributed Status"
    Write-Host "=================================" -ForegroundColor Cyan

    # Check Windows services
    Write-Host "Windows Services:" -ForegroundColor Yellow
    $services = @(
        @{Name="AAC System"; PID=".aac_pid.txt"},
        @{Name="CPU Maximizer"; PID=".cpu_pid.txt"},
        @{Name="Intelligence"; PID=".intel_pid.txt"},
        @{Name="Inner Council"; PID=".council_pid.txt"}
    )

    foreach ($service in $services) {
        if (Test-Path $service.PID) {
            $pid = Get-Content $service.PID
            if (Get-Process -Id $pid -ErrorAction SilentlyContinue) {
                Write-Host "  ✅ $($service.Name) running (PID: $pid)" -ForegroundColor Green
            } else {
                Write-Host "  ❌ $($service.Name) stopped" -ForegroundColor Red
                Remove-Item $service.PID
            }
        } else {
            Write-Host "  ⏸️ $($service.Name) not started" -ForegroundColor Gray
        }
    }

    # Check Mac connectivity
    Write-Host "`nMac Connectivity:" -ForegroundColor Yellow
    $macIP = if (Test-Path ".mac_ip.txt") { Get-Content ".mac_ip.txt" } else { "unknown" }
    Write-Host "  📍 Mac IP: $macIP" -ForegroundColor White

    if ($macIP -ne "unknown") {
        Test-MacConnection $macIP
    } else {
        Write-Warning "Mac IP not configured. Run sync with -MacIP parameter"
    }
}

# Main logic
if ($Status) {
    Show-Status
    exit
}

if ($StopServices) {
    Stop-WindowsServices
    # Stop heartbeat job
    Get-Job -Name "SASPHeartbeat" -ErrorAction SilentlyContinue | Stop-Job -ErrorAction SilentlyContinue
    Get-Job -Name "SASPHeartbeat" -ErrorAction SilentlyContinue | Remove-Job -ErrorAction SilentlyContinue
    exit
}

# Determine Mac IP
$macIP = if ($MacIP -eq "auto-detect") { Get-MacIP } else { $MacIP }

# Save Mac IP for future use
$macIP | Out-File -FilePath ".mac_ip.txt"

Write-Host "🔄 Bit Rage Systems Distributed Setup (SASP v$($SASP_CONFIG.Version))" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host "Mac IP: $macIP" -ForegroundColor White
Write-Host "Windows: Heavy computation" -ForegroundColor White
Write-Host "Mac: Operations & mobile access" -ForegroundColor White
Write-Host "Protocol: $($SASP_CONFIG.Protocol)" -ForegroundColor White
Write-Host ""

# Test connection and send initial status
Test-MacConnection $macIP
Send-SASPStatus $macIP

# Start services
if ($StartServices) {
    Start-WindowsServices
    # Start SASP heartbeat after services are running
    Start-SASPHeartbeat $macIP
}

Write-Host "`n🎯 Access Points:" -ForegroundColor Green
Write-Host "📱 Mobile Command Center: http://$macIP`:8080" -ForegroundColor White
Write-Host "⚙️ Operations Interface: http://$macIP`:5000" -ForegroundColor White
Write-Host "🧠 Matrix Monitor: http://$macIP`:3000" -ForegroundColor White
Write-Host "💰 AAC System: http://localhost:8081" -ForegroundColor White

Write-Host "`n💡 Commands:" -ForegroundColor Cyan
Write-Host "  .\sync_to_windows.ps1 -Status              # Check status" -ForegroundColor White
Write-Host "  .\sync_to_windows.ps1 -StartServices       # Start Windows services + SASP" -ForegroundColor White
Write-Host "  .\sync_to_windows.ps1 -StopServices        # Stop Windows services + SASP" -ForegroundColor White

Write-Success "Distributed setup complete with SASP protocol!"</content>
<parameter name="filePath">C:/Dev/SuperAgency-Shared/sync_to_windows.ps1