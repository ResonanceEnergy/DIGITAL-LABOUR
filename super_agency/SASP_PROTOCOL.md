# Bit Rage Systems Share Protocol (SASP)
# Formal communication protocol between Mac and Windows

## Overview
SASP defines the communication protocol for distributed Bit Rage Systems operations between Mac (operations hub) and Windows (heavy computation) machines.

## Protocol Version
**Version:** 1.0
**Date:** February 20, 2026
**Status:** Active

## Architecture

### Components
- **Mac Hub (Operations)**: Command center, mobile interface, lightweight processing
- **Windows Node (Computation)**: Heavy processing, data storage, specialized agents
- **Mobile Clients**: Remote access via PWA interface

### Communication Flow
```
Mobile Client ↔ Mac Hub ↔ Windows Node
       ↓           ↓           ↓
   Commands    Coordination  Execution
   Status      Resource Mgmt  Results
   Monitoring  Load Balancing Data Sync
```

## Message Format

### Base Message Structure
```json
{
  "protocol": "SASP",
  "version": "1.0",
  "timestamp": "2026-02-20T14:30:00Z",
  "message_id": "uuid-v4",
  "sender": {
    "type": "mac|windows|mobile",
    "id": "unique-identifier",
    "ip": "192.168.1.100"
  },
  "recipient": {
    "type": "mac|windows|mobile",
    "id": "unique-identifier"
  },
  "message_type": "command|status|data|error",
  "payload": {},
  "signature": "hmac-sha256-signature"
}
```

## Message Types

### 1. Command Messages
```json
{
  "message_type": "command",
  "payload": {
    "command_id": "deploy_agents_heavy",
    "parameters": {
      "agent_count": 4,
      "duration": 300,
      "priority": "high"
    },
    "callback_url": "http://mac-ip:8080/api/callback"
  }
}
```

### 2. Status Messages
```json
{
  "message_type": "status",
  "payload": {
    "system_status": "operational",
    "services": {
      "aac_system": "running",
      "cpu_maximizer": "running",
      "agents": 4
    },
    "resources": {
      "cpu_percent": 75,
      "memory_gb": 12.5,
      "disk_free_gb": 250
    }
  }
}
```

### 3. Data Messages
```json
{
  "message_type": "data",
  "payload": {
    "data_type": "agent_results|system_logs|performance_metrics",
    "data": {},
    "compression": "gzip|none",
    "chunk_info": {
      "total_chunks": 5,
      "chunk_number": 1,
      "chunk_id": "uuid"
    }
  }
}
```

### 4. Error Messages
```json
{
  "message_type": "error",
  "payload": {
    "error_code": "RESOURCE_EXHAUSTED|NETWORK_ERROR|AUTH_FAILED",
    "error_message": "Detailed error description",
    "error_context": {},
    "retry_suggested": true,
    "retry_after_seconds": 30
  }
}
```

## Endpoints

### Mac Hub Endpoints
- `POST /sasp/command` - Execute command on Windows
- `GET /sasp/status` - Get Windows status
- `POST /sasp/data` - Send data to Windows
- `GET /sasp/health` - Protocol health check

### Windows Node Endpoints
- `POST /sasp/response` - Send command results to Mac
- `POST /sasp/status` - Send status updates to Mac
- `POST /sasp/data` - Send data to Mac
- `GET /sasp/health` - Protocol health check

## Authentication & Security

### HMAC-SHA256 Signatures
- Shared secret key between Mac and Windows
- Message integrity verification
- Timestamp validation (5-minute window)

### Key Exchange
1. Initial manual key setup
2. Automatic key rotation every 24 hours
3. Key stored in secure local files

## Connection Management

### Auto-Discovery
- UDP broadcast for service discovery
- IP range scanning (192.168.x.x, 10.x.x.x)
- Service announcement with capabilities

### Connection States
- **DISCOVERING**: Finding peer systems
- **CONNECTING**: Establishing connection
- **AUTHENTICATING**: Verifying credentials
- **OPERATIONAL**: Active communication
- **DEGRADED**: Partial functionality
- **FAILED**: Connection lost

### Heartbeat Protocol
- 30-second heartbeat messages
- Automatic reconnection on failure
- Graceful degradation

## Data Synchronization

### File Sync
- Git-based repository synchronization
- Real-time file change detection
- Conflict resolution policies

### State Sync
- System state replication
- Configuration synchronization
- Agent state sharing

## Error Handling

### Retry Logic
- Exponential backoff (1s, 2s, 4s, 8s, 16s max)
- Maximum 5 retry attempts
- Circuit breaker pattern for persistent failures

### Fallback Modes
- **Local-only**: Mac operates independently
- **Cache mode**: Use cached data when network fails
- **Reduced functionality**: Core operations only

## Performance Optimization

### Message Batching
- Group multiple messages into single transmission
- Reduce network overhead
- Configurable batch sizes

### Compression
- Gzip compression for large payloads
- Automatic compression based on size thresholds
- CPU vs bandwidth trade-off consideration

### Connection Pooling
- Maintain persistent connections
- Connection reuse for multiple messages
- Automatic pool management

## Monitoring & Diagnostics

### Metrics Collection
- Message throughput (messages/second)
- Latency measurements (ms)
- Error rates by message type
- Connection stability metrics

### Logging
- Structured JSON logging
- Log levels: DEBUG, INFO, WARN, ERROR
- Centralized log aggregation
- Log rotation and retention

## Implementation Status

### ✅ Completed
- Basic message format specification
- REST API endpoints
- Authentication framework
- Auto-discovery mechanism

### 🚧 In Progress
- Full protocol implementation
- Error handling and retry logic
- Performance optimization
- Comprehensive testing

### 📋 Planned
- WebSocket support for real-time communication
- Advanced security features
- Multi-node support
- Protocol versioning

## Usage Examples

### Mac to Windows Command
```bash
curl -X POST http://windows-ip:9090/sasp/command \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "SASP",
    "version": "1.0",
    "message_type": "command",
    "payload": {
      "command_id": "deploy_agents_heavy",
      "parameters": {"count": 4}
    }
  }'
```

### Windows Status Update
```bash
curl -X POST http://mac-ip:8080/sasp/status \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "SASP",
    "version": "1.0",
    "message_type": "status",
    "payload": {
      "system_status": "operational",
      "active_agents": 4
    }
  }'
```

## Future Extensions

### WebSocket Support
- Real-time bidirectional communication
- Reduced latency for interactive operations
- Better support for streaming data

### Multi-Node Support
- Support for multiple Windows nodes
- Load balancing across nodes
- Failover and redundancy

### Advanced Security
- TLS 1.3 encryption
- Certificate-based authentication
- Zero-trust architecture</content>
<parameter name="filePath">C:/Dev/SuperAgency-Shared/SASP_PROTOCOL.md