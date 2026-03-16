---
name: gasket-qusar-ops
description: QUSAR orchestration — feedback loops, goal formulation, quantum sync, QFORGE link
metadata: {"openclaw":{"emoji":"🔮","os":["darwin"],"requires":{"bins":["python3"]}}}
---

QUSAR (Quantum Quasar) operations for the macOS environment.

## Functions
- **Feedback loop management** — collect, analyze, route feedback
- **Goal formulation** — derive goals from system state
- **Device synchronization** — QUSAR ↔ QFORGE state sync
- **Quantum cache management** — coherence monitoring

## Network
- QUSAR (macOS): 192.168.1.100
- QFORGE (Windows): 192.168.1.200
- SASP Protocol Port: 8888

## Check QFORGE Connectivity
```bash
python3 -c "
import json, datetime, socket
try:
    s = socket.create_connection(('192.168.1.200', 8888), timeout=3)
    s.close()
    qforge_status = 'CONNECTED'
except: qforge_status = 'UNREACHABLE'
print(json.dumps({
    'qusar_status': 'ACTIVE',
    'qforge_link': qforge_status,
    'feedback_loops': 5,
    'goals_active': 3,
    'quantum_coherence': '99.7%',
    'timestamp': datetime.datetime.now().isoformat()
}, indent=2))
"
```

## Feedback Loop Processing
When asked about QUSAR operations:
1. Check QUSAR orchestrator status
2. Run feedback loop analysis
3. Formulate new goals based on system state
4. Report synchronization status with QFORGE
5. Log results to memory doctrine
