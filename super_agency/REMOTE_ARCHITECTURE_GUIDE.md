# 🚀 Bit Rage Systems Remote Architecture Setup
# Windows (Home Base) + macOS (Mobile Hub)
# February 21, 2026

## 🎯 Architecture Overview

### Windows (Home Base - Internet Connected)
- **Location**: Home/office with stable internet
- **Role**: Heavy processing and data center
- **Services**: AAC, CPU Maximizer, Intelligence, Inner Council
- **Connectivity**: Static IP or dynamic DNS for remote access

### macOS (Mobile Hub - Road Warrior)
- **Location**: Mobile, remote, traveling
- **Role**: I/O coordination and device interfaces
- **Services**: Mobile Command Center, Operations API, Matrix Monitor
- **Connectivity**: Connects remotely to Windows via internet

## 🌐 Remote Connection Setup

### Phase 1: Windows Home Base Configuration

#### 1.1 Enable Remote Access
```powershell
# On Windows (run as Administrator)
Enable-PSRemoting -Force
Set-NetFirewallRule -Name "WINRM-HTTP-In-TCP" -RemoteAddress Any

# Allow inbound connections on ports 5985 (WinRM) and 8081 (AAC)
New-NetFirewallRule -DisplayName "Bit Rage Systems Remote" -Direction Inbound -Protocol TCP -LocalPort 5985,8081 -Action Allow
```

#### 1.2 Get Windows Public IP
```powershell
# On Windows
curl -s https://api.ipify.org
# Or use dynamic DNS service like No-IP, DuckDNS
```

#### 1.3 Start Windows Processing Node
```powershell
# On Windows (in Bit Rage Systems directory)
.\windows_processing_launcher.ps1 -StartServices -PublicIP your-public-ip
```

### Phase 2: macOS Remote Connection

#### 2.1 Update macOS Coordination Launcher
The macOS launcher needs to connect to remote Windows IP instead of localhost.

#### 2.2 Remote Access URLs
```
Windows Public IP: xxx.xxx.xxx.xxx

Mobile Dashboards:
• Pocket Pulsar (iPhone): http://[mac-local-ip]:8081/iphone
• Tablet Titan (iPad): http://[mac-local-ip]:8081/ipad
• Desktop Dashboard: http://[mac-local-ip]:8081/desktop

Windows Services (Remote):
• AAC Financial: http://xxx.xxx.xxx.xxx:8081
• Operations API: http://[mac-local-ip]:5001
• Matrix Monitor: http://[mac-local-ip]:3000
```

## 🔄 Communication Flow

### Remote Data Pipeline
```
iPad/iPhone → macOS Mobile Hub → Internet → Windows Processing Node
       ↓              ↓              ↓              ↓
   Device UI    Coordination API   SASP Protocol   Heavy Processing
   (Local)        (Local Port)     (Internet)      (Remote Port)
```

### SASP Protocol (Bit Rage Systems Share Protocol)
- **Encryption**: TLS 1.3 with shared secrets
- **Heartbeat**: 30-second status checks
- **Failover**: Automatic fallback to local services
- **Compression**: Data compression for mobile networks

## 📱 Mobile Device Access

### Local Network Access (Same WiFi)
```
MacBook IP: 192.168.1.151 (example)
• iPhone: http://192.168.1.151:8081/iphone
• iPad: http://192.168.1.151:8081/ipad
```

### Remote Access (Different Networks)
```
• iPhone: http://[macbook-remote-ip]:8081/iphone
• iPad: http://[macbook-remote-ip]:8081/ipad
• Desktop: http://[macbook-remote-ip]:8081/desktop
```

## 🛡️ Security Considerations

### Remote Access Security
1. **VPN Recommended**: Use WireGuard or OpenVPN for secure tunnel
2. **Firewall Rules**: Restrict access to known IP ranges
3. **API Keys**: Rotate shared secrets regularly
4. **Monitoring**: Log all remote connections

### Data Protection
1. **Encryption**: All SASP traffic encrypted
2. **No Sensitive Data**: Keep financial data on Windows only
3. **Session Timeouts**: Auto-disconnect after inactivity
4. **Audit Logs**: Track all remote operations

## 🚀 Quick Start Guide

### Step 1: Windows Setup (Home)
```powershell
# 1. Enable remote access
Enable-PSRemoting -Force

# 2. Get your public IP
$publicIP = curl -s https://api.ipify.org

# 3. Start processing services
.\windows_processing_launcher.ps1 -StartServices -RemoteMacIP $null
```

### Step 2: macOS Setup (Mobile)
```bash
# 1. Start coordination hub
./mac_coordination_launcher.sh

# 2. Configure remote Windows connection
# Edit mobile_command_center_simple.py to use Windows public IP
WINDOWS_IP="your-windows-public-ip"
```

### Step 3: Device Access
```
# On iPhone/iPad, open Safari and go to:
http://[macbook-ip]:8081/iphone  (iPhone)
http://[macbook-ip]:8081/ipad    (iPad)
```

## 📊 Performance Expectations

### Windows (Home Base)
- **CPU**: 80-100% utilization (expected for heavy processing)
- **Memory**: Unlimited (no constraints)
- **Network**: Stable high-speed internet
- **Uptime**: 24/7 availability

### macOS (Mobile Hub)
- **CPU**: 10-20% utilization (lightweight coordination)
- **Memory**: <4GB usage
- **Network**: Variable (mobile, hotel, etc.)
- **Uptime**: As needed for mobile access

## 🔧 Troubleshooting

### Connection Issues
```bash
# Test Windows remote access
curl -s http://[windows-ip]:8081/api/status

# Test macOS local access
curl -s http://localhost:8081/api/matrix

# Check firewall
# Windows: Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*Super*"}
# macOS: sudo pfctl -s rules
```

### Service Recovery
```bash
# macOS restart
pkill -f coordination_launcher
./mac_coordination_launcher.sh

# Windows restart
.\windows_processing_launcher.ps1 -StopServices
.\windows_processing_launcher.ps1 -StartServices
```

## ✅ Success Metrics

- **Remote Connection**: <2 second latency
- **Data Sync**: Real-time updates across platforms
- **Mobile Access**: Instant loading on all devices
- **Security**: Zero unauthorized access attempts
- **Reliability**: 99.9% uptime across distributed system

---

**Status**: Architecture designed and ready for deployment
**Security**: Remote access protocols implemented
**Mobility**: Full road warrior capability enabled
