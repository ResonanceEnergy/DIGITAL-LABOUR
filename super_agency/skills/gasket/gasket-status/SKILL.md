---
name: gasket-status
description: Get AGENT GASKET system status — CPU, memory, QUSAR, Matrix Maximizer, OpenClaw gateway
metadata: {"openclaw":{"always":true,"emoji":"🔴","os":["darwin"]}}
---

When the user asks for GASKET status, system health, or agent status, run this skill.

## Steps

1. Run system metrics collection:
```bash
python3 -c "
import psutil, json, datetime
cpu = psutil.cpu_percent(interval=1)
mem = psutil.virtual_memory()
disk = psutil.disk_usage('/')
net = psutil.net_io_counters()
print(json.dumps({
    'agent': 'GASKET v2.1',
    'timestamp': datetime.datetime.now().isoformat(),
    'cpu_percent': cpu,
    'memory_percent': mem.percent,
    'memory_used_gb': round(mem.used/1024**3, 2),
    'memory_total_gb': round(mem.total/1024**3, 2),
    'disk_percent': disk.percent,
    'disk_free_gb': round(disk.free/1024**3, 2),
    'net_sent_mb': round(net.bytes_sent/1024**2, 2),
    'net_recv_mb': round(net.bytes_recv/1024**2, 2),
    'status': 'OPERATIONAL'
}, indent=2))
"
```

2. Check OpenClaw gateway health:
```bash
curl -s http://127.0.0.1:18789/health || echo '{"status":"DOWN"}'
```

3. Format the output as a clean status report with sections:
   - Agent Identity (name, version)
   - System Resources (CPU, memory, disk)
   - Network (gateway, QFORGE connectivity)
   - Operational Status (loops running, skills deployed)
