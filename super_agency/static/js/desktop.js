// Desktop JavaScript for Quantum Quasar
// Optimized for MacBook Pro M1 - High-performance desktop interface
// Enhanced with real-time data updates and Chart.js integration

class QuantumQuasarDesktop {
    constructor() {
        this.currentSection = 'dashboard';
        this.charts = {};
        this.updateIntervals = {};
        this.matrixData = {};
        this.agentData = {};
        this.systemData = {};
        this.portfolioData = {};
        this.analyticsData = {};
        this.intelligenceData = {};
        this.securityData = {};

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializeCharts();
        this.startRealTimeUpdates();
        this.loadInitialData();
        this.setupKeyboardShortcuts();
        this.setupTouchGestures();
    }

    setupEventListeners() {
        // Navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const section = item.dataset.section;
                this.switchSection(section);
            });
        });

        // Action buttons
        document.querySelectorAll('.action-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.handleAction(e.target.dataset.action);
            });
        });

        // Matrix controls
        document.querySelectorAll('.matrix-control').forEach(control => {
            control.addEventListener('input', (e) => {
                this.updateMatrixParameter(e.target.name, e.target.value);
            });
        });

        // Agent controls
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('agent-action')) {
                this.handleAgentAction(e.target.dataset.agent, e.target.dataset.action);
            }
        });

        // Window resize
        window.addEventListener('resize', () => {
            this.handleResize();
        });

        // Online/offline detection
        window.addEventListener('online', () => this.handleConnectivityChange(true));
        window.addEventListener('offline', () => this.handleConnectivityChange(false));
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Cmd/Ctrl + number shortcuts for sections
            if (e.metaKey || e.ctrlKey) {
                const sections = ['dashboard', 'agents', 'systems', 'matrix', 'portfolio', 'analytics', 'intelligence', 'security'];
                const num = parseInt(e.key);
                if (num >= 1 && num <= sections.length) {
                    e.preventDefault();
                    this.switchSection(sections[num - 1]);
                }
            }

            // Cmd/Ctrl + R for refresh
            if ((e.metaKey || e.ctrlKey) && e.key === 'r') {
                e.preventDefault();
                this.refreshAllData();
            }

            // Escape to close modals or return to dashboard
            if (e.key === 'Escape') {
                this.closeModals();
            }
        });
    }

    setupTouchGestures() {
        let startX = 0;
        let startY = 0;

        document.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
        });

        document.addEventListener('touchend', (e) => {
            const endX = e.changedTouches[0].clientX;
            const endY = e.changedTouches[0].clientY;
            const diffX = startX - endX;
            const diffY = startY - endY;

            // Horizontal swipe for navigation
            if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > 50) {
                const sections = ['dashboard', 'agents', 'systems', 'matrix', 'portfolio', 'analytics', 'intelligence', 'security'];
                const currentIndex = sections.indexOf(this.currentSection);

                if (diffX > 0 && currentIndex < sections.length - 1) {
                    // Swipe left - next section
                    this.switchSection(sections[currentIndex + 1]);
                } else if (diffX < 0 && currentIndex > 0) {
                    // Swipe right - previous section
                    this.switchSection(sections[currentIndex - 1]);
                }
            }
        });
    }

    switchSection(sectionName) {
        // Update navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[data-section="${sectionName}"]`).classList.add('active');

        // Update content
        document.querySelectorAll('.content-section').forEach(section => {
            section.classList.remove('active');
        });
        document.getElementById(`${sectionName}-section`).classList.add('active');

        this.currentSection = sectionName;

        // Load section-specific data
        this.loadSectionData(sectionName);

        // Update URL hash
        window.location.hash = sectionName;
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
                    }, {
                        label: 'Network I/O',
                        data: [],
                        borderColor: '#ff9f0a',
                        backgroundColor: 'rgba(255, 159, 10, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top'
                        }
                    },
                    scales: {
                        x: {
                            display: true,
                            title: {
                                display: true,
                                text: 'Time'
                            }
                        },
                        y: {
                            display: true,
                            title: {
                                display: true,
                                text: 'Usage (%)'
                            },
                            min: 0,
                            max: 100
                        }
                    }
                }
            });
        }

        // Matrix Visualization Chart
        const matrixCtx = document.getElementById('matrix-visualization-chart');
        if (matrixCtx) {
            this.charts.matrixVisualization = new Chart(matrixCtx, {
                type: 'radar',
                data: {
                    labels: ['Performance', 'Efficiency', 'Stability', 'Security', 'Intelligence', 'Adaptability'],
                    datasets: [{
                        label: 'Current State',
                        data: [85, 92, 88, 95, 78, 82],
                        borderColor: '#007aff',
                        backgroundColor: 'rgba(0, 122, 255, 0.2)',
                        pointBackgroundColor: '#007aff',
                        pointBorderColor: '#fff',
                        pointHoverBackgroundColor: '#fff',
                        pointHoverBorderColor: '#007aff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    elements: {
                        line: {
                            borderWidth: 2
                        }
                    },
                    scales: {
                        r: {
                            beginAtZero: true,
                            max: 100,
                            ticks: {
                                stepSize: 20
                            }
                        }
                    }
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
                            display: true,
                            title: {
                                display: true,
                                text: 'Time'
                            }
                        },
                        y: {
                            display: true,
                            title: {
                                display: true,
                                text: 'Value ($)'
                            }
                        }
                    }
                }
            });
        }

        // Analytics Charts
        this.initializeAnalyticsCharts();
    }

    initializeAnalyticsCharts() {
        // Agent Performance Chart
        const agentCtx = document.getElementById('agent-performance-chart');
        if (agentCtx) {
            this.charts.agentPerformance = new Chart(agentCtx, {
                type: 'bar',
                data: {
                    labels: ['Council', 'Daily Brief', 'Orchestrator', 'Repo Sentry', 'Common'],
                    datasets: [{
                        label: 'Tasks Completed',
                        data: [45, 32, 28, 19, 67],
                        backgroundColor: [
                            'rgba(0, 122, 255, 0.8)',
                            'rgba(48, 209, 88, 0.8)',
                            'rgba(255, 159, 10, 0.8)',
                            'rgba(255, 69, 58, 0.8)',
                            'rgba(142, 142, 147, 0.8)'
                        ],
                        borderRadius: 4
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
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Tasks'
                            }
                        }
                    }
                }
            });
        }

        // System Health Chart
        const healthCtx = document.getElementById('system-health-chart');
        if (healthCtx) {
            this.charts.systemHealth = new Chart(healthCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Optimal', 'Good', 'Warning', 'Critical'],
                    datasets: [{
                        data: [65, 25, 8, 2],
                        backgroundColor: [
                            '#30d158',
                            '#007aff',
                            '#ff9f0a',
                            '#ff453a'
                        ],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });
        }
    }

    startRealTimeUpdates() {
        // Update system metrics every 5 seconds
        this.updateIntervals.system = setInterval(() => {
            this.updateSystemMetrics();
        }, 5000);

        // Update matrix data every 10 seconds
        this.updateIntervals.matrix = setInterval(() => {
            this.updateMatrixData();
        }, 10000);

        // Update agent status every 15 seconds
        this.updateIntervals.agents = setInterval(() => {
            this.updateAgentStatus();
        }, 15000);

        // Update portfolio data every 30 seconds
        this.updateIntervals.portfolio = setInterval(() => {
            this.updatePortfolioData();
        }, 30000);

        // Update time every second
        this.updateIntervals.time = setInterval(() => {
            this.updateTime();
        }, 1000);
    }

    async loadInitialData() {
        try {
            const response = await fetch('/api/matrix');
            const data = await response.json();
            this.updateDashboardWithData(data);
        } catch (error) {
            console.error('Failed to load initial data:', error);
        }
    }

    async loadSectionData(section) {
        try {
            switch (section) {
                case 'dashboard':
                    await this.loadDashboardData();
                    break;
                case 'agents':
                    await this.loadAgentData();
                    break;
                case 'systems':
                    await this.loadSystemData();
                    break;
                case 'matrix':
                    await this.loadMatrixData();
                    break;
                case 'portfolio':
                    await this.loadPortfolioData();
                    break;
                case 'analytics':
                    await this.loadAnalyticsData();
                    break;
                case 'intelligence':
                    await this.loadIntelligenceData();
                    break;
                case 'security':
                    await this.loadSecurityData();
                    break;
            }
        } catch (error) {
            console.error(`Failed to load ${section} data:`, error);
        }
    }

    async loadDashboardData() {
        const response = await fetch('/api/matrix');
        const data = await response.json();
        this.updateDashboardWithData(data);
    }

    async loadAgentData() {
        const response = await fetch('/api/agents');
        const data = await response.json();
        this.updateAgentCards(data);
    }

    async loadSystemData() {
        const response = await fetch('/api/systems');
        const data = await response.json();
        this.updateSystemCards(data);
    }

    async loadMatrixData() {
        const response = await fetch('/api/matrix');
        const data = await response.json();
        this.updateMatrixVisualization(data);
    }

    async loadPortfolioData() {
        const response = await fetch('/api/portfolio');
        const data = await response.json();
        this.updatePortfolioDisplay(data);
    }

    async loadAnalyticsData() {
        const response = await fetch('/api/analytics');
        const data = await response.json();
        this.updateAnalyticsCharts(data);
    }

    async loadIntelligenceData() {
        const response = await fetch('/api/intelligence');
        const data = await response.json();
        this.updateIntelligenceDisplay(data);
    }

    async loadSecurityData() {
        const response = await fetch('/api/security');
        const data = await response.json();
        this.updateSecurityDisplay(data);
    }

    updateDashboardWithData(data) {
        // Update metrics
        this.updateMetrics(data.metrics);

        // Update activity feed
        this.updateActivityFeed(data.activity);

        // Update alerts
        this.updateAlerts(data.alerts);

        // Update charts
        this.updateSystemPerformanceChart(data.performance);
    }

    updateMetrics(metrics) {
        // Update metric cards
        Object.keys(metrics).forEach(key => {
            const element = document.getElementById(`${key}-metric`);
            if (element) {
                element.textContent = metrics[key].value;
                const trendElement = element.parentElement.querySelector('.metric-trend');
                if (trendElement) {
                    trendElement.textContent = metrics[key].trend;
                    trendElement.className = `metric-trend ${metrics[key].trendClass}`;
                }
            }
        });
    }

    updateActivityFeed(activities) {
        const container = document.getElementById('activity-list');
        if (!container) return;

        container.innerHTML = activities.map(activity => `
            <div class="activity-item">
                <span class="activity-time">${activity.time}</span>
                <div class="activity-content">
                    <span class="activity-icon">${activity.icon}</span>
                    <span class="activity-text">${activity.text}</span>
                </div>
            </div>
        `).join('');
    }

    updateAlerts(alerts) {
        const container = document.getElementById('alerts-list');
        if (!container) return;

        container.innerHTML = alerts.map(alert => `
            <div class="alert-item ${alert.type}">
                <span class="alert-icon">${alert.icon}</span>
                <div class="alert-content">
                    <div class="alert-title">${alert.title}</div>
                    <div class="alert-time">${alert.time}</div>
                </div>
            </div>
        `).join('');
    }

    updateSystemPerformanceChart(performance) {
        if (!this.charts.systemPerformance) return;

        const chart = this.charts.systemPerformance;
        const now = new Date().toLocaleTimeString();

        // Add new data point
        chart.data.labels.push(now);
        chart.data.datasets[0].data.push(performance.cpu);
        chart.data.datasets[1].data.push(performance.memory);
        chart.data.datasets[2].data.push(performance.network);

        // Keep only last 20 data points
        if (chart.data.labels.length > 20) {
            chart.data.labels.shift();
            chart.data.datasets.forEach(dataset => dataset.data.shift());
        }

        chart.update('none');
    }

    updateAgentCards(agents) {
        const container = document.getElementById('agents-grid');
        if (!container) return;

        container.innerHTML = agents.map(agent => `
            <div class="agent-card">
                <div class="agent-header">
                    <div class="agent-avatar">${agent.icon}</div>
                    <div class="agent-status" style="background: ${agent.statusColor}"></div>
                </div>
                <div class="agent-info">
                    <h4>${agent.name}</h4>
                    <p>${agent.description}</p>
                </div>
                <div class="agent-metrics">
                    <span class="metric">Tasks: ${agent.tasks}</span>
                    <span class="metric">Uptime: ${agent.uptime}</span>
                </div>
                <div class="agent-actions">
                    <button class="btn btn-sm agent-action" data-agent="${agent.id}" data-action="start">Start</button>
                    <button class="btn btn-sm agent-action" data-agent="${agent.id}" data-action="stop">Stop</button>
                    <button class="btn btn-sm agent-action" data-agent="${agent.id}" data-action="config">Config</button>
                </div>
            </div>
        `).join('');
    }

    updateSystemCards(systems) {
        const container = document.getElementById('systems-overview');
        if (!container) return;

        container.innerHTML = systems.map(system => `
            <div class="system-detail-card">
                <div class="system-header">
                    <h3>${system.name}</h3>
                    <span class="system-status">${system.status}</span>
                </div>
                <div class="system-specs">
                    <div class="spec-group">
                        <h4>Hardware</h4>
                        <div class="spec">CPU: ${system.cpu}</div>
                        <div class="spec">Memory: ${system.memory}</div>
                        <div class="spec">Storage: ${system.storage}</div>
                    </div>
                    <div class="spec-group">
                        <h4>Software</h4>
                        <div class="spec">OS: ${system.os}</div>
                        <div class="spec">Version: ${system.version}</div>
                        <div class="spec">Uptime: ${system.uptime}</div>
                    </div>
                </div>
                <div class="system-metrics">
                    <div class="metric-bar">
                        <label>CPU</label>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${system.cpuUsage}%"></div>
                        </div>
                        <span class="metric-value">${system.cpuUsage}%</span>
                    </div>
                    <div class="metric-bar">
                        <label>Memory</label>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${system.memoryUsage}%"></div>
                        </div>
                        <span class="metric-value">${system.memoryUsage}%</span>
                    </div>
                    <div class="metric-bar">
                        <label>Storage</label>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${system.storageUsage}%"></div>
                        </div>
                        <span class="metric-value">${system.storageUsage}%</span>
                    </div>
                </div>
            </div>
        `).join('');
    }

    updateMatrixVisualization(data) {
        if (!this.charts.matrixVisualization) return;

        this.charts.matrixVisualization.data.datasets[0].data = [
            data.performance,
            data.efficiency,
            data.stability,
            data.security,
            data.intelligence,
            data.adaptability
        ];
        this.charts.matrixVisualization.update();
    }

    updatePortfolioDisplay(data) {
        // Update summary cards
        document.getElementById('total-value').textContent = data.totalValue;
        document.getElementById('total-change').textContent = data.totalChange;
        document.getElementById('total-change').className = `change ${data.changeClass}`;

        // Update chart
        if (this.charts.portfolioPerformance) {
            this.charts.portfolioPerformance.data.labels = data.labels;
            this.charts.portfolioPerformance.data.datasets[0].data = data.values;
            this.charts.portfolioPerformance.update();
        }
    }

    updateAnalyticsCharts(data) {
        if (this.charts.agentPerformance) {
            this.charts.agentPerformance.data.datasets[0].data = data.agentTasks;
            this.charts.agentPerformance.update();
        }

        if (this.charts.systemHealth) {
            this.charts.systemHealth.data.datasets[0].data = data.healthStatus;
            this.charts.systemHealth.update();
        }
    }

    updateIntelligenceDisplay(data) {
        const insightsContainer = document.getElementById('insights-cards');
        if (insightsContainer) {
            insightsContainer.innerHTML = data.insights.map(insight => `
                <div class="insight-card">
                    <div class="insight-header">
                        <span class="insight-icon">${insight.icon}</span>
                        <span class="insight-priority ${insight.priority}">${insight.priority}</span>
                    </div>
                    <h4>${insight.title}</h4>
                    <p>${insight.description}</p>
                    <div class="insight-actions">
                        <button class="btn btn-sm">View Details</button>
                        <button class="btn btn-sm secondary">Dismiss</button>
                    </div>
                </div>
            `).join('');
        }
    }

    updateSecurityDisplay(data) {
        // Update threat level
        const threatLevel = document.querySelector('.threat-level');
        if (threatLevel) {
            threatLevel.textContent = data.threatLevel;
            threatLevel.className = `threat-level ${data.threatLevelClass}`;
        }

        // Update threat count
        const threatCount = document.querySelector('.threat-count');
        if (threatCount) {
            threatCount.textContent = data.threatCount;
        }

        // Update access log
        const accessLog = document.querySelector('.access-log');
        if (accessLog) {
            accessLog.innerHTML = data.accessLog.map(entry => `
                <div class="log-entry">
                    <span class="log-time">${entry.time}</span>
                    <span class="log-action">${entry.action}</span>
                    <span class="log-status ${entry.statusClass}">${entry.status}</span>
                </div>
            `).join('');
        }
    }

    updateTime() {
        const now = new Date();
        const timeElement = document.getElementById('current-time');
        const dateElement = document.getElementById('current-date');

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

    handleAction(action) {
        switch (action) {
            case 'refresh':
                this.refreshAllData();
                break;
            case 'optimize':
                this.runOptimization();
                break;
            case 'backup':
                this.createBackup();
                break;
            case 'shutdown':
                this.initiateShutdown();
                break;
        }
    }

    handleAgentAction(agentId, action) {
        console.log(`Agent ${agentId}: ${action}`);
        // Implement agent control logic
    }

    updateMatrixParameter(param, value) {
        this.matrixData[param] = value;
        // Update matrix visualization based on new parameters
        this.updateMatrixVisualization(this.matrixData);
    }

    handleResize() {
        // Resize charts on window resize
        Object.values(this.charts).forEach(chart => {
            if (chart) chart.resize();
        });
    }

    handleConnectivityChange(isOnline) {
        const statusIndicator = document.querySelector('.status-indicator');
        if (statusIndicator) {
            if (isOnline) {
                statusIndicator.classList.remove('offline');
                statusIndicator.querySelector('.status-text').textContent = 'Online';
            } else {
                statusIndicator.classList.add('offline');
                statusIndicator.querySelector('.status-text').textContent = 'Offline';
            }
        }
    }

    async refreshAllData() {
        await Promise.all([
            this.loadDashboardData(),
            this.loadAgentData(),
            this.loadSystemData(),
            this.loadMatrixData(),
            this.loadPortfolioData(),
            this.loadAnalyticsData(),
            this.loadIntelligenceData(),
            this.loadSecurityData()
        ]);
    }

    async runOptimization() {
        try {
            const response = await fetch('/api/optimize', { method: 'POST' });
            const result = await response.json();
            this.showNotification('Optimization completed', 'success');
        } catch (error) {
            this.showNotification('Optimization failed', 'error');
        }
    }

    async createBackup() {
        try {
            const response = await fetch('/api/backup', { method: 'POST' });
            const result = await response.json();
            this.showNotification('Backup created successfully', 'success');
        } catch (error) {
            this.showNotification('Backup failed', 'error');
        }
    }

    async initiateShutdown() {
        if (confirm('Are you sure you want to shut down the system?')) {
            try {
                const response = await fetch('/api/shutdown', { method: 'POST' });
                this.showNotification('Shutdown initiated', 'warning');
            } catch (error) {
                this.showNotification('Shutdown failed', 'error');
            }
        }
    }

    showNotification(message, type) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;

        // Add to DOM
        document.body.appendChild(notification);

        // Animate in
        setTimeout(() => notification.classList.add('show'), 10);

        // Remove after 3 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => document.body.removeChild(notification), 300);
        }, 3000);
    }

    closeModals() {
        // Close any open modals
        document.querySelectorAll('.modal').forEach(modal => {
            modal.style.display = 'none';
        });
    }

    // Cleanup method
    destroy() {
        // Clear all intervals
        Object.values(this.updateIntervals).forEach(interval => {
            clearInterval(interval);
        });

        // Destroy charts
        Object.values(this.charts).forEach(chart => {
            if (chart) chart.destroy();
        });
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.quantumQuasar = new QuantumQuasarDesktop();
});

// Handle page visibility changes
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        // Pause updates when page is not visible
        Object.values(window.quantumQuasar.updateIntervals).forEach(interval => {
            clearInterval(interval);
        });
    } else {
        // Resume updates when page becomes visible
        window.quantumQuasar.startRealTimeUpdates();
    }
});

// Export for potential use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = QuantumQuasarDesktop;
}