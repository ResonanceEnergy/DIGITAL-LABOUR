# BIT RAGE LABOUR Local Development & Deployment Plan

## Current Status (Feb 2026)
✅ **Phase 1 Complete**: MVP operational with core agent orchestration
- Repo Sentry monitoring 23+ repositories
- Daily Ops Brief generation
- NCL Second Brain with YouTube ingestion
- Local-first architecture (no cloud dependency)

## 1. Local Repository Development Workflow

### Current Setup
- **Workspace**: `C:\Dev\DIGITAL-LABOUR`
- **Active Repos**: `demo/`, `TESLACALLS2026/`
- **Portfolio**: 23 repos tracked (most not cloned locally yet)

### Development Workflow
```bash
# Daily operations (already working)
cd "C:\Dev\DIGITAL-LABOUR"
python agents\orchestrator.py

# Clone missing repos for development
git clone https://github.com/ResonanceEnergy/{repo-name}.git repos/{repo-name}

# Test changes locally
python -m pytest tests/
```

### VS Code Integration
- **Workspace**: Open Digital-Labour folder
- **Extensions Needed**:
  - Python
  - GitLens
  - GitHub Pull Requests
  - Jupyter (for notebooks)
  - YAML (for config)

## 2. Matrix Monitor Output Usage

### Current State
- **Panel**: `matrix_monitor/panels/second_brain_panel.json` (basic)
- **Output**: Daily briefs in `reports/daily/`

### Enhancement Plan
```json
{
  "panel": "BIT RAGE LABOUR Matrix Monitor",
  "metrics": {
    "portfolio_health": "23 repos monitored",
    "agent_status": "All agents operational",
    "ncl_ingestion": "YouTube pipeline active",
    "daily_briefs": "Generated successfully"
  },
  "alerts": {
    "repo_changes": "Detected in last 24h",
    "failures": "Agent errors or timeouts",
    "security": "Provenance violations"
  }
}
```

### Integration with VS Code
- Use VS Code's output panel for real-time monitoring
- GitHub Actions for CI/CD status
- Live share for collaborative debugging

## 3. GitHub Integration for Updates

### Current Workflow
```bash
# Check changes
git status
git diff

# Commit and push
git add .
git commit -m "feat: [description]"
git push origin main

# Create PR
gh pr create --title "feat: [description]" --body "Details..."
```

### Automated Updates
- **GitHub Actions**: For CI/CD on portfolio repos
- **Dependabot**: Automated dependency updates
- **CodeQL**: Security scanning
- **Release Automation**: Version bumps and changelogs

## 4. Go-Live Requirements

### ✅ Ready Now
- Core agent orchestration
- Daily operations brief
- NCL Second Brain ingestion
- Portfolio monitoring
- Local-first security model

### 🚧 Phase 2 Prerequisites (Mar-May 2026)
- Multi-modal content ingestion (podcasts, docs)
- Enhanced agent collaboration
- Portfolio intelligence tiering
- Matrix monitor expansion

### 🎯 Go-Live Checklist
- [x] All agents pass tests (`python -m pytest tests/`)
- [x] Daily brief generates successfully
- [x] NCL ingestion working
- [x] Matrix monitor panels functional
- [ ] Portfolio repos cloned and monitored
- [ ] GitHub Actions configured
- [ ] Documentation complete
- [ ] Security audit passed

## 5. AWS Compute Implementation Timeline

### Current Architecture: Local-First
- **No mandatory cloud**: All operations run locally
- **Opt-in cloud**: Only when explicitly approved
- **Data sovereignty**: Local storage with selective sharing

### AWS Implementation Phases

#### Phase 2 (Q2 2026): Optional Cloud Enhancement
**When**: After stable local operations (April 2026)
**Purpose**: Scaling and resilience, not core functionality

**Components**:
- **EC2**: For compute-intensive tasks (LLM inference, batch processing)
- **S3**: Encrypted backup storage with local-first sync
- **Lambda**: Event-driven processing (YouTube ingestion triggers)
- **CloudWatch**: Enhanced monitoring and alerting

**Requirements**:
- Council approval for each cloud component
- Data redaction and consent protocols
- Local fallback for all cloud services
- Cost monitoring and budget controls

#### Phase 3 (2027): Hybrid Operations
**When**: After Phase 2 completion
**Purpose**: Business operations scaling

**Components**:
- **ECS/EKS**: Container orchestration for agent deployment
- **RDS**: Managed databases (PostgreSQL/Neo4j) with local mirrors
- **API Gateway**: Secure API endpoints for external integrations
- **CloudFormation**: Infrastructure as Code

#### Phase 4 (2028): Full Ecosystem
**When**: Company-of-companies scale
**Purpose**: Global operations and AI safety

**Components**:
- **SageMaker**: Advanced ML model training/deployment
- **Bedrock**: Multi-provider LLM orchestration
- **Control Tower**: Multi-account governance
- **Global Accelerator**: Worldwide distribution

### AWS Migration Strategy
1. **Start with isolated services**: Lambda for ingestion, S3 for backups
2. **Maintain local primacy**: All operations work without AWS
3. **Gradual migration**: One component at a time with rollback plans
4. **Cost governance**: Budget alerts, usage monitoring
5. **Security first**: VPC isolation, encryption, audit trails

### Immediate Actions (Feb-Mar 2026)
1. **Complete local stability** - All agents running reliably
2. **Expand matrix monitoring** - Real-time dashboards
3. **Clone and monitor portfolio repos** - Full visibility
4. **Set up GitHub Actions** - Automated testing/deployment
5. **Document all processes** - Runbooks and playbooks

### AWS Readiness Checklist
- [ ] Local operations stable for 30+ days
- [ ] Cost-benefit analysis completed
- [ ] Security review passed
- [ ] Council approval obtained
- [ ] Rollback procedures documented
- [ ] Local fallback tested

## Development Priorities (Next 30 Days)

1. **Week 1**: Clone and monitor all portfolio repos
2. **Week 2**: Enhance matrix monitor with real-time metrics
3. **Week 3**: Set up GitHub Actions for CI/CD
4. **Week 4**: Complete documentation and runbooks

## Risk Mitigation

### Local Development Risks
- **Dependency conflicts**: Use virtual environments per project
- **Path issues**: Consistent workspace structure
- **Git conflicts**: Clear branching strategy

### Cloud Migration Risks
- **Vendor lock-in**: Design for portability (AWS/Azure/GCP)
- **Cost overruns**: Budget monitoring and alerts
- **Security breaches**: Zero-trust architecture
- **Data privacy**: Local-first with explicit consent

### Operational Risks
- **Agent failures**: Circuit breakers and automatic retries
- **Data corruption**: Provenance tracking and backups
- **Human error**: Council governance and approval workflows

---

## Next Steps

**Immediate (Today)**:
- Clone high-priority portfolio repos
- Test all agents locally
- Review and enhance matrix monitor

**Short-term (This Week)**:
- Set up GitHub integration
- Complete local testing suite
- Document current processes

**Medium-term (Next Month)**:
- Evaluate AWS proof-of-concept
- Expand agent capabilities
- Begin Phase 2 development

**Questions for Council**:
- Which portfolio repos to prioritize for local development?
- AWS timeline and budget constraints?
- Additional monitoring requirements?