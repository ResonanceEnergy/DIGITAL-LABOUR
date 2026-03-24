---
name: gasket-matrix-maximizer
description: Matrix Maximizer — performance visualization, project intelligence, resource monitoring
metadata: {"openclaw":{"emoji":"📊","os":["darwin"],"requires":{"bins":["python3"]}}}
---

Matrix Maximizer provides performance analytics and project intelligence.

## Capabilities
- Real-time performance metrics visualization
- Project progress tracking across all repos
- Resource allocation intelligence
- Build pipeline optimization

## Collect Metrics
```bash
python3 -c "
import psutil, json, datetime, os
from pathlib import Path
cpu = psutil.cpu_percent(interval=1)
mem = psutil.virtual_memory()
disk = psutil.disk_usage('/')
status_file = Path.home() / 'repos' / 'Digital-Labour' / 'repo_depot_status.json'
repo_status = {}
if status_file.exists():
    repo_status = json.loads(status_file.read_text())
print(json.dumps({
    'matrix_maximizer': 'ONLINE',
    'system': {
        'cpu': cpu, 'memory': mem.percent,
        'disk': disk.percent,
        'uptime_hours': round((datetime.datetime.now().timestamp() - psutil.boot_time())/3600, 1)
    },
    'repo_depot': repo_status.get('metrics', {}),
    'recommendations': [
        'CPU optimal' if cpu < 60 else 'Consider load balancing',
        'Memory OK' if mem.percent < 80 else 'Memory pressure detected',
    ],
    'timestamp': datetime.datetime.now().isoformat()
}, indent=2))
"
```

## When Asked for Performance Analytics
1. Run system metrics collection (above)
2. Check repo build status (`~/repos/Digital-Labour/repo_depot_status.json`)
3. Aggregate and analyze project intelligence
4. Provide actionable recommendations
5. Visualize with Streamlit if requested: `streamlit run streamlit_matrix_maximizer.py`
