# DIGITAL LABOUR Orchestration Speed Optimization Guide

## 🎯 Current Performance
- **Cycle Duration**: 3-4 seconds (execution time)
- **Current Interval**: 30 minutes (waiting time)
- **Active Time**: ~0.2% (4 seconds per 30 minutes)
- **Efficiency**: 99.8% idle time (optimal for resource conservation)

## ⚡ Speed Optimization Options

### 1. ULTRA-HIGH FREQUENCY MODE (1-2 min) - MAXIMUM PERFORMANCE
**Command**: `.\continuous_orchestration_runner_ultra_high.ps1 -IntervalMinutes 1`
**Benefits**:
- ✅ 30x more frequent monitoring (every minute!)
- ✅ Near real-time issue detection
- ✅ Maximum system responsiveness
- ✅ Enhanced safety monitoring
**Trade-offs**:
- ⚠️ EXTREME resource usage (CPU/Memory)
- ⚠️ High risk of API rate limits (~4,800 calls/hour)
- ⚠️ Potential system instability
- ⚠️ Requires constant monitoring
- ⚠️ Massive log volume growth

### 2. HIGH FREQUENCY MODE (5-minute intervals)
**Command**: `.\continuous_orchestration_runner_high_freq.ps1 -IntervalMinutes 5`
**Benefits**:
- ✅ 6x more frequent monitoring
- ✅ Faster issue detection
- ✅ More responsive system
**Trade-offs**:
- ⚠️ Higher resource usage
- ⚠️ More API calls (OpenAI limits)
- ⚠️ Increased log volume
- ⚠️ Potential system interference

### 3. MODERATE FREQUENCY MODE (10-minute intervals)
**Command**: `.\continuous_orchestration_runner_moderate.ps1 -IntervalMinutes 10`
**Benefits**:
- ✅ 3x more frequent monitoring
- ✅ Good balance of speed vs resources
- ✅ Suitable for active development
**Trade-offs**:
- ⚠️ Moderate resource increase
- ⚠️ Some API usage increase

### 4. STANDARD FREQUENCY MODE (30-minute intervals) - CURRENT
**Command**: `.\continuous_orchestration_runner.ps1 -IntervalMinutes 30`
**Benefits**:
- ✅ Conservative resource usage
- ✅ Proven stability
- ✅ API rate limit friendly
**Trade-offs**:
- ❌ Slower issue detection
- ❌ Less responsive monitoring

## 🚀 Quick Start Options

### Option A: Interactive Launcher (Recommended)
```cmd
start_orchestration_launcher.bat
```
Choose from menu options 1-4

### Option B: Direct Commands
```powershell
# High Frequency (5 min)
.\continuous_orchestration_runner_high_freq.ps1 -IntervalMinutes 5 -SafeMode

# Moderate Frequency (10 min)
.\continuous_orchestration_runner_moderate.ps1 -IntervalMinutes 10

# Standard Frequency (30 min) - Current
.\continuous_orchestration_runner.ps1 -IntervalMinutes 30

# Test Mode (10 sec) - Development only
.\continuous_orchestration_runner_high_freq.ps1 -IntervalMinutes 1 -TestMode
```

## 📊 Performance Impact Analysis

### Resource Usage Comparison (Estimated)

| Frequency | Cycles/Day | API Calls/Day | CPU Impact | Memory Impact | Log Growth |
|-----------|------------|---------------|------------|---------------|------------|
| 30 min    | 48         | ~200          | Low        | Low           | Low        |
| 10 min    | 144        | ~600          | Medium     | Medium        | Medium     |
| 5 min     | 288        | ~1,200        | High       | High          | High       |

### OpenAI API Limits (gpt-4o)
- **Requests**: 200 per minute (~12,000 per hour)
- **Tokens**: 10,000 per minute (~600,000 per hour)
- **Current Usage**: ~4 requests per cycle
- **Safe Limit**: 50 cycles per hour (10-minute intervals)

## 🛡️ Safety Features

### High Frequency Mode Includes:
- **Resource Monitoring**: Automatic CPU/memory checks
- **Safe Mode**: `-SafeMode` flag enables resource monitoring
- **Automatic Warnings**: Alerts when usage exceeds 80% CPU or 90% memory
- **Emergency Stop**: Manual intervention capability

### Built-in Protections:
- **API Rate Limiting**: Respects OpenAI limits
- **Memory Management**: QUASMEM automatic cleanup
- **Error Handling**: Graceful failure recovery
- **Logging Separation**: Different log files per frequency

## 📈 Monitoring & Logs

### Log Files by Frequency:
- `continuous_orchestration_log.csv` - Standard (30 min)
- `continuous_orchestration_log_moderate.csv` - Moderate (10 min)
- `continuous_orchestration_log_high_freq.csv` - High (5 min)

### Performance Tracking:
```powershell
# Monitor current orchestration processes
Get-Process | Where-Object { $_.ProcessName -like "*powershell*" -and $_.StartTime -gt (Get-Date).AddHours(-1) }

# Check recent log activity
Get-Content "continuous_orchestration_log_high_freq.csv" -Tail 10
```

## 🎯 Recommendations

### For Development/Testing:
**Use MODERATE FREQUENCY (10 minutes)**
- Good balance of speed and stability
- Suitable for active development work
- Minimal API limit concerns

### For Production Monitoring:
**Use HIGH FREQUENCY (5 minutes) with Safe Mode**
- Maximum responsiveness
- Built-in safety monitoring
- Automatic resource alerts

### For Resource-Constrained Systems:
**Stick with STANDARD FREQUENCY (30 minutes)**
- Minimal resource impact
- Proven stability
- API-friendly

## ⚡ Immediate Speed Increase

To get started right now with moderate frequency:

```cmd
# Quick start moderate frequency
powershell -ExecutionPolicy Bypass -File "continuous_orchestration_runner_moderate.ps1"
```

This will give you **3x more frequent monitoring** (every 10 minutes instead of 30) with reasonable resource usage.

## 🔍 Performance Validation

After changing frequency, monitor:

1. **System Resources**: CPU, memory usage
2. **API Usage**: OpenAI rate limits
3. **Log Volume**: File size growth
4. **System Stability**: Error rates
5. **Response Time**: Cycle completion times

**The system is now ready for frequency optimization!** 🚀

*Choose your speed based on development needs vs resource constraints.*
