/* MATRIX MAXIMIZER JavaScript */
/* Advanced UI/XI for BIT RAGE LABOUR - Real-time Monitoring & Intervention Platform */
/* Optimized for Quantum Quasar (Mac), Pocket Pulsar (iPhone), Tablet Titan (iPad) */

class MatrixMaximizer {
    constructor() {
        this.currentView = 'dashboard';
        this.charts = {};
        this.intervals = {};
        this.modalOpen = false;
        this.selectedNode = null;
        this.agentCategories = ['all', 'core', 'inner-council', 'portfolio', 'security', 'system'];
        this.currentCategory = 'all';

        this.init();
    }

    init() {
        this.bindEvents();
        this.initializeCharts();
        this.startRealTimeUpdates();
        this.loadInitialData();
        this.setupMatrixVisualization();
    }

    bindEvents() {
        // Navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const view = item.dataset.view;
                this.switchView(view);
            });
        });

        // Agent category tabs
        document.querySelectorAll('.category-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                this.switchAgentCategory(e.target.dataset.category);
            });
        });

        // Intervention forms
        document.getElementById('intervention-form')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitIntervention();
        });

        // Matrix node clicks
        document.addEventListener('click', (e) => {
            if (e.target.closest('.matrix-node')) {
                const node = e.target.closest('.matrix-node');
                this.showNodeDetails(node.dataset.nodeId);
            }
        });

        // Modal close
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal') || e.target.classList.contains('modal-close')) {
                this.closeModal();
            }
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modalOpen) {
                this.closeModal();
            }
        });

        // Window resize
        window.addEventListener('resize', () => {
            this.resizeCharts();
        });
    }

    switchView(view) {
        // Update navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[data-view="${view}"]`).classList.add('active');

        // Update content
        document.querySelectorAll('.content-view').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${view}-view`).classList.add('active');

        this.currentView = view;
        this.updateViewData();
    }

    switchAgentCategory(category) {
        document.querySelectorAll('.category-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-category="${category}"]`).classList.add('active');

        this.currentCategory = category;
        this.filterAgents();
    }

    initializeCharts() {
        // System Performance Chart
        const systemCtx = document.getElementById('system-performance-chart');
        if (systemCtx) {
            this.charts.systemPerformance = new Chart(systemCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'CPU Usage',
                        data: [],
                        borderColor: '#007aff',
                        backgroundColor: 'rgba(0, 122, 255, 0.1)',
                        tension: 0.4,
                        fill: true
                    }, {
                        label: 'Memory Usage',
                        data: [],
                        borderColor: '#30d158',
                        backgroundColor: 'rgba(48, 209, 88, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top',
                            labels: {
                                color: '#ffffff',
                                font: { size: 12 }
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: { color: 'rgba(255, 255, 255, 0.1)' },
                            ticks: { color: '#8892a0', font: { size: 11 } }
                        },
                        y: {
                            grid: { color: 'rgba(255, 255, 255, 0.1)' },
                            ticks: { color: '#8892a0', font: { size: 11 } }
                        }
                    },
                    animation: {
                        duration: 1000,
                        easing: 'easeInOutQuart'
                    }
                }
            });
        }

        // Agent Activity Chart
        const agentCtx = document.getElementById('agent-activity-chart');
        if (agentCtx) {
            this.charts.agentActivity = new Chart(agentCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Active', 'Idle', 'Error', 'Maintenance'],
                    datasets: [{
                        data: [65, 25, 5, 5],
                        backgroundColor: [
                            '#30d158',
                            '#64d2ff',
                            '#ff453a',
                            '#ff9f0a'
                        ],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'bottom',
                            labels: {
                                color: '#ffffff',
                                font: { size: 12 },
                                padding: 20
                            }
                        }
                    },
                    cutout: '60%'
                }
            });
        }

        // Portfolio Performance Chart
        const portfolioCtx = document.getElementById('portfolio-performance-chart');
        if (portfolioCtx) {
            this.charts.portfolioPerformance = new Chart(portfolioCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Portfolio Value',
                        data: [],
                        borderColor: '#30d158',
                        backgroundColor: 'rgba(48, 209, 88, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        x: {
                            grid: { color: 'rgba(255, 255, 255, 0.1)' },
                            ticks: { color: '#8892a0', font: { size: 11 } }
                        },
                        y: {
                            grid: { color: 'rgba(255, 255, 255, 0.1)' },
                            ticks: {
                                color: '#8892a0',
                                font: { size: 11 },
                                callback: function (value) {
                                    return '$' + value.toLocaleString();
                                }
                            }
                        }
                    }
                }
            });
        }

        // Security Threat Chart
        const securityCtx = document.getElementById('security-threat-chart');
        if (securityCtx) {
            this.charts.securityThreats = new Chart(securityCtx, {
                type: 'bar',
                data: {
                    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                    datasets: [{
                        label: 'Threats Detected',
                        data: [12, 19, 3, 5, 2, 3, 9],
                        backgroundColor: 'rgba(255, 69, 58, 0.6)',
                        borderColor: '#ff453a',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        x: {
                            grid: { color: 'rgba(255, 255, 255, 0.1)' },
                            ticks: { color: '#8892a0', font: { size: 11 } }
                        },
                        y: {
                            grid: { color: 'rgba(255, 255, 255, 0.1)' },
                            ticks: { color: '#8892a0', font: { size: 11 } }
                        }
                    }
                }
            });
        }
    }

    startRealTimeUpdates() {
        // Update system metrics every 5 seconds
        this.intervals.systemMetrics = setInterval(() => {
            this.updateSystemMetrics();
        }, 5000);

        // Update agent status every 10 seconds
        this.intervals.agentStatus = setInterval(() => {
            this.updateAgentStatus();
        }, 10000);

        // Update alerts every 30 seconds
        this.intervals.alerts = setInterval(() => {
            this.updateAlerts();
        }, 30000);

        // Update time display every second
        this.intervals.time = setInterval(() => {
            this.updateTimeDisplay();
        }, 1000);
    }

    async loadInitialData() {
        try {
            const response = await fetch('/api/matrix');
            const data = await response.json();
            this.updateDashboard(data);
        } catch (error) {
            console.error('Failed to load initial data:', error);
        }
    }

    async updateSystemMetrics() {
        try {
            const response = await fetch('/api/system');
            const data = await response.json();

            // Update chart data
            if (this.charts.systemPerformance) {
                const chart = this.charts.systemPerformance;
                const now = new Date().toLocaleTimeString();

                // Add new data point
                chart.data.labels.push(now);
                chart.data.datasets[0].data.push(data.system.cpu_percent);
                chart.data.datasets[1].data.push(data.system.memory.percent);

                // Keep only last 20 points
                if (chart.data.labels.length > 20) {
                    chart.data.labels.shift();
                    chart.data.datasets[0].data.shift();
                    chart.data.datasets[1].data.shift();
                }

                chart.update('none');
            }

            // Update metric displays
            this.updateMetricDisplays(data);
        } catch (error) {
            console.error('Failed to update system metrics:', error);
        }
    }

    async updateAgentStatus() {
        try {
            const response = await fetch('/api/agents');
            const data = await response.json();

            // Update agent cards
            this.updateAgentCards(data.agents);

            // Update activity chart
            if (this.charts.agentActivity) {
                // Calculate status counts from agent data
                const agents = Object.values(data.agents || {});
                const active = agents.filter(a => a.status === 'active').length;
                const idle = agents.filter(a => a.status === 'idle').length;
                const error = agents.filter(a => a.status === 'error').length;
                const maintenance = agents.filter(a => a.status === 'maintenance').length;

                this.charts.agentActivity.data.datasets[0].data = [
                    active,
                    idle,
                    error,
                    maintenance
                ];
                this.charts.agentActivity.update('none');
            }
        } catch (error) {
            console.error('Failed to update agent status:', error);
        }
    }

    async updateAlerts() {
        try {
            const response = await fetch('/api/alerts');
            const data = await response.json();

            this.updateAlertsDisplay(data.alerts);
            this.updateAlertIndicator(data.count);
        } catch (error) {
            console.error('Failed to update alerts:', error);
        }
    }

    updateTimeDisplay() {
        const now = new Date();
        const timeElement = document.querySelector('.current-time');
        const dateElement = document.querySelector('.current-date');

        if (timeElement) {
            timeElement.textContent = now.toLocaleTimeString('en-US', {
                hour12: false,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        }

        if (dateElement) {
            dateElement.textContent = now.toLocaleDateString('en-US', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        }
    }

    updateDashboard(data) {
        // Update system health display
        const healthElement = document.getElementById('system-health');
        if (healthElement && data.system_health) {
            healthElement.textContent = data.system_health.toFixed(1) + '%';
        }

        // Update active agents count
        const agentsElement = document.getElementById('active-agents');
        if (agentsElement && data.online_nodes) {
            agentsElement.textContent = data.online_nodes;
        }

        // Update matrix visualization
        this.updateMatrixVisualization(data.matrix);

        // Update alerts (if available)
        if (data.alerts) {
            this.updateAlertsDisplay(data.alerts);
        }
    }

    updateMatrixVisualization(matrixData) {
        if (!matrixData) return;

        const matrixContainer = document.querySelector('.matrix-visualization');
        if (!matrixContainer) return;

        // Create matrix nodes
        const nodesHtml = matrixData.map(node => {
            const statusClass = node.status === 'online' ? 'online' : 'offline';
            const typeClass = node.type || 'unknown';

            return `
                <div class="matrix-node ${statusClass} ${typeClass}" data-node-id="${node.id}">
                    <div class="node-header">
                        <div class="node-icon">${this.getNodeIcon(node.type)}</div>
                        <div class="node-status"></div>
                    </div>
                    <div class="node-info">
                        <div class="node-name">${node.name}</div>
                        <div class="node-health">${node.health}%</div>
                    </div>
                    <div class="node-metrics">
                        ${node.metrics ? node.metrics.slice(0, 2).map(metric =>
                `<div class="metric">${metric.label}: ${metric.value}</div>`
            ).join('') : ''}
                    </div>
                </div>
            `;
        }).join('');

        matrixContainer.innerHTML = nodesHtml;
    }

    getNodeIcon(type) {
        const icons = {
            'device': '💻',
            'agent': '🤖',
            'memory': '🧠',
            'finance': '💰',
            'network': '🌐'
        };
        return icons[type] || '⚡';
    }

    updateGlobalMetrics(metrics) {
        const metricsContainer = document.querySelector('.global-metrics');
        if (!metricsContainer) return;

        metricsContainer.innerHTML = `
            <div class="metric-item">
                <div class="metric-label">Agents</div>
                <div class="metric-value">${metrics.agents}</div>
            </div>
            <div class="metric-item">
                <div class="metric-label">CPU</div>
                <div class="metric-value">${metrics.cpu}%</div>
            </div>
            <div class="metric-item">
                <div class="metric-label">Memory</div>
                <div class="metric-value">${metrics.memory}%</div>
            </div>
            <div class="metric-item">
                <div class="metric-label">Alerts</div>
                <div class="metric-value">${metrics.alerts}</div>
            </div>
        `;
    }

    updateActivityFeed(activities) {
        const activityList = document.querySelector('.activity-list');
        if (!activityList) return;

        activityList.innerHTML = activities.map(activity => `
            <div class="activity-item">
                <div class="activity-time">${activity.time}</div>
                <div class="activity-content">
                    <span class="activity-icon">${activity.icon}</span>
                    <div class="activity-text">${activity.message}</div>
                </div>
            </div>
        `).join('');
    }

    updateAlertsDisplay(alerts) {
        const alertsList = document.querySelector('.alerts-list');
        if (!alertsList) return;

        alertsList.innerHTML = alerts.map(alert => `
            <div class="alert-item ${alert.type}">
                <div class="alert-header">
                    <span class="alert-icon">${alert.icon}</span>
                    <div class="alert-title">${alert.title}</div>
                    <div class="alert-time">${alert.time}</div>
                </div>
                <div class="alert-message">${alert.message}</div>
                <div class="alert-actions">
                    <button class="btn btn-xs btn-secondary">Acknowledge</button>
                    <button class="btn btn-xs btn-primary">Investigate</button>
                </div>
            </div>
        `).join('');
    }

    updateAlertIndicator(count) {
        const indicator = document.querySelector('.alert-indicator');
        const countElement = document.querySelector('.alert-count');

        if (indicator && countElement) {
            if (count > 0) {
                indicator.style.display = 'flex';
                countElement.textContent = count;
            } else {
                indicator.style.display = 'none';
            }
        }
    }

    updateMetricDisplays(data) {
        // Update individual metric cards
        const cpuElement = document.querySelector('[data-metric="cpu"] .metric-value');
        const memoryElement = document.querySelector('[data-metric="memory"] .metric-value');
        const diskElement = document.querySelector('[data-metric="disk"] .metric-value');

        if (cpuElement) cpuElement.textContent = `${data.system.cpu_percent.toFixed(1)}%`;
        if (memoryElement) memoryElement.textContent = `${data.system.memory.percent.toFixed(1)}%`;
        if (diskElement) diskElement.textContent = `${data.system.disk.percent.toFixed(1)}%`;
    }

    updateAgentCards(agents) {
        const agentsGrid = document.querySelector('.agents-grid');
        if (!agentsGrid) return;

        agentsGrid.innerHTML = agents.map(agent => `
            <div class="agent-card" data-agent-id="${agent.id}">
                <div class="agent-header">
                    <div class="agent-avatar">${agent.icon}</div>
                    <div class="agent-status" style="background: ${agent.statusColor}"></div>
                </div>
                <div class="agent-info">
                    <h4>${agent.name}</h4>
                    <p>${agent.description}</p>
                </div>
                <div class="agent-metrics">
                    <span class="metric">CPU: ${agent.cpu}%</span>
                    <span class="metric">Mem: ${agent.memory}%</span>
                    <span class="metric">Tasks: ${agent.tasks}</span>
                </div>
                <div class="agent-actions">
                    <button class="btn btn-xs btn-secondary" onclick="matrixMaximizer.restartAgent('${agent.id}')">Restart</button>
                    <button class="btn btn-xs btn-primary" onclick="matrixMaximizer.showAgentDetails('${agent.id}')">Details</button>
                </div>
            </div>
        `).join('');
    }

    setupMatrixVisualization() {
        // Initialize matrix nodes with connections
        this.drawMatrixConnections();
    }

    drawMatrixConnections() {
        // This would use D3.js or Canvas API to draw connections between matrix nodes
        // For now, we'll use CSS-based connections
        const nodes = document.querySelectorAll('.matrix-node');
        nodes.forEach(node => {
            const connections = node.dataset.connections?.split(',') || [];
            connections.forEach(connectionId => {
                this.createConnection(node, document.querySelector(`[data-node-id="${connectionId}"]`));
            });
        });
    }

    createConnection(fromNode, toNode) {
        if (!fromNode || !toNode) return;

        const svg = document.querySelector('.matrix-visualization svg') || this.createMatrixSVG();
        const fromRect = fromNode.getBoundingClientRect();
        const toRect = toNode.getBoundingClientRect();
        const containerRect = svg.getBoundingClientRect();

        const x1 = fromRect.left + fromRect.width / 2 - containerRect.left;
        const y1 = fromRect.top + fromRect.height / 2 - containerRect.top;
        const x2 = toRect.left + toRect.width / 2 - containerRect.left;
        const y2 = toRect.top + toRect.height / 2 - containerRect.top;

        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', x1);
        line.setAttribute('y1', y1);
        line.setAttribute('x2', x2);
        line.setAttribute('y2', y2);
        line.setAttribute('stroke', 'rgba(0, 122, 255, 0.3)');
        line.setAttribute('stroke-width', '2');

        svg.appendChild(line);
    }

    createMatrixSVG() {
        const visualization = document.querySelector('.matrix-visualization');
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.style.position = 'absolute';
        svg.style.top = '0';
        svg.style.left = '0';
        svg.style.width = '100%';
        svg.style.height = '100%';
        svg.style.pointerEvents = 'none';
        svg.style.zIndex = '1';
        visualization.appendChild(svg);
        return svg;
    }

    showNodeDetails(nodeId) {
        this.selectedNode = nodeId;
        const modal = document.getElementById('matrix-details');
        const detailsContent = document.querySelector('.details-content');

        // Fetch node details
        fetch(`/api/matrix/node/${nodeId}`)
            .then(response => response.json())
            .then(data => {
                detailsContent.innerHTML = `
                    <div class="detail-item">
                        <span class="detail-label">Name</span>
                        <span class="detail-value">${data.name}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Type</span>
                        <span class="detail-value">${data.type}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Status</span>
                        <span class="detail-value">${data.status}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">CPU Usage</span>
                        <span class="detail-value">${data.cpu}%</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Memory Usage</span>
                        <span class="detail-value">${data.memory}%</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Connections</span>
                        <span class="detail-value">${data.connections}</span>
                    </div>
                `;

                modal.style.display = 'flex';
                this.modalOpen = true;
            })
            .catch(error => {
                console.error('Failed to load node details:', error);
            });
    }

    closeModal() {
        document.querySelectorAll('.modal').forEach(modal => {
            modal.style.display = 'none';
        });
        this.modalOpen = false;
        this.selectedNode = null;
    }

    async submitIntervention() {
        const form = document.getElementById('intervention-form');
        const formData = new FormData(form);
        const intervention = {
            type: formData.get('intervention-type'),
            target: formData.get('target'),
            parameters: formData.get('parameters'),
            priority: formData.get('priority')
        };

        try {
            const response = await fetch('/api/interventions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(intervention)
            });

            if (response.ok) {
                this.showNotification('Intervention submitted successfully', 'success');
                form.reset();
                this.updateInterventionQueue();
            } else {
                throw new Error('Failed to submit intervention');
            }
        } catch (error) {
            console.error('Intervention submission failed:', error);
            this.showNotification('Failed to submit intervention', 'error');
        }
    }

    async updateInterventionQueue() {
        try {
            const response = await fetch('/api/interventions/queue');
            const data = await response.json();

            const queueList = document.querySelector('.queue-list');
            if (queueList) {
                queueList.innerHTML = data.interventions.map(intervention => `
                    <div class="queue-item ${intervention.status}">
                        <div class="queue-info">
                            <h4>${intervention.type}</h4>
                            <p>${intervention.description}</p>
                        </div>
                        <div class="queue-status ${intervention.status}">
                            ${intervention.status}
                        </div>
                    </div>
                `).join('');
            }
        } catch (error) {
            console.error('Failed to update intervention queue:', error);
        }
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <span class="notification-icon">${type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ'}</span>
            <span class="notification-message">${message}</span>
        `;

        // Add to page
        document.body.appendChild(notification);

        // Animate in
        setTimeout(() => notification.classList.add('show'), 10);

        // Remove after 5 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => document.body.removeChild(notification), 300);
        }, 5000);
    }

    filterAgents() {
        const agentCards = document.querySelectorAll('.agent-card');
        agentCards.forEach(card => {
            if (this.currentCategory === 'all' || card.dataset.category === this.currentCategory) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
    }

    updateViewData() {
        // Update data based on current view
        switch (this.currentView) {
            case 'performance':
                this.updatePerformanceData();
                break;
            case 'intelligence':
                this.updateIntelligenceData();
                break;
            case 'portfolio':
                this.updatePortfolioData();
                break;
            case 'security':
                this.updateSecurityData();
                break;
        }
    }

    async updatePerformanceData() {
        try {
            const response = await fetch('/api/performance/metrics');
            const data = await response.json();

            // Update performance charts and metrics
            this.updatePerformanceCharts(data);
        } catch (error) {
            console.error('Failed to update performance data:', error);
        }
    }

    async updateIntelligenceData() {
        try {
            const response = await fetch('/api/intelligence/insights');
            const data = await response.json();

            this.updateInsightsDisplay(data.insights);
            this.updatePredictionsDisplay(data.predictions);
        } catch (error) {
            console.error('Failed to update intelligence data:', error);
        }
    }

    async updatePortfolioData() {
        try {
            const response = await fetch('/api/portfolio/status');
            const data = await response.json();

            this.updatePortfolioDisplay(data);
        } catch (error) {
            console.error('Failed to update portfolio data:', error);
        }
    }

    async updateSecurityData() {
        try {
            const response = await fetch('/api/security/status');
            const data = await response.json();

            this.updateSecurityDisplay(data);
        } catch (error) {
            console.error('Failed to update security data:', error);
        }
    }

    updatePerformanceCharts(data) {
        // Update performance-specific charts
        if (this.charts.systemPerformance) {
            // Update with performance data
        }
    }

    updateInsightsDisplay(insights) {
        const insightsList = document.querySelector('.insights-list');
        if (insightsList) {
            insightsList.innerHTML = insights.map(insight => `
                <div class="insight-card">
                    <div class="insight-header">
                        <span class="insight-icon">${insight.icon}</span>
                        <span class="insight-priority ${insight.priority}">${insight.priority}</span>
                    </div>
                    <h4>${insight.title}</h4>
                    <p>${insight.description}</p>
                </div>
            `).join('');
        }
    }

    updatePredictionsDisplay(predictions) {
        const predictionsList = document.querySelector('.predictions-list');
        if (predictionsList) {
            predictionsList.innerHTML = predictions.map(prediction => `
                <div class="prediction-card">
                    <div class="prediction-header">
                        <span class="prediction-icon">${prediction.icon}</span>
                        <span class="prediction-confidence ${prediction.confidence}">${prediction.confidence}%</span>
                    </div>
                    <h4>${prediction.title}</h4>
                    <p>${prediction.description}</p>
                </div>
            `).join('');
        }
    }

    updatePortfolioDisplay(data) {
        // Update portfolio summary cards
        const summaryCards = document.querySelectorAll('.summary-card');
        summaryCards.forEach((card, index) => {
            const metric = data.summary[index];
            if (metric) {
                card.querySelector('h3').textContent = metric.label;
                card.querySelector('.value-large').textContent = metric.value;
                card.querySelector('.change').textContent = metric.change;
                card.querySelector('.change').className = `change ${metric.changeType}`;
            }
        });

        // Update portfolio chart
        if (this.charts.portfolioPerformance) {
            // Update chart data
        }
    }

    updateSecurityDisplay(data) {
        // Update security status
        const threatLevel = document.querySelector('.threat-level');
        if (threatLevel) {
            threatLevel.className = `threat-level ${data.threatLevel}`;
            threatLevel.textContent = data.threatLevel.toUpperCase();
        }

        // Update threat count
        const threatCount = document.querySelector('.threat-count');
        if (threatCount) {
            threatCount.textContent = data.threatCount;
        }

        // Update access logs
        const accessLog = document.querySelector('.access-log');
        if (accessLog) {
            accessLog.innerHTML = data.accessLogs.map(log => `
                <div class="log-entry">
                    <span class="log-time">${log.time}</span>
                    <span class="log-action">${log.action}</span>
                    <span class="log-status ${log.status}">${log.status}</span>
                </div>
            `).join('');
        }
    }

    resizeCharts() {
        Object.values(this.charts).forEach(chart => {
            if (chart) {
                chart.resize();
            }
        });
    }

    restartAgent(agentId) {
        fetch(`/api/agents/${agentId}/restart`, { method: 'POST' })
            .then(response => {
                if (response.ok) {
                    this.showNotification(`Agent ${agentId} restarted successfully`, 'success');
                } else {
                    throw new Error('Restart failed');
                }
            })
            .catch(error => {
                console.error('Failed to restart agent:', error);
                this.showNotification(`Failed to restart agent ${agentId}`, 'error');
            });
    }

    showAgentDetails(agentId) {
        // Show agent details modal
        this.showNodeDetails(agentId);
    }

    destroy() {
        // Clear all intervals
        Object.values(this.intervals).forEach(interval => {
            clearInterval(interval);
        });

        // Destroy charts
        Object.values(this.charts).forEach(chart => {
            if (chart) {
                chart.destroy();
            }
        });
    }
}

// Initialize Matrix Maximizer when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.matrixMaximizer = new MatrixMaximizer();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.matrixMaximizer) {
        window.matrixMaximizer.destroy();
    }
});
