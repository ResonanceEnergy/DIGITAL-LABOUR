# gasket-dashboard

## Dynamic Dashboard with Sub-Agent Spawning

**Type**: always-on
**Trigger**: cron (every 5 minutes) + on-demand
**Model**: any

## Description

Spawns parallel sub-agents to fetch data from multiple sources simultaneously (GitHub stars, X followers, system health, Polymarket positions, repo metrics). Aggregates into a unified dashboard rendered as text, HTML, or Canvas. Avoids sequential blocking and rate limits through parallel execution.

## Key Patterns

- **Sub-agent spawning**: `sessions_spawn(label="dash-github", task="fetch GitHub metrics")` for each data source
- **Parallel fetch**: all sub-agents run concurrently, results collected
- **Alert thresholds**: notify if GitHub stars change > 50/hr, CPU > 90%, disk > 85%
- **Historical metrics**: PostgreSQL/SQLite for trend analysis
- **Canvas/HTML render**: rich dashboard output, not just text

## Data Sources

| Source | Metric | Refresh |
|--------|--------|---------|
| GitHub API | stars, forks, issues, PRs | 5 min |
| System (psutil) | CPU, RAM, disk, processes | 1 min |
| repo_depot_status.json | agent task completion | 5 min |
| OpenClaw Gateway | health, session count, memory | 5 min |
| QUSAR/QFORGE | build status, feedback loops | 15 min |

## Integration with GASKET

```python
async def spawn_dashboard_agents(self):
    """Spawn parallel sub-agents for dashboard data collection."""
    sources = ['github', 'system', 'gateway', 'qusar', 'repo_depot']
    tasks = [self._fetch_source(src) for src in sources]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return self._aggregate_dashboard(results)
```

## Alert Rules

- CPU sustained > 90% for 3 checks → alert + auto-optimize
- Disk > 85% → alert + identify large files
- Gateway unhealthy → alert + self-heal attempt
- GitHub stars spike → celebration notification

## Output Format

Morning brief includes dashboard summary. On-demand `dashboard` command returns full metrics with sparkline trends.

## Super-Agency Specific

- Monitors both QUANTUM FORGE (192.168.1.200) and Quantum Quasar (192.168.1.100)
- Tracks all 5 GASKET async loops
- Cross-references repo_depot_status.json for agent productivity metrics
