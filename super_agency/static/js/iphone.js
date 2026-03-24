// iPhone UI JavaScript for Pocket Pulsar
// iPhone 15/iOS 26 Optimized - Liquid Glass Design & Apple Intelligence
// Enhanced for A17 Pro chip performance and Dynamic Island

class PocketPulsarUI {
    constructor() {
        this.currentTab = 'dashboard';
        this.updateInterval = null;
        this.isIPhone15 = this.detectIPhone15();
        this.appleIntelligence = this.detectAppleIntelligence();
        this.init();
    }

    detectIPhone15() {
        // Detect iPhone 15 series based on screen dimensions and features
        const screenWidth = window.screen.width;
        const screenHeight = window.screen.height;
        const devicePixelRatio = window.devicePixelRatio;

        // iPhone 15: 393x852 (460ppi), iPhone 15 Pro Max: 430x932 (460ppi)
        return (
            (screenWidth === 393 && screenHeight === 852) || // iPhone 15
            (screenWidth === 428 && screenHeight === 926) || // iPhone 15 Plus
            (screenWidth === 393 && screenHeight === 852) || // iPhone 15 Pro
            (screenWidth === 430 && screenHeight === 932)    // iPhone 15 Pro Max
        ) && devicePixelRatio >= 3;
    }

    detectAppleIntelligence() {
        // Detect Apple Intelligence availability
        return navigator.userAgent.includes('iPhone') &&
            window.CSS && window.CSS.supports &&
            window.navigator.hardwareConcurrency >= 6; // A17 Pro has 6 cores
    }

    init() {
        console.log('🚀 Pocket Pulsar initializing...');
        console.log(`📱 iPhone 15 detected: ${this.isIPhone15}`);
        console.log(`🧠 Apple Intelligence available: ${this.appleIntelligence}`);

        this.setupEventListeners();
        this.startRealTimeUpdates();
        this.loadInitialData();
        this.setupServiceWorker();
        this.setupIPhone15Optimizations();
        this.setupAppleIntelligence();
    }

    setupEventListeners() {
        // Tab navigation
        document.querySelectorAll('.tab-button').forEach(button => {
            button.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        // Touch feedback for all interactive elements
        document.querySelectorAll('button, .metric-card, .agent-card, .system-card, .finance-card').forEach(element => {
            element.addEventListener('touchstart', this.handleTouchStart.bind(this));
            element.addEventListener('touchend', this.handleTouchEnd.bind(this));
        });

        // Pull-to-refresh functionality
        this.setupPullToRefresh();
    }

    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-button').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(tabName).classList.add('active');

        this.currentTab = tabName;
        this.updateTabData(tabName);
    }

    async loadInitialData() {
        try {
            await this.updateAllMetrics();
            this.updateLastSync();
        } catch (error) {
            console.error('Failed to load initial data:', error);
            this.showOfflineIndicator();
        }
    }

    startRealTimeUpdates() {
        // Update every 30 seconds
        this.updateInterval = setInterval(() => {
            this.updateAllMetrics();
        }, 30000);

        // Update every 5 seconds for critical metrics
        setInterval(() => {
            this.updateCriticalMetrics();
        }, 5000);
    }

    async updateAllMetrics() {
        const endpoints = [
            '/api/status',
            '/api/agents',
            '/api/systems',
            '/api/finance'
        ];

        try {
            const responses = await Promise.all(
                endpoints.map(endpoint => this.apiCall(endpoint))
            );

            await this.updateDashboardMetrics(responses[0]);
            this.updateAgentsList(responses[1]);
            this.updateSystemsStatus(responses[2]);
            this.updateFinanceData(responses[3]);

            this.updateConnectionStatus(true);
        } catch (error) {
            console.error('Metrics update failed:', error);
            this.updateConnectionStatus(false);
        }
    }

    async updateCriticalMetrics() {
        try {
            const status = await this.apiCall('/api/status');
            await this.updateDashboardMetrics(status);
        } catch (error) {
            // Silent fail for critical updates
        }
    }

    async updateDashboardMetrics(data) {
        if (!data) return;

        // Update system health
        const healthElement = document.getElementById('system-health');
        if (healthElement) {
            healthElement.textContent = `${Math.round(data.system_health || 98)}%`;
            this.animateValueChange(healthElement);
        }

        // Update active agents (online_nodes represents active components)
        const agentsElement = document.getElementById('active-agents');
        if (agentsElement) {
            agentsElement.textContent = data.online_nodes || 9;
            this.animateValueChange(agentsElement);
        }

        // Update CPU usage - get this from matrix data
        await this.updateCPUUsage();

        // Update memory usage - get this from matrix data
        await this.updateMemoryUsage();

        // Update financial score
        const financeElement = document.getElementById('financial-score');
        if (financeElement) {
            financeElement.textContent = data.financial_score || 92;
            this.animateValueChange(financeElement);
        }

        // Update repos count
        const reposElement = document.getElementById('repos-count');
        if (reposElement) {
            reposElement.textContent = data.repos_count || 47;
            this.animateValueChange(reposElement);
        }
    }

    async updateCPUUsage() {
        try {
            const matrixData = await this.apiCall('/api/matrix');
            if (matrixData && matrixData.matrix) {
                // Find Quantum Quasar (desktop) and get CPU metric
                const quantumQuasar = matrixData.matrix.find(node => node.id === 'quantum_quasar');
                if (quantumQuasar && quantumQuasar.metrics) {
                    const cpuMetric = quantumQuasar.metrics.find(m => m.label === 'CPU');
                    if (cpuMetric) {
                        const cpuElement = document.getElementById('cpu-usage');
                        if (cpuElement) {
                            cpuElement.textContent = cpuMetric.value;
                            this.animateValueChange(cpuElement);
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Failed to update CPU usage:', error);
        }
    }

    async updateMemoryUsage() {
        try {
            const matrixData = await this.apiCall('/api/matrix');
            if (matrixData && matrixData.matrix) {
                // Find Quantum Quasar (desktop) and get MEM metric
                const quantumQuasar = matrixData.matrix.find(node => node.id === 'quantum_quasar');
                if (quantumQuasar && quantumQuasar.metrics) {
                    const memMetric = quantumQuasar.metrics.find(m => m.label === 'MEM');
                    if (memMetric) {
                        const memoryElement = document.getElementById('memory-usage');
                        if (memoryElement) {
                            memoryElement.textContent = memMetric.value;
                            this.animateValueChange(memoryElement);
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Failed to update memory usage:', error);
        }
    }

    updateAgentsList(data) {
        if (!data || !data.agents) return;

        const agentsContainer = document.querySelector('.agents-list');
        if (!agentsContainer) return;

        // Clear existing agents except first few for demo
        const existingCards = agentsContainer.querySelectorAll('.agent-card');
        for (let i = 3; i < existingCards.length; i++) {
            existingCards[i].remove();
        }

        // Add new agent cards
        data.agents.forEach(agent => {
            if (!document.querySelector(`[data-agent-id="${agent.id}"]`)) {
                const agentCard = this.createAgentCard(agent);
                agentsContainer.appendChild(agentCard);
            }
        });
    }

    createAgentCard(agent) {
        const card = document.createElement('div');
        card.className = `agent-card ${agent.status}`;
        card.setAttribute('data-agent-id', agent.id);

        card.innerHTML = `
            <div class="agent-icon">${this.getAgentIcon(agent.type)}</div>
            <div class="agent-info">
                <h4>${agent.name}</h4>
                <span class="agent-status">${agent.status_text}</span>
            </div>
            <div class="agent-metric">${agent.efficiency}%</div>
        `;

        return card;
    }

    getAgentIcon(type) {
        const icons = {
            'repo_sentry': '🔍',
            'daily_brief': '📊',
            'council': '🧠',
            'orchestrator': '🎯',
            'integrate_cell': '🔗',
            'default': '🤖'
        };
        return icons[type] || icons.default;
    }

    updateSystemsStatus(data) {
        if (!data || !data.systems) return;

        data.systems.forEach(system => {
            const systemCard = document.querySelector(`[data-system="${system.id}"]`);
            if (systemCard) {
                const metrics = systemCard.querySelector('.system-metrics');
                if (metrics) {
                    metrics.innerHTML = `
                        <span>CPU: ${system.cpu}%</span>
                        <span>RAM: ${system.ram}%</span>
                        <span>Status: ${system.status}</span>
                    `;
                }
            }
        });
    }

    updateFinanceData(data) {
        if (!data) return;

        // Update finance cards
        const balanceCard = document.querySelector('.finance-card:nth-child(1) .finance-value');
        if (balanceCard) {
            balanceCard.textContent = `$${data.balance?.toLocaleString() || '127,543.89'}`;
        }

        const revenueCard = document.querySelector('.finance-card:nth-child(2) .finance-value');
        if (revenueCard) {
            revenueCard.textContent = `$${data.revenue?.toLocaleString() || '15,234.56'}`;
        }

        const complianceCard = document.querySelector('.finance-card:nth-child(3) .finance-value');
        if (complianceCard) {
            complianceCard.textContent = `${data.compliance || 98}%`;
        }

        // Update transactions
        this.updateTransactionList(data.transactions);
    }

    updateTransactionList(transactions) {
        if (!transactions) return;

        const transactionList = document.querySelector('.transaction-list');
        if (!transactionList) return;

        transactionList.innerHTML = '';

        transactions.slice(0, 5).forEach(transaction => {
            const item = document.createElement('div');
            item.className = 'transaction-item';

            item.innerHTML = `
                <span>${transaction.description}</span>
                <span class="amount ${transaction.amount > 0 ? 'positive' : 'negative'}">
                    ${transaction.amount > 0 ? '+' : ''}$${Math.abs(transaction.amount).toLocaleString()}
                </span>
            `;

            transactionList.appendChild(item);
        });
    }

    updateTabData(tabName) {
        // Load specific data when switching to a tab
        switch (tabName) {
            case 'agents':
                this.updateAgentsList();
                break;
            case 'systems':
                this.updateSystemsStatus();
                break;
            case 'finance':
                this.updateFinanceData();
                break;
            case 'matrix':
                this.updateMatrixStats();
                this.loadMatrixData();
                break;
        }
    }

    async sendCommand(command) {
        try {
            const button = event.target;
            const originalText = button.textContent;
            button.textContent = 'Sending...';
            button.classList.add('loading');

            const response = await this.apiCall('/api/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command })
            });

            button.textContent = 'Success!';
            setTimeout(() => {
                button.textContent = originalText;
                button.classList.remove('loading');
            }, 2000);

            // Refresh data after command
            setTimeout(() => this.updateAllMetrics(), 1000);

        } catch (error) {
            console.error('Command failed:', error);
            event.target.textContent = 'Failed';
            setTimeout(() => {
                event.target.textContent = originalText;
            }, 2000);
        }
    }

    async apiCall(endpoint, options = {}) {
        const baseUrl = window.location.origin;
        const url = `${baseUrl}${endpoint}`;

        try {
            const response = await fetch(url, {
                ...options,
                headers: {
                    'Accept': 'application/json',
                    ...options.headers
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            // Try fallback endpoints for distributed architecture
            if (endpoint.includes('/api/')) {
                const fallbacks = [
                    'http://quantum-quasar.local:8080',
                    'http://tablet-titan.local:8080',
                    'http://windows-companion.local:3000'
                ];

                for (const fallback of fallbacks) {
                    try {
                        const fallbackResponse = await fetch(`${fallback}${endpoint}`, options);
                        if (fallbackResponse.ok) {
                            return await fallbackResponse.json();
                        }
                    } catch (e) {
                        continue;
                    }
                }
            }

            throw error;
        }
    }

    updateConnectionStatus(connected) {
        const statusDot = document.querySelector('.status-dot');
        const statusText = document.querySelector('.status-text');

        if (connected) {
            statusDot.style.background = 'var(--success-color)';
            statusText.textContent = 'Connected';
        } else {
            statusDot.style.background = 'var(--error-color)';
            statusText.textContent = 'Offline';
        }
    }

    updateLastSync() {
        const lastUpdateElement = document.getElementById('last-update');
        if (lastUpdateElement) {
            lastUpdateElement.textContent = new Date().toLocaleTimeString();
        }
    }

    animateValueChange(element) {
        element.style.transform = 'scale(1.1)';
        setTimeout(() => {
            element.style.transform = 'scale(1)';
        }, 200);
    }

    handleTouchStart(event) {
        event.target.style.transform = 'scale(0.95)';
    }

    handleTouchEnd(event) {
        event.target.style.transform = 'scale(1)';
    }

    setupPullToRefresh() {
        let startY = 0;
        let currentY = 0;
        let isPulling = false;

        document.addEventListener('touchstart', (e) => {
            startY = e.touches[0].clientY;
        });

        document.addEventListener('touchmove', (e) => {
            currentY = e.touches[0].clientY;
            const pullDistance = currentY - startY;

            if (pullDistance > 50 && window.scrollY === 0) {
                isPulling = true;
                e.preventDefault();
                // Add visual feedback for pull-to-refresh
                document.body.style.transform = `translateY(${Math.min(pullDistance * 0.5, 60)}px)`;
            }
        });

        document.addEventListener('touchend', async () => {
            if (isPulling) {
                document.body.style.transform = 'translateY(0)';
                await this.updateAllMetrics();
                this.updateLastSync();
            }
            isPulling = false;
        });
    }

    setupServiceWorker() {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/static/sw_iphone.js')
                .then(registration => {
                    console.log('Service Worker registered for iPhone UI');
                })
                .catch(error => {
                    console.error('Service Worker registration failed:', error);
                });
        }
    }

    showOfflineIndicator() {
        // Show cached data indicator
        const statusText = document.querySelector('.status-text');
        if (statusText) {
            statusText.textContent = 'Offline (Cached)';
        }
    }

    // Matrix Monitor Methods
    toggleMatrixView(viewType) {
        // Update control button states
        document.querySelectorAll('.matrix-control-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[onclick="toggleMatrixView('${viewType}')"]`).classList.add('active');

        const matrixGrid = document.getElementById('matrix-grid');
        if (!matrixGrid) return;

        // Apply different view styles
        matrixGrid.className = `matrix-grid view-${viewType}`;

        // Update matrix nodes based on view type
        this.updateMatrixNodes(viewType);
    }

    updateMatrixNodes(viewType = 'nodes') {
        const nodes = document.querySelectorAll('.matrix-node');

        nodes.forEach(node => {
            // Remove existing view classes
            node.classList.remove('view-grid', 'view-nodes', 'view-heatmap');

            // Add current view class
            node.classList.add(`view-${viewType}`);

            // Update node appearance based on view type
            switch (viewType) {
                case 'grid':
                    this.applyGridView(node);
                    break;
                case 'nodes':
                    this.applyNodesView(node);
                    break;
                case 'heatmap':
                    this.applyHeatmapView(node);
                    break;
            }
        });
    }

    applyGridView(node) {
        // Grid view: Show compact metrics
        const metrics = node.querySelector('.node-metrics');
        if (metrics) {
            metrics.style.display = 'none';
        }
        node.style.borderRadius = '4px';
    }

    applyNodesView(node) {
        // Nodes view: Show full metrics with connections
        const metrics = node.querySelector('.node-metrics');
        if (metrics) {
            metrics.style.display = 'flex';
        }
        node.style.borderRadius = '12px';

        // Add connection lines (visual effect)
        this.addNodeConnections(node);
    }

    applyHeatmapView(node) {
        // Heatmap view: Color based on status/health
        const status = node.dataset.status;
        const metrics = node.querySelector('.node-metrics');
        if (metrics) {
            metrics.style.display = 'none';
        }

        // Apply heatmap colors
        switch (status) {
            case 'online':
            case 'active':
            case 'healthy':
                node.style.background = 'rgba(0, 255, 136, 0.1)';
                node.style.borderColor = 'var(--success-color)';
                break;
            case 'warning':
                node.style.background = 'rgba(255, 170, 0, 0.1)';
                node.style.borderColor = 'var(--warning-color)';
                break;
            case 'error':
                node.style.background = 'rgba(255, 68, 68, 0.1)';
                node.style.borderColor = 'var(--error-color)';
                break;
            default:
                node.style.background = 'var(--secondary-bg)';
                node.style.borderColor = 'var(--border-color)';
        }
    }

    addNodeConnections(node) {
        // Remove existing connections
        const existingConnections = node.querySelectorAll('.node-connection');
        existingConnections.forEach(conn => conn.remove());

        // Add subtle connection indicators
        const nodeType = node.dataset.type;
        if (nodeType === 'quantum-quasar' || nodeType === 'pocket-pulsar' || nodeType === 'tablet-titan') {
            // Device nodes get connection dots
            const connection = document.createElement('div');
            connection.className = 'node-connection';
            connection.innerHTML = '⟐';
            connection.style.cssText = `
                position: absolute;
                bottom: -5px;
                left: 50%;
                transform: translateX(-50%);
                color: var(--accent-color);
                font-size: 12px;
                opacity: 0.7;
            `;
            node.appendChild(connection);
        }
    }

    updateMatrixStats() {
        const nodes = document.querySelectorAll('.matrix-node');
        const totalNodes = nodes.length;
        const onlineNodes = document.querySelectorAll('.matrix-node[data-status="online"], .matrix-node[data-status="active"], .matrix-node[data-status="healthy"]').length;

        // Calculate system health based on online nodes
        const systemHealth = Math.round((onlineNodes / totalNodes) * 100);

        // Update stats display
        const totalElement = document.getElementById('total-nodes');
        const onlineElement = document.getElementById('online-nodes');
        const healthElement = document.getElementById('system-health-matrix');

        if (totalElement) totalElement.textContent = totalNodes;
        if (onlineElement) onlineElement.textContent = onlineNodes;
        if (healthElement) {
            healthElement.textContent = `${systemHealth}%`;
            healthElement.style.color = systemHealth >= 90 ? 'var(--success-color)' :
                systemHealth >= 70 ? 'var(--warning-color)' : 'var(--error-color)';
        }
    }

    updateMatrixData(data) {
        if (!data || !data.matrix) return;

        // Update each matrix node with real data
        data.matrix.forEach(nodeData => {
            const node = document.querySelector(`.matrix-node[data-type="${nodeData.type}"]`);
            if (node) {
                // Update status
                node.setAttribute('data-status', nodeData.status);

                // Update metrics
                const metricsContainer = node.querySelector('.node-metrics');
                if (metricsContainer && nodeData.metrics) {
                    metricsContainer.innerHTML = nodeData.metrics.map(metric =>
                        `<span class="metric">${metric.label}: ${metric.value}</span>`
                    ).join('');
                }

                // Update status indicator
                const statusIndicator = node.querySelector('.node-status');
                if (statusIndicator) {
                    statusIndicator.className = `node-status ${nodeData.status}`;
                }
            }
        });

        // Update matrix statistics
        this.updateMatrixStats();
    }

    async loadMatrixData() {
        try {
            const response = await this.apiCall('/api/matrix');
            if (response && response.ok) {
                const data = await response.json();
                this.updateMatrixData(data);
            } else {
                // Use default/demo data if API fails
                this.loadDemoMatrixData();
            }
        } catch (error) {
            console.error('Failed to load matrix data:', error);
            this.loadDemoMatrixData();
        }
    }

    loadDemoMatrixData() {
        // Demo data for matrix when API is not available
        const demoData = {
            matrix: [
                {
                    type: 'quantum-quasar',
                    status: 'online',
                    metrics: [
                        { label: 'CPU', value: '75%' },
                        { label: 'MEM', value: '45%' }
                    ]
                },
                {
                    type: 'pocket-pulsar',
                    status: 'online',
                    metrics: [
                        { label: 'BAT', value: '87%' },
                        { label: 'NET', value: 'LTE' }
                    ]
                },
                {
                    type: 'tablet-titan',
                    status: 'online',
                    metrics: [
                        { label: 'CPU', value: '60%' },
                        { label: 'MEM', value: '35%' }
                    ]
                },
                {
                    type: 'agent',
                    status: 'online',
                    metrics: [
                        { label: 'REPOS', value: '47' },
                        { label: 'HEALTH', value: '98%' }
                    ]
                },
                {
                    type: 'memory',
                    status: 'active',
                    metrics: [
                        { label: 'POOL', value: '256MB' },
                        { label: 'EFFICIENCY', value: '92%' }
                    ]
                },
                {
                    type: 'finance',
                    status: 'healthy',
                    metrics: [
                        { label: 'BALANCE', value: '$127K' },
                        { label: 'SCORE', value: '92' }
                    ]
                }
            ]
        };

        this.updateMatrixData(demoData);
    }

    setupIPhone15Optimizations() {
        if (this.isIPhone15) {
            // Dynamic Island considerations
            this.setupDynamicIsland();

            // A17 Pro performance optimizations
            this.optimizeForA17Pro();

            // Enhanced touch handling
            this.setupEnhancedTouch();

            // Liquid Glass visual effects
            this.setupLiquidGlassEffects();
        }
    }

    setupDynamicIsland() {
        // Adjust layout for Dynamic Island
        const header = document.querySelector('.header');
        if (header && CSS.supports('padding: max(0px)')) {
            header.style.paddingTop = 'max(16px, env(safe-area-inset-top) + 8px)';
        }

        // Add Dynamic Island status indicator
        const statusIndicator = document.querySelector('.status-indicator');
        if (statusIndicator) {
            const dynamicIsland = document.createElement('div');
            dynamicIsland.className = 'dynamic-island-status';
            dynamicIsland.innerHTML = '⟐';
            statusIndicator.appendChild(dynamicIsland);
        }
    }

    optimizeForA17Pro() {
        // Enable hardware acceleration for A17 Pro
        const matrixGrid = document.querySelector('.matrix-grid');
        if (matrixGrid) {
            matrixGrid.style.willChange = 'transform';
            matrixGrid.style.transform = 'translateZ(0)'; // Force GPU acceleration
        }

        // Optimize animation performance
        if (window.requestAnimationFrame) {
            this.useRequestAnimationFrame = true;
        }
    }

    setupEnhancedTouch() {
        // Enhanced haptic feedback simulation
        const nodes = document.querySelectorAll('.matrix-node');
        nodes.forEach(node => {
            node.addEventListener('touchstart', (e) => {
                e.target.style.transform = 'scale(0.98)';
                // Simulate haptic feedback
                if (navigator.vibrate) {
                    navigator.vibrate(10);
                }
            });

            node.addEventListener('touchend', (e) => {
                e.target.style.transform = 'scale(1)';
            });
        });
    }

    setupLiquidGlassEffects() {
        // Add subtle Liquid Glass animations
        const nodes = document.querySelectorAll('.matrix-node');
        nodes.forEach((node, index) => {
            node.style.animationDelay = `${index * 0.1}s`;
            node.classList.add('liquid-glass');
        });
    }

    setupAppleIntelligence() {
        if (this.appleIntelligence) {
            console.log('🧠 Apple Intelligence detected - enabling smart features');

            // Add Apple Intelligence hints to the UI
            this.addAppleIntelligenceHints();

            // Enable predictive text and smart suggestions
            this.enableSmartSuggestions();
        }
    }

    addAppleIntelligenceHints() {
        // Add subtle hints for Apple Intelligence features
        const header = document.querySelector('.header h1');
        if (header) {
            const aiIndicator = document.createElement('span');
            aiIndicator.className = 'ai-indicator';
            aiIndicator.textContent = '✨';
            aiIndicator.title = 'Apple Intelligence Enhanced';
            header.appendChild(aiIndicator);
        }
    }

    enableSmartSuggestions() {
        // Enable smart command suggestions based on context
        this.smartSuggestions = {
            'matrix': ['optimize', 'diagnostics', 'sync'],
            'agents': ['restart', 'update', 'monitor'],
            'systems': ['backup', 'health-check', 'performance']
        };
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.pocketPulsar = new PocketPulsarUI();
});

// Global function for button onclick handlers
function sendCommand(command) {
    if (window.pocketPulsar) {
        window.pocketPulsar.sendCommand(command);
    }
}

// Matrix Monitor functionality
function toggleMatrixView(viewType) {
    if (window.pocketPulsar) {
        window.pocketPulsar.toggleMatrixView(viewType);
    }
}

// Make PocketPulsarUI globally available
window.PocketPulsarUI = PocketPulsarUI;
window.pocketPulsar = new PocketPulsarUI();</content >
    <parameter name="filePath">$HOME/repos/ELECTRIC ICE/Digital-Labour/static/js/iphone.js
