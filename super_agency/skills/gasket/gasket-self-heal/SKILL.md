---
name: gasket-self-heal
description: Self-healing infrastructure — detect, diagnose, fix issues autonomously
metadata: {"openclaw":{"emoji":"🔧","os":["darwin"],"requires":{"bins":["python3"]}}}
---

Self-healing infrastructure agent for the DIGITAL LABOUR platform.

## Automated Checks

### 1. OpenClaw Gateway Health
```bash
curl -sf http://127.0.0.1:18789/health && echo "UP" || echo "DOWN"
```
If DOWN: `openclaw gateway restart`

### 2. System Resources
```bash
python3 -c "
import psutil, subprocess, json
checks = {}
# Gateway
try:
    import urllib.request
    r = urllib.request.urlopen('http://127.0.0.1:18789/health', timeout=5)
    checks['gateway'] = 'UP' if r.status == 200 else 'DOWN'
except: checks['gateway'] = 'DOWN'
# Disk
disk = psutil.disk_usage('/')
checks['disk_percent'] = disk.percent
checks['disk_alert'] = disk.percent > 90
# Memory
mem = psutil.virtual_memory()
checks['memory_percent'] = mem.percent
checks['memory_alert'] = mem.percent > 85
# CPU
checks['cpu_percent'] = psutil.cpu_percent(interval=1)
checks['cpu_alert'] = checks['cpu_percent'] > 90
print(json.dumps(checks, indent=2))
"
```

### 3. Git Repo Health
```bash
cd ~/repos/Digital-Labour && git status --porcelain | head -20
```

### 4. LaunchAgent Status
```bash
launchctl list | grep DIGITAL LABOUR
```

### 5. Network — QFORGE Connectivity
```bash
nc -z -w 3 192.168.1.200 8888 && echo "QFORGE: UP" || echo "QFORGE: DOWN"
```

## Auto-Remediation
- **Gateway down**: restart with `openclaw gateway restart`
- **Disk > 90%**: clean old logs (`find ~/repos/Digital-Labour -name '*.log' -mtime +30 -delete`)
- **Runaway process**: report PID and CPU%, offer to `kill -15 <PID>` (with confirmation)
- **Unloaded launchd plist**: `launchctl load ~/Library/LaunchAgents/com.digitallabour.*.plist`

If any check fails, attempt auto-fix and report results to memory.
