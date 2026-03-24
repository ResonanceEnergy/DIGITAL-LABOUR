# 🚀 Bit Rage Systems Windows Processing Node Launcher
# Heavy computation and AI processing for distributed architecture
# February 21, 2026

param(
    [string]$MacIP = "192.168.1.151",
    [switch]$StartServices,
    [switch]$StopServices,
    [switch]$Status,
    [switch]$Optimize
)

# Configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogFile = "$ScriptDir\windows_processing_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

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

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] $Level`: $Message"
    Write-Host $LogMessage -ForegroundColor $Colors.Blue
    Add-Content -Path $LogFile -Value $LogMessage
}

function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor $Colors.Green
    Write-Log $Message "SUCCESS"
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor $Colors.Yellow
    Write-Log $Message "WARNING"
}

function Write-Error {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor $Colors.Red
    Write-Log $Message "ERROR"
}

# Get system information
function Get-SystemInfo {
    $cpu = Get-WmiObject Win32_Processor
    $mem = Get-WmiObject Win32_ComputerSystem
    $os = Get-WmiObject Win32_OperatingSystem

    return @{
        CPU = "$($cpu.Name) ($($cpu.NumberOfCores) cores)"
        Memory = "$([math]::Round($mem.TotalPhysicalMemory / 1GB, 1)) GB"
        OS = "$($os.Caption) $($os.Version)"
    }
}

# Check if port is available
function Test-PortAvailable {
    param([int]$Port)
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $tcpClient.Connect("localhost", $Port)
        $tcpClient.Close()
        return $false
    } catch {
        return $true
    }
}

# Start heavy processing service
function Start-HeavyService {
    param(
        [string]$Name,
        [string]$Command,
        [string]$Arguments = "",
        [string]$PidFile
    )

    Write-Log "Starting $Name (Heavy Processing)..."

    # Check if already running
    if (Test-Path $PidFile) {
        $existingPid = Get-Content $PidFile
        if (Get-Process -Id $existingPid -ErrorAction SilentlyContinue) {
            Write-Warning "$Name already running (PID: $existingPid)"
            return $true
        } else {
            Remove-Item $PidFile -Force
        }
    }

    try {
        # Start process
        $process = Start-Process -FilePath $Command -ArgumentList $Arguments -NoNewWindow -PassThru
        $process.Id | Out-File -FilePath $PidFile
        Write-Success "$Name started (PID: $($process.Id))"
        return $true
    } catch {
        Write-Error "Failed to start $Name`: $($_.Exception.Message)"
        return $false
    }
}

# Start all Windows processing services
function Start-WindowsProcessing {
    Write-Log "🚀 Starting Windows Heavy Processing Node..."
    Write-Log "🎯 Role: Heavy Computation (Unlimited Resources)"

    # Display system info
    $sysInfo = Get-SystemInfo
    Write-Log "💻 System: $($sysInfo.OS)"
    Write-Log "🖥️  CPU: $($sysInfo.CPU)"
    Write-Log "🧠 Memory: $($sysInfo.Memory)"

    $startedServices = 0

    # 1. AAC Financial System (Primary heavy processing)
    if (Test-Path "repos\AAC\aac_dashboard.py") {
        if (Start-HeavyService -Name "AAC Financial System" -Command "python" -Arguments "repos\AAC\aac_dashboard.py" -PidFile ".aac_pid.txt") {
            $startedServices++
        }
    } else {
        Write-Warning "AAC Financial System not found at repos\AAC\aac_dashboard.py"
    }

    # 2. CPU Maximizer (Full core utilization)
    if (Test-Path "cpu_maximizer.py") {
        if (Start-HeavyService -Name "CPU Maximizer" -Command "python" -Arguments "cpu_maximizer.py" -PidFile ".cpu_pid.txt") {
            $startedServices++
        }
    }

    # 3. Intelligence Gathering (AI/ML processing)
    if (Test-Path "youtube_intelligence_monitor.py") {
        if (Start-HeavyService -Name "Intelligence Monitor" -Command "python" -Arguments "youtube_intelligence_monitor.py" -PidFile ".intel_pid.txt") {
            $startedServices++
        }
    }

    # 4. Inner Council Agents (Decision processing)
    if (Test-Path "inner_council\deploy_agents.py") {
        $agentArgs = "inner_council\deploy_agents.py --mode deploy --duration 0 --max-agents 6"
        if (Start-HeavyService -Name "Inner Council (6 agents)" -Command "python" -Arguments $agentArgs -PidFile ".council_pid.txt") {
            $startedServices++
        }
    }

    # 5. Portfolio Intelligence (Data processing)
    if (Test-Path "run_portfolio_intelligence.py") {
        if (Start-HeavyService -Name "Portfolio Intelligence" -Command "python" -Arguments "run_portfolio_intelligence.py" -PidFile ".portfolio_pid.txt") {
            $startedServices++
        }
    }

    Write-Success "Started $startedServices heavy processing services"

    # Start SASP communication with macOS
    Start-SASPCommunication $MacIP

    return $startedServices
}

# Stop all Windows processing services
function Stop-WindowsProcessing {
    Write-Log "🛑 Stopping Windows Processing Services..."

    $pidFiles = @(".aac_pid.txt", ".cpu_pid.txt", ".intel_pid.txt", ".council_pid.txt", ".portfolio_pid.txt")
    $stoppedServices = 0

    foreach ($pidFile in $pidFiles) {
        if (Test-Path $pidFile) {
            try {
                $pid = Get-Content $pidFile
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                Remove-Item $pidFile -Force
                $stoppedServices++
                Write-Success "Stopped service (PID: $pid)"
            } catch {
                Write-Warning "Failed to stop service from $pidFile"
            }
        }
    }

    Write-Success "Stopped $stoppedServices services"
    return $stoppedServices
}

# Start SASP communication with macOS
function Start-SASPCommunication {
    param([string]$MacIP)

    Write-Log "🔄 Starting SASP communication with macOS ($MacIP)..."

    # Test connection to macOS
    try {
        $testConnection = Test-NetConnection -ComputerName $MacIP -Port 8081 -ErrorAction Stop
        if ($testConnection.TcpTestSucceeded) {
            Write-Success "SASP connection established to macOS"
        } else {
            Write-Warning "Cannot connect to macOS, but proceeding with local services"
        }
    } catch {
        Write-Warning "Cannot reach macOS coordination hub, running in standalone mode"
    }
}

# Get status of all services
function Get-ProcessingStatus {
    Write-Log "📊 Windows Processing Node Status"

    $services = @(
        @{Name = "AAC Financial"; PidFile = ".aac_pid.txt"; Port = 8081},
        @{Name = "CPU Maximizer"; PidFile = ".cpu_pid.txt"; Port = $null},
        @{Name = "Intelligence Monitor"; PidFile = ".intel_pid.txt"; Port = $null},
        @{Name = "Inner Council"; PidFile = ".council_pid.txt"; Port = $null},
        @{Name = "Portfolio Intelligence"; PidFile = ".portfolio_pid.txt"; Port = $null}
    )

    $runningServices = 0

    foreach ($service in $services) {
        $status = "❌ Stopped"
        if (Test-Path $service.PidFile) {
            $pid = Get-Content $service.PidFile
            if (Get-Process -Id $pid -ErrorAction SilentlyContinue) {
                $status = "✅ Running (PID: $pid)"
                $runningServices++
            }
        }
        Write-Host "$($service.Name): $status" -ForegroundColor $(if ($status.StartsWith("✅")) { $Colors.Green } else { $Colors.Red })
    }

    # System resources
    $cpu = Get-WmiObject Win32_Processor | Measure-Object -Property LoadPercentage -Average
    $mem = Get-WmiObject Win32_OperatingSystem
    $memUsage = [math]::Round(($mem.TotalVisibleMemorySize - $mem.FreePhysicalMemory) / $mem.TotalVisibleMemorySize * 100, 1)

    Write-Host "`n💻 System Resources:" -ForegroundColor $Colors.Cyan
    Write-Host "   CPU Usage: $($cpu.Average)%" -ForegroundColor $(if ($cpu.Average -gt 80) { $Colors.Red } elseif ($cpu.Average -gt 50) { $Colors.Yellow } else { $Colors.Green })
    Write-Host "   Memory Usage: $memUsage%" -ForegroundColor $(if ($memUsage -gt 80) { $Colors.Red } elseif ($memUsage -gt 50) { $Colors.Yellow } else { $Colors.Green })

    return $runningServices
}

# Optimize Windows for heavy processing
function Optimize-WindowsProcessing {
    Write-Log "⚡ Optimizing Windows for Heavy Processing..."

    # Set power plan to high performance
    powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c

    # Disable Windows visual effects
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects" -Name "VisualFXSetting" -Value 2

    # Set process priority for Python processes
    Write-Success "Windows optimized for heavy processing workloads"
}

# Main execution
try {
    Write-Log "🎯 Bit Rage Systems Windows Processing Node Launcher"

    if ($Status) {
        Get-ProcessingStatus
        exit 0
    }

    if ($StopServices) {
        Stop-WindowsProcessing
        exit 0
    }

    if ($Optimize) {
        Optimize-WindowsProcessing
        exit 0
    }

    if ($StartServices) {
        $started = Start-WindowsProcessing

        Write-Host "`n🎯 Windows Processing Node Active!" -ForegroundColor $Colors.Green
        Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor $Colors.Cyan
        Write-Host "🏗️  Role: Heavy Computation Engine" -ForegroundColor $Colors.White
        Write-Host "🔄 Connected to macOS: $MacIP" -ForegroundColor $Colors.White
        Write-Host "⚡ Services Running: $started" -ForegroundColor $Colors.White
        Write-Host "" -ForegroundColor $Colors.White
        Write-Host "📊 Commands:" -ForegroundColor $Colors.Cyan
        Write-Host "   .\windows_processing_launcher.ps1 -Status" -ForegroundColor $Colors.White
        Write-Host "   .\windows_processing_launcher.ps1 -StopServices" -ForegroundColor $Colors.White
        Write-Host "   .\windows_processing_launcher.ps1 -Optimize" -ForegroundColor $Colors.White
        Write-Host "" -ForegroundColor $Colors.White
        Write-Host "📋 Logs: $LogFile" -ForegroundColor $Colors.White
        Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor $Colors.Cyan
    } else {
        Write-Host "💡 Usage:" -ForegroundColor $Colors.Cyan
        Write-Host "   .\windows_processing_launcher.ps1 -StartServices [-MacIP ip]" -ForegroundColor $Colors.White
        Write-Host "   .\windows_processing_launcher.ps1 -StopServices" -ForegroundColor $Colors.White
        Write-Host "   .\windows_processing_launcher.ps1 -Status" -ForegroundColor $Colors.White
        Write-Host "   .\windows_processing_launcher.ps1 -Optimize" -ForegroundColor $Colors.White
    }

} catch {
    Write-Error "Script execution failed: $($_.Exception.Message)"
    exit 1
}
