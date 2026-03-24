# Bit Rage Systems Local Execution Guide
## Step-by-Step Instructions for Running Locally & Tracking Progress

**Version 2.0 - Maximum CPU Utilization Era**
**Date: February 20, 2026**

---

## 🚀 QUICK START (3 Minutes to Full Operation)

### Linux/macOS
```bash
# Make executable and run full system
chmod +x run_locally.sh
./run_locally.sh full
```

### Windows
```batch
# Run full system
run_locally.bat full
```

### Python Direct
```bash
# Run full system
python run_locally.py full
```

**Result**: Complete Bit Rage Systems deployment in under 3 minutes!

---

## 📋 DETAILED STEP-BY-STEP GUIDE

### Step 1: Prerequisites Check

#### 1.1 Verify System Requirements
```bash
# Linux/macOS
./run_locally.sh deps

# Windows
run_locally.bat deps

# Manual check
python --version  # Should be 3.7+
nproc             # CPU cores (4+ recommended)
free -h          # RAM (8GB+ recommended)
```

**Expected Output:**
```
[INFO] Python found: Python 3.9.7
[INFO] Required Python packages available
[INFO] System Resources: 8 CPU cores, 16GB RAM
[SUCCESS] Dependencies check completed
```

#### 1.2 Install Missing Dependencies (if needed)
```bash
# Install Python packages for AAC
cd repos/AAC
pip install -r requirements.txt

# Install Flask for web dashboard
pip install flask
```

---

### Step 2: Start Inner Council (Intelligence Gathering)

#### Option A: Using Runner Script
```bash
# Linux/macOS
./run_locally.sh council

# Windows
run_locally.bat council
```

#### Option B: Manual Start
```bash
cd inner_council
python deploy_agents.py --mode deploy --duration 300
```

**What happens:**
- Deploys 6 autonomous agents
- Starts intelligence gathering across repositories
- Initializes decision-making framework
- Creates monitoring and reporting systems

**Expected Output:**
```
========================================
STARTING INNER COUNCIL
========================================
[INFO] Deploying Inner Council agents...
[SUCCESS] Inner Council agents deployed
```

---

### Step 3: Start AAC Financial System

#### Option A: Using Runner Script
```bash
# Linux/macOS
./run_locally.sh aac

# Windows
run_locally.bat aac
```

#### Option B: Manual Start
```bash
cd repos/AAC

# Initialize database
python aac_engine.py

# Start compliance monitoring
python aac_compliance.py &

# Start financial intelligence
python aac_intelligence.py &

# Start web dashboard
python run_aac.py --web &
```

**What happens:**
- Initializes SQLite accounting database
- Starts automated compliance monitoring
- Launches financial intelligence analysis
- Deploys web dashboard at http://localhost:5000

**Expected Output:**
```
========================================
STARTING AAC FINANCIAL SYSTEM
========================================
[SUCCESS] AAC engine initialized
[SUCCESS] AAC system started - Dashboard at http://localhost:5000
```

---

### Step 4: Run CPU Maximization

#### Option A: Using Runner Script (Recommended)
```bash
# Maximum overdrive (100% CPU, 5 minutes)
./run_locally.sh cpu maximum 5

# Balanced processing (70-90% CPU, 15 minutes)
./run_locally.sh cpu balanced 15

# Windows
run_locally.bat cpu maximum 5
```

#### Option B: Manual Start
```bash
# Maximum mode
python cpu_control_center.py maximum --duration 10

# Balanced mode
python cpu_control_center.py balanced --duration 15

# Diagnostic mode (test all systems)
python cpu_control_center.py diagnostic
```

#### Option C: Advanced Control
```bash
# Batch processing (50 cycles)
python batch_processor.py --cycles 50

# Continuous processing (1 hour)
python batch_processor.py --continuous 60

# Parallel orchestrator only
python parallel_orchestrator.py
```

**What happens:**
- Launches all systems simultaneously
- Utilizes all available CPU cores
- Processes repositories in parallel
- Monitors performance in real-time

**Expected Output:**
```
========================================
STARTING CPU MAXIMIZATION (maximum mode, 5min)
========================================
[SUCCESS] CPU maximization completed
Peak CPU: 98.5% | Average CPU: 87.3%
```

---

### Step 5: Run Daily Operations

#### Option A: Using Runner Script
```bash
# Linux/macOS
./run_locally.sh daily

# Windows
run_locally.bat daily
```

#### Option B: Manual Start
```bash
# Run complete daily cycle
./bin/run_daily.sh

# Or run components individually
cd inner_council
python agents/repo_sentry.py
python agents/daily_brief.py
```

**What happens:**
- Executes repository analysis
- Generates intelligence reports
- Updates financial records
- Creates operational summaries

---

### Step 6: Monitor System Performance

#### Real-time Monitoring
```bash
# Monitor for 5 minutes
./run_locally.sh monitor 300

# Windows
run_locally.bat monitor 300
```

#### View Live Metrics
```bash
# Watch system metrics in real-time
tail -f monitoring/system_metrics.log

# Windows PowerShell
Get-Content monitoring\system_metrics.log -Wait
```

**Monitoring Output:**
```
2026-02-20 14:30:15|CPU:87.3%|MEM:68.4%|PROCESSES:12
2026-02-20 14:30:20|CPU:92.1%|MEM:71.2%|PROCESSES:14
2026-02-20 14:30:25|CPU:89.7%|MEM:69.8%|PROCESSES:13
```

#### Performance Dashboard
```bash
# View web dashboard
open http://localhost:5000  # AAC Financial Dashboard

# Check Inner Council status
cd inner_council && python monitor_agents.py
```

---

### Step 7: Generate Reports & Track Progress

#### Automatic Report Generation
```bash
# Generate comprehensive report
./run_locally.sh reports

# Windows
run_locally.bat reports
```

#### View Progress Logs
```bash
# View progress tracking
cat .super_agency_progress

# View recent activity
tail -20 .super_agency_progress

# Windows
type .super_agency_progress
```

**Progress Tracking Output:**
```
2026-02-20 14:25:30|inner_council|STARTED|Deploying autonomous agents
2026-02-20 14:26:15|inner_council|COMPLETED|Agents deployed successfully
2026-02-20 14:26:20|aac_system|STARTED|Initializing financial operations
2026-02-20 14:27:45|aac_system|COMPLETED|AAC system fully operational
2026-02-20 14:27:50|cpu_maximization|STARTED|Mode: maximum, Duration: 5min
2026-02-20 14:32:50|cpu_maximization|COMPLETED|CPU maximization completed successfully
```

#### Report Contents
Generated reports include:
- System resource utilization
- Performance metrics over time
- Component status and health
- Error logs and warnings
- Recommendations for optimization

---

## 🎯 INTERACTIVE MODE (Step-by-Step Control)

### Linux/macOS Interactive
```bash
./run_locally.sh
```

### Windows Interactive
```batch
run_locally.bat
```

**Interactive Menu Options:**
1. **Run Full System** - Complete deployment (recommended)
2. **Start Inner Council Only** - Intelligence agents only
3. **Start AAC System Only** - Financial system only
4. **Run CPU Maximization Only** - Performance optimization only
5. **Run Daily Operations** - Standard operational cycle
6. **Monitor System** - Real-time performance monitoring
7. **Generate Reports** - Create comprehensive reports
8. **Cleanup Processes** - Stop all running processes

---

## 📊 TRACKING PROGRESS & METRICS

### Real-Time Progress Tracking

#### 1. Command Line Monitoring
```bash
# Watch progress in real-time
watch -n 5 'tail -5 .super_agency_progress'

# Windows PowerShell
while ($true) { Get-Content .super_agency_progress -Tail 5; Start-Sleep 5; Clear-Host }
```

#### 2. Performance Metrics
```bash
# CPU and memory usage
top -p $(pgrep -f "python.*super")

# Process monitoring
ps aux | grep python | grep -E "(aac_|cpu_|inner_council)"

# Windows
tasklist /fi "imagename eq python.exe"
```

#### 3. System Health Checks
```bash
# Check all services
curl -s http://localhost:5000 > /dev/null && echo "AAC Dashboard: OK" || echo "AAC Dashboard: DOWN"

# Check database
cd repos/AAC && python -c "import sqlite3; sqlite3.connect('aac_accounting.db').close()" && echo "AAC DB: OK"

# Check Inner Council
cd inner_council && python -c "import json; print('Inner Council config:', json.load(open('config/settings.json'))['name'])" 2>/dev/null && echo "Inner Council: OK"
```

### Key Performance Indicators (KPIs)

#### CPU Utilization Metrics
- **Maximum Mode**: 95-100% CPU usage
- **Balanced Mode**: 70-90% CPU usage
- **Idle State**: <20% CPU usage

#### Memory Utilization
- **Normal Operation**: 60-80% RAM usage
- **Peak Load**: 80-95% RAM usage
- **Stable Operation**: <85% RAM usage

#### Process Health
- **Active Processes**: 8-15 Python processes during full operation
- **Failed Processes**: 0 (automatic restart on failure)
- **Response Time**: <2 seconds average

#### Throughput Metrics
- **Repository Analysis**: 10-50 repos/minute
- **Financial Transactions**: 1000-5000 transactions/minute
- **Intelligence Reports**: 5-20 reports/minute

---

## 🔧 TROUBLESHOOTING & DEBUGGING

### Common Issues & Solutions

#### 1. Python Not Found
```bash
# Check Python installation
which python3
python3 --version

# Install Python if missing
# Ubuntu/Debian: sudo apt install python3 python3-pip
# macOS: brew install python3
# Windows: Download from python.org
```

#### 2. Port Conflicts
```bash
# Check if port 5000 is in use
lsof -i :5000

# Kill conflicting process
kill -9 $(lsof -ti :5000)

# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

#### 3. Permission Issues
```bash
# Make scripts executable
chmod +x run_locally.sh
chmod +x max_cpu.sh
chmod +x bin/*.sh

# Check directory permissions
ls -la .super_agency_progress
ls -la monitoring/
ls -la reports/
```

#### 4. Memory Issues
```bash
# Check available memory
free -h

# Kill memory-intensive processes
pkill -f "python.*cpu_maximizer"

# Windows
taskkill /f /im python.exe /fi "memusage gt 500000"
```

#### 5. Database Issues
```bash
cd repos/AAC

# Check database file
ls -la aac_accounting.db

# Reinitialize database
rm aac_accounting.db
python aac_engine.py
```

### Debug Mode Execution
```bash
# Run with verbose logging
export PYTHONPATH=$PWD
python -m logging.basicConfig(level=logging.DEBUG)
./run_locally.sh full

# Check detailed logs
tail -f monitoring/system_metrics.log
tail -f .super_agency_progress
```

---

## 🧹 CLEANUP & MAINTENANCE

### Stop All Processes
```bash
# Using runner script
./run_locally.sh cleanup

# Windows
run_locally.bat cleanup

# Manual cleanup
pkill -f "python.*super"
pkill -f "aac_"
pkill -f "cpu_maximizer"
```

### Clear Logs and Cache
```bash
# Clear monitoring data
rm -rf monitoring/*.log
rm -rf monitoring/*.pid

# Clear progress logs
> .super_agency_progress

# Clear reports (optional)
rm -rf reports/*.md
```

### System Health Check
```bash
# Run diagnostic
python cpu_control_center.py diagnostic

# Check all components
./run_locally.sh deps
./run_locally.sh reports
```

---

## 📈 ADVANCED USAGE & OPTIMIZATION

### Custom CPU Maximization
```bash
# Custom worker count
python cpu_maximizer.py --workers 4

# Specific duration
python cpu_control_center.py maximum --duration 30

# PowerShell advanced mode
.\cpu_maximizer.ps1 -Processes 8 -Duration 20 -Mode maximum
```

### Batch Processing Optimization
```bash
# Large batch processing
python batch_processor.py --cycles 100 --batch-size 10

# Continuous operation
python batch_processor.py --continuous 120  # 2 hours
```

### Performance Tuning
```bash
# Increase system limits
ulimit -n 65536  # File descriptors
ulimit -u 2048   # Processes

# Optimize Python
export PYTHONOPTIMIZE=1
export PYTHONDONTWRITEBYTECODE=1
```

### Monitoring Enhancements
```bash
# Advanced monitoring
./run_locally.sh monitor 3600  # 1 hour monitoring

# Custom metrics
python -c "
import psutil
import time
while True:
    print(f'CPU: {psutil.cpu_percent()}%, MEM: {psutil.virtual_memory().percent}%, PROC: {len([p for p in psutil.process_iter() if \"python\" in p.name()])}')
    time.sleep(1)
"
```

---

## 🎯 SUCCESS METRICS & VALIDATION

### System Readiness Checklist
- [ ] Inner Council agents deployed and operational
- [ ] AAC database initialized and accessible
- [ ] Web dashboard responding at http://localhost:5000
- [ ] CPU utilization >70% during maximization
- [ ] All background processes running
- [ ] Progress logs being generated
- [ ] Reports generating successfully

### Performance Validation
```bash
# Quick validation script
python -c "
import requests
import sqlite3
import os

# Check AAC dashboard
try:
    r = requests.get('http://localhost:5000', timeout=5)
    print('✅ AAC Dashboard: OK')
except:
    print('❌ AAC Dashboard: DOWN')

# Check database
try:
    conn = sqlite3.connect('repos/AAC/aac_accounting.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM accounts')
    count = cursor.fetchone()[0]
    print(f'✅ AAC Database: {count} accounts')
    conn.close()
except:
    print('❌ AAC Database: ERROR')

# Check processes
import subprocess
result = subprocess.run(['pgrep', '-f', 'python.*super'], capture_output=True, text=True)
proc_count = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
print(f'✅ Active Processes: {proc_count}')

print('🎯 Bit Rage Systems Status: OPERATIONAL' if all([
    'OK' in open('.super_agency_progress').read().split()[-1:],
    os.path.exists('monitoring/system_metrics.log'),
    os.path.exists('repos/AAC/aac_accounting.db')
]) else 'PARTIAL')
"
```

---

## 📞 SUPPORT & RESOURCES

### Documentation
- **Main README**: Comprehensive system overview
- **Doctrine**: `SUPER_AGENCY_DOCTRINE_MEMORY.md`
- **CPU Guide**: `CPU_MAXIMIZER_README.md`
- **Session Memory**: `SESSION_MEMORY_CAPTURE.md`

### Quick Commands Reference
```bash
# Full system deployment
./run_locally.sh full

# Emergency stop
./run_locally.sh cleanup

# System status
./run_locally.sh monitor 60

# Generate report
./run_locally.sh reports

# CPU maximization only
./run_locally.sh cpu maximum 10
```

### Log Locations
- **Progress**: `.super_agency_progress`
- **Monitoring**: `monitoring/system_metrics.log`
- **Reports**: `reports/super_agency_report_*.md`
- **AAC Logs**: `repos/AAC/*.log`

---

**🎉 Ready to achieve maximum computational output! Run `./run_locally.sh full` to begin.**