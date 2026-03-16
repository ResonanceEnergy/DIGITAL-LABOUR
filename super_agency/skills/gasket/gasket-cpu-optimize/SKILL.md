---
name: gasket-cpu-optimize
description: Optimize CPU usage — find high-CPU processes, suggest throttling, resource management
metadata: {"openclaw":{"emoji":"⚡","os":["darwin"],"requires":{"bins":["python3"]}}}
---

When the user asks to optimize CPU, check performance, or throttle processes:

## Steps

1. Collect CPU metrics and high-usage processes:
```bash
python3 -c "
import psutil, json
procs = []
for p in psutil.process_iter(['pid','name','cpu_percent','memory_percent']):
    try:
        info = p.info
        if info['cpu_percent'] and info['cpu_percent'] > 5:
            procs.append(info)
    except: pass
procs.sort(key=lambda x: x.get('cpu_percent',0), reverse=True)
cpu = psutil.cpu_percent(interval=1, percpu=True)
print(json.dumps({
    'overall_cpu': psutil.cpu_percent(),
    'per_core': cpu,
    'core_count': psutil.cpu_count(),
    'high_cpu_processes': procs[:10],
    'recommendation': 'HIGH CPU' if psutil.cpu_percent() > 80 else 'NOMINAL'
}, indent=2))
"
```

2. Analyze the results and provide:
   - Which processes are using the most CPU
   - Whether the system is under stress
   - Recommendations for optimization
   - If CPU > 80%, suggest which processes could be throttled

3. If the user confirms, offer to:
   - Renice processes: `renice +10 -p <PID>`
   - Kill runaway processes (with confirmation)
   - Start/stop scheduled tasks
