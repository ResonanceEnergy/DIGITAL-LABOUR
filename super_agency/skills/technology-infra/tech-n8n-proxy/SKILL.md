# SKILL: tech-n8n-proxy
## n8n Workflow Orchestration Proxy

Bridges OpenClaw natural language to n8n workflow automation, allowing
agents and CEO to trigger, monitor, and create n8n workflows via chat.
Powers Conductor-level orchestration through visual workflow engine.

### Triggers
- Manual: "run workflow [name]", "trigger [automation]"
- Event: Agent requests n8n workflow execution
- Event: Scheduled workflow completion/failure notification
- Webhook: n8n → OpenClaw callback on workflow events

### What It Does
1. Translates natural language commands to n8n workflow triggers
2. Monitors running workflow executions in real-time
3. Creates new workflows from natural language descriptions
4. Routes workflow results back to requesting agent/department
5. Manages webhook registrations between n8n and OpenClaw
6. Provides workflow execution history and analytics

### Workflow Registry
| Workflow | Description | Trigger |
|---|---|---|
| repo-backup | Backup all 27 repos to secondary storage | Cron: daily |
| news-aggregate | Collect tech news from all sources | Cron: 6 AM |
| deploy-pipeline | Build → test → deploy for any repo | Webhook: git push |
| alert-router | Route alerts to correct department | Event: alert fired |
| report-generator | Generate any department report | Manual: chat command |
| data-sync | Sync data between QUANTUM FORGE and Quasar | Cron: every 4 hours |

### Natural Language → n8n Mapping
```
User: "backup all repos"
  → POST n8n/webhook/repo-backup
  → Response: "Workflow 'repo-backup' triggered. Execution #1247 started."

User: "create a workflow that checks GitHub stars daily"
  → OpenClaw generates n8n workflow JSON
  → POST n8n/api/v1/workflows
  → Response: "Workflow 'github-stars-check' created. ID: 89"

User: "what workflows ran today?"
  → GET n8n/api/v1/executions?startedAfter=[today]
  → Response: "12 workflows ran today. 11 succeeded, 1 failed (alert-router at 3:42 AM)"
```

### n8n Connection
```
OpenClaw (port 18789)
  ↕ HTTP/Webhook
n8n (port 5678)
  ↕ Execute
External APIs, databases, services
```

### Output Format
```
N8N WORKFLOW STATUS

Active Workflows: 14
Executions Today: 23 (22 success, 1 failed)

Recent:
  ✅ repo-backup — completed 4min ago — 27/27 repos backed up
  ✅ news-aggregate — completed 2hr ago — 89 articles collected
  ❌ alert-router — failed 6hr ago — timeout connecting to Matrix Monitor
       → Auto-retry scheduled in 15min

Scheduled Next:
  data-sync — in 47 minutes
  report-generator — tomorrow 6:00 AM
```

### Dependencies
- n8n-proxy skill (clawhub install n8n-proxy)
- n8n instance running (port 5678)
- n8n API key (N8N_API_KEY)
- Conductor agent (for orchestration coordination)
- Webhook endpoint registration
