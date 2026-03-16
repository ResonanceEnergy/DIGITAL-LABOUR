// ============================================
// MATRIX MONITOR v4.0 - ENTERPRISE COMMAND CENTER
// Extracted from matrix_monitor_v4.py for proper IDE support
// ============================================

// ============================================
// STATE & CONFIGURATION
// ============================================
let cpuHistory = [];
let ramHistory = [];
let performanceChart = null;
let cpuSparkline = null;
let ramSparkline = null;
const UPDATE_INTERVAL = 3000; // 3 seconds

// ============================================
// TAB NAVIGATION
// ============================================
document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById('panel-' + tab.dataset.tab).classList.add('active');
    });
});

// ============================================
// CLOCK UPDATE
// ============================================
function updateClock() {
    document.getElementById('clock').textContent = new Date().toLocaleTimeString();
}
setInterval(updateClock, 1000);
updateClock();

// ============================================
// CHARTS INITIALIZATION
// ============================================
function initCharts() {
    // Performance Chart
    const perfCtx = document.getElementById('performance-chart').getContext('2d');
    performanceChart = new Chart(perfCtx, {
        type: 'line',
        data: {
            labels: Array(60).fill(''),
            datasets: [
                {
                    label: 'CPU %',
                    data: Array(60).fill(0),
                    borderColor: '#00ddff',
                    backgroundColor: 'rgba(0, 221, 255, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointRadius: 0
                },
                {
                    label: 'RAM %',
                    data: Array(60).fill(0),
                    borderColor: '#aa66ff',
                    backgroundColor: 'rgba(170, 102, 255, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointRadius: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 0 },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#888' }
                },
                x: {
                    display: false,
                    grid: { display: false }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: { color: '#888', boxWidth: 12 }
                }
            }
        }
    });

    // CPU Sparkline
    const cpuCtx = document.getElementById('cpu-sparkline').getContext('2d');
    cpuSparkline = new Chart(cpuCtx, {
        type: 'line',
        data: {
            labels: Array(20).fill(''),
            datasets: [{
                data: Array(20).fill(0),
                borderColor: '#00ddff',
                borderWidth: 1.5,
                tension: 0.4,
                pointRadius: 0,
                fill: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 0 },
            scales: { x: { display: false }, y: { display: false, min: 0, max: 100 } },
            plugins: { legend: { display: false } }
        }
    });

    // RAM Sparkline
    const ramCtx = document.getElementById('ram-sparkline').getContext('2d');
    ramSparkline = new Chart(ramCtx, {
        type: 'line',
        data: {
            labels: Array(20).fill(''),
            datasets: [{
                data: Array(20).fill(0),
                borderColor: '#aa66ff',
                borderWidth: 1.5,
                tension: 0.4,
                pointRadius: 0,
                fill: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 0 },
            scales: { x: { display: false }, y: { display: false, min: 0, max: 100 } },
            plugins: { legend: { display: false } }
        }
    });
}

// ============================================
// DATA FETCHING
// ============================================
async function fetchData() {
    try {
        const response = await fetch('/api/v4/status');
        const data = await response.json();
        updateDashboard(data);
    } catch (error) {
        console.error('Fetch error:', error);
    }
}

function updateDashboard(data) {
    // Update metrics
    document.getElementById('cpu-value').textContent = data.cpu.toFixed(0) + '%';
    document.getElementById('ram-value').textContent = data.ram.toFixed(0) + '%';

    // Repo Depot status
    const depotStatus = data.repo_depot.active ? 'ACTIVE' : 'OFFLINE';
    const depotEl = document.getElementById('depot-status');
    depotEl.textContent = depotStatus;
    depotEl.style.color = data.repo_depot.active ? 'var(--accent-green)' : 'var(--accent-red)';
    document.getElementById('depot-detail').textContent = data.repo_depot.active ? 'Running' : 'Stopped';

    // Repos built
    const metrics = data.repo_depot.metrics;
    document.getElementById('repos-built').textContent = `${metrics.repos_completed}/${metrics.total_repos}`;
    document.getElementById('repos-detail').textContent = metrics.repos_building > 0 ? `${metrics.repos_building} building` : 'Idle';

    // QFORGE/QUSAR status
    const qforgeEl = document.getElementById('qforge-status');
    qforgeEl.textContent = data.qforge;
    qforgeEl.style.color = data.qforge === 'ACTIVE' ? 'var(--accent-green)' : 'var(--accent-red)';

    const qusarEl = document.getElementById('qusar-status');
    qusarEl.textContent = data.qusar;
    qusarEl.style.color = data.qusar === 'ACTIVE' ? 'var(--accent-green)' : 'var(--accent-red)';

    // PULSAR (Pocket Pulsar - iPhone) status
    const pulsarEl = document.getElementById('pulsar-status');
    const pulsarSync = data.device_sync?.pulsar || {};
    pulsarEl.textContent = pulsarSync.status === 'synced' ? 'SYNCED' : (pulsarSync.status === 'reachable' ? 'ONLINE' : 'OFFLINE');
    pulsarEl.style.color = pulsarSync.status === 'synced' ? 'var(--accent-green)' : (pulsarSync.status === 'reachable' ? 'var(--accent-yellow)' : 'var(--accent-red)');
    document.getElementById('pulsar-detail').textContent = pulsarSync.last_sync ? ('Last sync: ' + pulsarSync.last_sync) : 'No sync data';

    // TITAN (Tablet Titan - iPad) status
    const titanEl = document.getElementById('titan-status');
    const titanSync = data.device_sync?.titan || {};
    titanEl.textContent = titanSync.status === 'synced' ? 'SYNCED' : (titanSync.status === 'reachable' ? 'ONLINE' : 'OFFLINE');
    titanEl.style.color = titanSync.status === 'synced' ? 'var(--accent-green)' : (titanSync.status === 'reachable' ? 'var(--accent-yellow)' : 'var(--accent-red)');
    document.getElementById('titan-detail').textContent = titanSync.last_sync ? ('Last sync: ' + titanSync.last_sync) : 'No sync data';

    // Update charts
    cpuHistory.push(data.cpu);
    ramHistory.push(data.ram);
    if (cpuHistory.length > 60) cpuHistory.shift();
    if (ramHistory.length > 60) ramHistory.shift();

    performanceChart.data.datasets[0].data = [...cpuHistory];
    performanceChart.data.datasets[1].data = [...ramHistory];
    performanceChart.update('none');

    cpuSparkline.data.datasets[0].data = cpuHistory.slice(-20);
    cpuSparkline.update('none');

    ramSparkline.data.datasets[0].data = ramHistory.slice(-20);
    ramSparkline.update('none');

    // Update Repo Depot tab
    document.getElementById('rd-status').textContent = depotStatus;
    document.getElementById('rd-status').style.color = data.repo_depot.active ? 'var(--accent-green)' : 'var(--accent-red)';
    document.getElementById('rd-total').textContent = metrics.total_repos;
    document.getElementById('rd-completed').textContent = metrics.repos_completed;
    document.getElementById('rd-building').textContent = metrics.repos_building;
    document.getElementById('rd-flywheel').textContent = metrics.flywheel_cycles;
    document.getElementById('rd-files').textContent = metrics.files_created;

    // Update repos grid
    updateRepoGrid(data.repos);

    // Update agents
    updateAgents(data.agent_activity);

    // Activity feed
    updateActivityFeed(data.activity_log);

    // System tab
    updateSystemInfo(data.system);

    // Services status
    updateServices(data);
}

function updateRepoGrid(repos) {
    const grid = document.getElementById('repo-grid');
    if (!repos || repos.length === 0) {
        grid.innerHTML = '<p style="color: var(--text-secondary);">No repositories loaded</p>';
        return;
    }

    grid.innerHTML = repos.map(repo => `
        <div class="repo-card">
            <div class="repo-header">
                <div class="repo-name">${repo.name}</div>
                <span class="repo-tier ${repo.tier || 'M'}">${repo.tier || 'M'}</span>
            </div>
            <div class="repo-meta">
                <span>${repo.category || 'project'}</span>
                <span>${repo.visibility || 'private'}</span>
                <span>${repo.status || 'queued'}</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${repo.progress || 0}%"></div>
            </div>
        </div>
    `).join('');
}

function updateAgents(activity) {
    const grid = document.getElementById('agents-grid');

    const optimusHtml = `
        <div class="agent-card" style="border-left: 3px solid var(--accent-red);">
            <div class="agent-header">
                <div class="agent-name">
                    <span class="agent-icon">🤖</span>
                    AGENT OPTIMUS
                </div>
                <span class="status-badge active">Active</span>
            </div>
            <div class="agent-body">
                <div class="agent-task">${activity?.optimus?.active_work?.current_task || 'N/A'}</div>
                <div class="agent-progress">
                    <div class="agent-progress-header">
                        <span>Progress</span>
                        <span>${activity?.optimus?.progress || 0}%</span>
                    </div>
                    <div class="progress-bar" style="height: 6px;">
                        <div class="progress-fill" style="width: ${activity?.optimus?.progress || 0}%; background: linear-gradient(90deg, var(--accent-red), var(--accent-purple));"></div>
                    </div>
                </div>
                <div class="agent-operations">
                    ${(activity?.optimus?.active_work?.active_operations || []).slice(0, 4).map(op => `
                        <div class="operation-item">
                            <div class="operation-dot"></div>
                            ${op}
                        </div>
                    `).join('')}
                </div>
            </div>
        </div>
    `;

    const gasketHtml = `
        <div class="agent-card" style="border-left: 3px solid var(--accent-green);">
            <div class="agent-header">
                <div class="agent-name">
                    <span class="agent-icon">⚙️</span>
                    AGENT GASKET
                </div>
                <span class="status-badge active">Active</span>
            </div>
            <div class="agent-body">
                <div class="agent-task">${activity?.gasket?.active_work?.current_task || 'N/A'}</div>
                <div class="agent-progress">
                    <div class="agent-progress-header">
                        <span>Progress</span>
                        <span>${activity?.gasket?.progress || 0}%</span>
                    </div>
                    <div class="progress-bar" style="height: 6px;">
                        <div class="progress-fill" style="width: ${activity?.gasket?.progress || 0}%; background: linear-gradient(90deg, var(--accent-green), var(--accent-cyan));"></div>
                    </div>
                </div>
                <div class="agent-operations">
                    ${(activity?.gasket?.active_work?.active_operations || []).slice(0, 4).map(op => `
                        <div class="operation-item">
                            <div class="operation-dot"></div>
                            ${op}
                        </div>
                    `).join('')}
                </div>
            </div>
        </div>
    `;

    grid.innerHTML = optimusHtml + gasketHtml;
}

function updateActivityFeed(logs) {
    const feed = document.getElementById('activity-feed');
    const fullLog = document.getElementById('full-activity-log');

    if (!logs || logs.length === 0) return;

    const logsHtml = logs.slice(0, 10).map(log => `
        <div class="activity-item">
            <div class="activity-icon ${log.level}">${getLogIcon(log.level)}</div>
            <div class="activity-content">
                <div class="activity-message">${log.message}</div>
                <div class="activity-time">${log.time_display} | ${log.category}</div>
            </div>
        </div>
    `).join('');

    feed.innerHTML = logsHtml;

    // Full log
    fullLog.innerHTML = logs.map(log => `
        <div class="activity-item">
            <div class="activity-icon ${log.level}">${getLogIcon(log.level)}</div>
            <div class="activity-content">
                <div class="activity-message">${log.message}</div>
                <div class="activity-time">${log.timestamp} | ${log.category}</div>
            </div>
        </div>
    `).join('');
}

function getLogIcon(level) {
    switch(level) {
        case 'success': return '✓';
        case 'error': return '✗';
        case 'warning': return '⚠';
        default: return 'ℹ';
    }
}

function updateSystemInfo(system) {
    if (!system) return;
    document.getElementById('sys-platform').textContent = system.platform || '--';
    document.getElementById('sys-cores').textContent = system.cpu_count || '--';
    document.getElementById('sys-ram').textContent = system.total_ram || '--';
    document.getElementById('sys-python').textContent = system.python_version || '--';
    document.getElementById('sys-uptime').textContent = system.uptime || '--';
}

function updateServices(data) {
    const depotBadge = data.repo_depot.active ?
        '<span class="status-badge active">Active</span>' :
        '<span class="status-badge offline">Offline</span>';
    document.getElementById('svc-repodepot').innerHTML = depotBadge;

    document.getElementById('svc-qforge').innerHTML = data.qforge === 'ACTIVE' ?
        '<span class="status-badge active">Active</span>' :
        '<span class="status-badge offline">Offline</span>';

    document.getElementById('svc-qusar').innerHTML = data.qusar === 'ACTIVE' ?
        '<span class="status-badge active">Active</span>' :
        '<span class="status-badge offline">Offline</span>';

    // Watchdog service status
    document.getElementById('svc-watchdog').innerHTML = data.watchdog === 'ACTIVE' ?
        '<span class="status-badge active">Active</span>' :
        '<span class="status-badge offline">Offline</span>';

    // PULSAR service status
    const pulsarSync = data.device_sync?.pulsar || {};
    document.getElementById('svc-pulsar').innerHTML = pulsarSync.status === 'synced' ?
        '<span class="status-badge active">Synced</span>' :
        (pulsarSync.status === 'reachable' ?
            '<span class="status-badge building">Online</span>' :
            '<span class="status-badge offline">Offline</span>');

    // TITAN service status
    const titanSync = data.device_sync?.titan || {};
    document.getElementById('svc-titan').innerHTML = titanSync.status === 'synced' ?
        '<span class="status-badge active">Synced</span>' :
        (titanSync.status === 'reachable' ?
            '<span class="status-badge building">Online</span>' :
            '<span class="status-badge offline">Offline</span>');
}

// ============================================
// CONTROL FUNCTIONS
// ============================================
async function startRepoDepot() {
    try {
        const response = await fetch('/api/v4/control/start-depot', { method: 'POST' });
        const result = await response.json();
        alert(result.message);
        fetchData();
    } catch (e) {
        alert('Error starting Repo Depot: ' + e);
    }
}

async function stopRepoDepot() {
    try {
        const response = await fetch('/api/v4/control/stop-depot', { method: 'POST' });
        const result = await response.json();
        alert(result.message);
        fetchData();
    } catch (e) {
        alert('Error stopping Repo Depot: ' + e);
    }
}

function restartRepoDepot() {
    stopRepoDepot();
    setTimeout(startRepoDepot, 2000);
}

function checkStatus() {
    fetchData();
    alert('Status refreshed');
}

function startAgents() { alert('Agent control coming soon'); }
function stopAgents() { alert('Agent control coming soon'); }
function runQforge() { alert('QFORGE execution coming soon'); }
function runQusar() { alert('QUSAR execution coming soon'); }
function refreshData() { fetchData(); }
function clearLogs() { document.getElementById('full-activity-log').innerHTML = ''; }
function exportLogs() { alert('Export coming soon'); }
function openDocs() { window.open('/docs', '_blank'); }

// ============================================
// INITIALIZATION
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    fetchData();
    setInterval(fetchData, UPDATE_INTERVAL);
});
