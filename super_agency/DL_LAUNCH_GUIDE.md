# 🚀 DIGITAL LABOUR LAUNCH SEQUENCE
## Complete System Deployment Guide
## Date: February 20, 2026

---

## 📋 MISSION BRIEFING

**Objective:** Deploy distributed DIGITAL LABOUR command center with MacBook operations and Windows heavy computation.

**Architecture:**
- **MacBook (8GB M1/16GB):** Operations hub, mobile interface, lightweight processing
- **Windows:** Heavy computation, AAC system, full agent deployment
- **Mobile:** PWA interface for remote command and control

**System Variants:**
- **8GB M1 MacBook:** Ultra-conservative memory mode, Windows delegation
- **16GB MacBook:** Full operations mode, local processing available

**Expected Outcome:** Fully operational DIGITAL LABOUR accessible from mobile devices.

---

## 🎯 PHASE 1: MACBOOK SETUP & LAUNCH

### System Detection & Setup Selection

**Automatic System Detection:**
```bash
# Check your MacBook specifications
echo "RAM: $(echo "scale=1; $(sysctl -n hw.memsize) / 1024 / 1024 / 1024" | bc)GB"
echo "Chip: $(sysctl -n machdep.cpu.brand_string)"
echo "macOS: $(sw_vers -productVersion)"
```

**Setup Selection:**
- **8GB M1 MacBook:** Use `macbook_8gb_m1_setup.sh` (Ultra-conservative mode)
- **16GB+ MacBook:** Use `macbook_16gb_setup.sh` (Full operations mode)

---

### Option A: 8GB M1 MacBook Setup (Ultra-Conservative Mode)

#### Step 1.1A: 8GB M1 Setup
```bash
# Navigate to DIGITAL LABOUR directory
cd /path/to/Digital-Labour

# Make scripts executable
chmod +x macbook_8gb_m1_setup.sh m1_8gb_launch.sh optimize_m1_8gb.sh

# Run 8GB M1 optimized setup
./macbook_8gb_m1_setup.sh
```

**Expected Output:**
```
🚀 DIGITAL LABOUR 8GB M1 MacBook Setup
==================================
📊 RAM: 8.0GB
🔧 Chip: Apple M1
✅ 8GB M1 configuration created
✅ Minimal dependencies installed
✅ Ultra-lightweight communication configured
✅ 8GB M1 launch script created
🎯 Setup Complete!
```

#### Step 1.2A: 8GB M1 System Optimization
```bash
# Apply macOS optimizations for 8GB M1
./optimize_m1_8gb.sh
```

#### Step 1.3A: Launch 8GB M1 System
```bash
# Start ultra-lightweight DIGITAL LABOUR
./m1_8gb_launch.sh
```

**8GB M1 Mode Features:**
- ⚡ Ultra-low memory usage (<256MB for mobile center)
- 🔄 All heavy operations delegated to Windows
- 📱 Mobile-only interface (no local Matrix Monitor)
- 🚀 Optimized for Apple M1 Neural Engine disabled
- 💾 Minimal local storage, maximum remote delegation

---

### Option B: 16GB+ MacBook Setup (Full Operations Mode)
```bash
# Navigate to DIGITAL LABOUR directory
cd /path/to/Digital-Labour

# Make scripts executable
chmod +x macbook_16gb_setup.sh test_16gb_setup.sh macbook_launch.sh

# Run 16GB optimized setup
./macbook_16gb_setup.sh
```

**Expected Output:**
```
🍎 DIGITAL LABOUR 16GB MacBook Setup
==================================
✅ RAM check passed: 16GB
✅ Python installed
✅ Dependencies installed
✅ Configuration created
🎉 16GB MacBook setup complete!
```

### Step 1.2: System Test (MacBook)
```bash
# Test all components
./test_16gb_setup.sh
```

**Expected Output:**
```
🧪 DIGITAL LABOUR 16GB MacBook Test
=================================
✅ RAM: 16GB (sufficient)
✅ Python: Python 3.x.x
✅ flask installed
✅ requests installed
✅ psutil installed
✅ config/16gb_macbook.json exists
✅ macbook_launch.sh exists
✅ Mobile interface files present
✅ Port 8080 available
✅ Port 5000 available
✅ Port 3000 available
```

### Step 1.3: Launch Mac Services (MacBook)
```bash
# Start all Mac services
./macbook_launch.sh
```

**Expected Output:**
```
🚀 Starting DIGITAL LABOUR (16GB MacBook Mode)
📊 Memory: 16GB
📱 Starting Mobile Command Center...
⚙️ Starting Operations Interface...
🧠 Starting Matrix Monitor...
✅ Services started!
📱 Mobile Access: http://localhost:8080
⚙️ Operations: http://localhost:5000
🧠 Matrix Monitor: http://localhost:3000
💻 Heavy computation delegated to Windows machine
```

---

## 💪 PHASE 2: WINDOWS HEAVY COMPUTATION

**Compatible with both MacBook variants:**
- **8GB M1 MacBook:** Windows handles ALL heavy computation and services
- **16GB+ MacBook:** Windows provides additional heavy computation capacity

### Step 2.1: Windows Setup
```powershell
# On Windows machine, navigate to DIGITAL LABOUR
cd C:\path\to\Digital-Labour
```

### Step 2.2: Sync with MacBook (Auto-Detection)
```powershell
# Auto-detect Mac IP and start services
.\sync_to_windows.ps1 -StartServices
```

**For 8GB M1 MacBooks:**
- Windows becomes the primary computation hub
- All agent deployment, AAC system, and heavy processing runs here
- Mac provides ultra-lightweight mobile interface only

**For 16GB+ MacBooks:**
- Windows provides additional heavy computation capacity
- Mac can run some local services with Windows backup

**Expected Output (both variants):**
```
🔄 DIGITAL LABOUR Distributed Setup (SASP v1.0)
=================================
Mac IP: 192.168.1.100
Windows: Heavy computation
Mac: Operations & mobile access
Protocol: SASP

🔄 Syncing MacBook Operations to Windows...
✅ Mobile Center connected
✅ SASP protocol initialized
📡 SASP Status sent to Mac hub

💪 Starting Windows heavy computation services...
✅ AAC System started (PID: 1234)
✅ CPU Maximizer started (PID: 1235)
✅ Intelligence Monitor started (PID: 1236)
✅ Inner Council started (PID: 1237)

✅ Distributed setup complete with SASP protocol!
```

### Step 2.3: Verify Windows Status
```powershell
# Check all services are running
.\sync_to_windows.ps1 -Status
```

---

## 📱 PHASE 3: MOBILE ACCESS TEST

### Step 3.1: Local Access Test
- **Open browser:** http://localhost:8080 (on MacBook)
- **Expected:** Mobile dashboard loads with status indicators

### Step 3.2: Network Access Test
- **Find Mac IP:**
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```
- **Access from any device:** http://[MAC_IP]:8080

### Step 3.3: PWA Installation Test
1. **Open mobile browser** (iPhone/iPad/Android)
2. **Navigate to:** http://[MAC_IP]:8080
3. **Tap share button** (iOS) or menu (Android)
4. **Select "Add to Home Screen"**
5. **Name:** "DIGITAL LABOUR Command"
6. **Expected:** App icon appears on home screen

### Step 3.4: Mobile Interface Test
- **Status Dashboard:** Should show green indicators
- **Command Buttons:** Test "Max CPU Light" and "Deploy Agents Light"
- **Pull-to-Refresh:** Swipe down to update status
- **Memory Monitor:** Should stay under 4GB total

---

## ⚡ PHASE 4: LIGHTWEIGHT AGENT DEPLOYMENT

### Step 4.1: Test Agent Deployment (MacBook)
```bash
# Deploy 2 lightweight agents for 3 minutes
python3 inner_council/deploy_agents.py --mode deploy --duration 180 --max-agents 2
```

**Expected Output:**
```
🤖 Deploying Inner Council Agents (Lightweight Mode)
📊 Memory check: 2.3GB used, 13.7GB available
✅ Agent 1 deployed (PID: 5678)
✅ Agent 2 deployed (PID: 5679)
⏱️  Running for 180 seconds...
```

### Step 4.2: Monitor Agent Activity
- **Mobile Dashboard:** Check agent status indicators
- **Operations Interface:** http://localhost:5000
- **Matrix Monitor:** http://localhost:3000

### Step 4.3: Test Commands from Mobile
1. **Open PWA app**
2. **Tap "Deploy Agents Light"**
3. **Verify agents start** (should see activity in logs)
4. **Check memory usage** (should stay under 4GB)

---

## 🔧 PHASE 5: TROUBLESHOOTING & VERIFICATION

### Issue 1: Mac Services Won't Start
```bash
# Check ports
lsof -i :8080,5000,3000

# Kill existing processes
pkill -f python

# Restart
./macbook_launch.sh
```

### Issue 2: Windows Can't Connect to Mac
```powershell
# Manual IP entry
.\sync_to_windows.ps1 -MacIP 192.168.1.100 -StartServices

# Test connection
Test-NetConnection 192.168.1.100 -Port 8080
```

### Issue 3: Mobile Interface Not Loading
- **Check firewall:** Ensure ports 8080, 5000, 3000 open
- **Verify IP:** Use correct Mac IP address
- **Test locally:** http://localhost:8080 on MacBook

### Issue 4: Memory Usage Too High
```bash
# Check memory on Mac
top -l 1 | grep PhysMem

# Restart lightweight
pkill -f python
./macbook_launch.sh
```

### Issue 5: Agents Not Responding
```bash
# Check agent logs
tail -f logs/council.log

# Restart agents
python3 inner_council/deploy_agents.py --mode restart
```

---

## 📈 PHASE 6: PERFORMANCE VERIFICATION

### Memory Usage Check
```bash
# MacBook memory
echo "Mac Memory: $(echo "scale=1; $(ps aux | awk 'BEGIN {sum=0} {sum += $6} END {print sum/1024/1024}')MB" | bc)GB used"
```

### Service Status Check
```powershell
# Windows status
.\sync_to_windows.ps1 -Status
```

### Mobile Performance Test
- **Load time:** < 2 seconds
- **Memory usage:** < 4GB total on Mac
- **Command response:** < 5 seconds
- **Status updates:** Real-time

---

## 📊 PHASE 7: SCALE-UP PLANNING

### Immediate Upgrades (Next Month)
- **MacBook RAM:** Upgrade to 32GB ($200-400)
- **Expected improvement:** 6-10 agents, faster response

### Medium-term (3-6 Months)
- **Mac Studio 128GB:** $4,199
- **Expected capacity:** 25-40 agents, enterprise operations

### Long-term (6-12 Months)
- **Mac Pro:** $7,499+ with 768GB RAM
- **Multiple Windows machines**
- **AWS integration** for overflow

### Cost-Benefit Analysis
```
Current Setup: $0 (existing hardware)
32GB Upgrade: $300 → 2.5x capacity increase
Mac Studio: $4,199 → 10x capacity, 5-year ROI
```

---

## 🎯 SUCCESS CRITERIA

### ✅ System Operational
- [ ] Mac services running (ports 8080, 5000, 3000)
- [ ] Windows services active
- [ ] Mobile PWA installed and functional
- [ ] Cross-platform communication working

### ✅ Performance Verified
- [ ] Memory usage < 4GB on Mac
- [ ] Response times < 5 seconds
- [ ] Agents deploy successfully
- [ ] Commands execute from mobile

### ✅ User Experience
- [ ] Intuitive mobile interface
- [ ] Real-time status updates
- [ ] Reliable cross-platform sync
- [ ] Easy troubleshooting

---

## 🚨 EMERGENCY PROCEDURES

### Complete System Reset
```bash
# MacBook
pkill -f python
./macbook_launch.sh
```

```powershell
# Windows
.\sync_to_windows.ps1 -StopServices
.\sync_to_windows.ps1 -StartServices
```

### Emergency Memory Management
```bash
# Kill all Python processes
pkill -9 python

# Restart minimal services
python3 mobile_command_center.py &
```

---

## 📞 SUPPORT RESOURCES

### Documentation
- `MACBOOK_8GB_M1_GUIDE.md` - 8GB M1 MacBook setup guide
- `MACBOOK_16GB_GUIDE.md` - 16GB+ MacBook setup guide
- `MOBILE_REMOTE_ACCESS_README.md` - Mobile instructions
- `DL_DOCTRINE_MEMORY.md` - System architecture

### Logs Location
- Mac: `logs/` directory
- Windows: Event Viewer + console output
- Mobile: Browser developer tools

### Community Support
- GitHub issues for technical problems
- Documentation updates for improvements
- Performance tuning guides

---

**LAUNCH STATUS: READY FOR DEPLOYMENT** 🚀

**Next Action:** Begin with Phase 1 on your MacBook!

*This guide ensures complete system deployment with comprehensive testing and troubleshooting.*</content>
<parameter name="filePath">C:/Dev/DIGITAL-LABOUR/DL_LAUNCH_GUIDE.md