# Bit Rage Systems CPU Maximizer

**Maximum CPU utilization for distributed intelligence processing across all Bit Rage Systems repositories.**

This system provides multiple levels of CPU maximization to achieve maximum computational output from your Bit Rage Systems infrastructure.

## 🚀 Quick Start

### Linux/macOS
```bash
# Interactive mode
./max_cpu.sh

# Command line mode
./max_cpu.sh maximum 5    # Maximum overdrive for 5 minutes
./max_cpu.sh all          # Run all options sequentially
```

### Windows
```batch
# Interactive mode
max_cpu.bat

# Command line mode
max_cpu.bat maximum 5     # Maximum overdrive for 5 minutes
max_cpu.bat all           # Run all options sequentially
```

### Python Direct
```bash
# Maximum CPU mode
python cpu_control_center.py maximum --duration 10

# Diagnostic mode
python cpu_control_center.py diagnostic

# Batch processing
python batch_processor.py --cycles 20
```

## 📊 CPU Maximization Options

### 1. Single CPU Maximizer (`cpu_maximizer.py`)
- **Purpose**: Basic parallel processing across all systems
- **CPU Usage**: High (utilizes all available cores)
- **Duration**: 5-10 minutes per cycle
- **Best For**: General CPU maximization

### 2. Parallel Orchestrator (`parallel_orchestrator.py`)
- **Purpose**: Parallel execution of all Bit Rage Systems agents
- **CPU Usage**: Very High (all agents run simultaneously)
- **Duration**: Variable (depends on agent completion)
- **Best For**: Agent-based processing

### 3. Batch Processor (`batch_processor.py`)
- **Purpose**: Run multiple CPU maximizer cycles in sequence
- **CPU Usage**: High (staggered processing)
- **Duration**: Configurable (10+ minutes)
- **Best For**: Sustained processing

### 4. CPU Control Center (`cpu_control_center.py`)
- **Purpose**: Advanced orchestration with monitoring
- **Modes**:
  - `maximum`: All systems simultaneously (EXTREME CPU usage)
  - `balanced`: Controlled parallel execution
  - `diagnostic`: Test all systems individually
- **Best For**: Advanced users, monitoring required

### 5. PowerShell Maximizer (`cpu_maximizer.ps1`)
- **Purpose**: Windows-native parallel processing
- **CPU Usage**: Configurable (maximize/balanced/conservative)
- **Duration**: Configurable
- **Best For**: Windows environments

## 🏗️ System Architecture

```
Bit Rage Systems CPU Maximizer
├── cpu_maximizer.py           # Main parallel processor
├── parallel_orchestrator.py   # Agent orchestrator
├── batch_processor.py         # Batch processing system
├── cpu_control_center.py      # Advanced control center
├── cpu_maximizer.ps1          # PowerShell version
├── max_cpu.sh                 # Linux/macOS launcher
├── max_cpu.bat                # Windows launcher
└── cpu_results/               # Performance logs
```

## 🎯 Maximization Strategies

### Maximum Overdrive Mode
```bash
# Launch ALL systems simultaneously
python cpu_control_center.py maximum --duration 10
```
- **CPU Usage**: 100% across all cores
- **Memory Usage**: High (multiple processes)
- **Risk**: System may become unresponsive
- **Output**: Maximum computational throughput

### Balanced Mode
```bash
# Controlled parallel execution
python cpu_control_center.py balanced --duration 15
```
- **CPU Usage**: 70-90% sustained
- **Memory Usage**: Moderate
- **Risk**: Low (built-in safeguards)
- **Output**: High throughput with stability

### Batch Mode
```bash
# Multiple cycles with breaks
python batch_processor.py --cycles 50 --batch-size 4
```
- **CPU Usage**: Pulsed (high during cycles)
- **Memory Usage**: Variable
- **Risk**: Very low
- **Output**: Consistent long-term processing

## 📈 Performance Monitoring

All maximization tools include built-in monitoring:

- **Real-time CPU usage tracking**
- **Memory utilization monitoring**
- **Process health checks**
- **Performance logging**
- **Automatic failure recovery**

View results in `cpu_results/` directory.

## 🔧 Configuration

### Environment Variables
```bash
export CPU_MAXIMIZER_WORKERS=8        # Override auto-detected core count
export CPU_MAXIMIZER_MODE=balanced    # Default processing mode
export CPU_MAXIMIZER_LOG_LEVEL=INFO   # Logging verbosity
```

### System Requirements
- **Python**: 3.7+
- **CPU**: Multi-core recommended (4+ cores for best results)
- **RAM**: 8GB+ recommended
- **Disk**: 10GB+ free space for logs and results

## 🚨 Safety Features

- **Automatic process monitoring**
- **Memory usage limits**
- **Timeout protection**
- **Graceful shutdown handling**
- **Resource usage logging**

## 📊 Expected Performance

| Mode | CPU Usage | Memory | Processes | Duration | Output |
|------|-----------|--------|-----------|----------|--------|
| Single | 80-100% | Medium | 4-8 | 5-10min | High |
| Parallel | 90-100% | High | 6-12 | 10-20min | Very High |
| Batch | 70-95% | Variable | 4-16 | 30-60min | Sustained |
| Maximum | 100% | Very High | 8-20 | 5-15min | Maximum |
| Balanced | 70-90% | Medium | 6-12 | 15-30min | Optimized |

## 🛠️ Troubleshooting

### High CPU Usage Issues
```bash
# Reduce worker count
python cpu_maximizer.py --workers 4

# Use balanced mode
python cpu_control_center.py balanced
```

### Memory Issues
```bash
# Run diagnostic first
python cpu_control_center.py diagnostic

# Use batch mode with smaller batches
python batch_processor.py --batch-size 2
```

### Process Crashes
- Check `cpu_results/` for error logs
- Run diagnostic mode to identify failing components
- Ensure all dependencies are installed

## 🔄 Integration Points

The CPU maximizer integrates with:

- **Inner Council**: Distributed intelligence processing
- **AAC System**: Financial computation acceleration
- **NCL Second Brain**: Knowledge graph processing
- **Portfolio Intelligence**: Multi-repo analysis
- **Matrix Monitor**: Performance visualization

## 📝 API Usage

```python
from cpu_control_center import CPUControlCenter

# Initialize
cc = CPUControlCenter()

# Run maximum mode
results = cc.run_maximum_cpu_mode(duration_minutes=10)

# Get system info
info = cc.get_system_info()

# Monitor processes
monitoring = cc.monitor_processes(processes, duration_seconds=300)
```

## 🎯 Best Practices

1. **Start Small**: Begin with diagnostic mode to test all systems
2. **Monitor Resources**: Use built-in monitoring to avoid overload
3. **Scale Gradually**: Increase intensity as you verify stability
4. **Schedule Wisely**: Run during off-peak hours for maximum impact
5. **Backup First**: Ensure important data is backed up before maximum mode

## 📈 Performance Tuning

### For Maximum Output
```bash
# Disable CPU frequency scaling
sudo cpupower frequency-set -g performance

# Increase process limits
ulimit -n 65536

# Use real-time priority (careful!)
chrt --rr 50 python cpu_maximizer.py
```

### For Stability
```bash
# Enable CPU frequency scaling
sudo cpupower frequency-set -g ondemand

# Limit CPU usage
cpulimit -l 80 python cpu_maximizer.py
```

---

**⚠️ WARNING**: Maximum CPU modes can make your system unresponsive. Use with caution and monitor closely. Always have a way to forcibly terminate processes if needed.

*Generated by Bit Rage Systems Development System*