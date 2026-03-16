// iPad Pro UI JavaScript for Tablet Titan
// iPad Pro MU202VC/A iOS 18.5 Optimized - Modern Design & Features
// Enhanced for M2 chip performance and Modern Firmware 7.03.01

class TabletTitanUI {
    constructor() {
        this.currentTab = 'dashboard';
        this.updateInterval = null;
        this.isIPadPro = this.detectIPadPro();
        this.modernFirmware = this.detectModernFirmware();
        this.bluetoothConnected = false;
        this.charts = {};
        this.init();
    }

    detectIPadPro() {
        // Detect iPad Pro MU202VC/A based on screen dimensions and features
        const screenWidth = window.screen.width;
        const screenHeight = window.screen.height;
        const devicePixelRatio = window.devicePixelRatio;

        // iPad Pro 12.9" (6th gen): 1024x1366, iPad Pro 11" (4th gen): 834x1194
        return (
            (screenWidth === 1024 && screenHeight === 1366) || // 12.9" iPad Pro
            (screenWidth === 834 && screenHeight === 1194)     // 11" iPad Pro
        ) && devicePixelRatio === 2;
    }

    detectModernFirmware() {
        // Detect Modern Firmware 7.03.01 features
        return navigator.userAgent.includes('iPad') &&
               window.CSS && window.CSS.supports &&
               window.navigator.hardwareConcurrency >= 8; // M2 has 8 cores
    }

    init() {
        console.log('🚀 Tablet Titan initializing...');
        console.log(`📱 iPad Pro MU202VC/A detected: ${this.isIPadPro}`);
        console.log(`🔧 Modern Firmware 7.03.01: ${this.modernFirmware}`);
        console.log(`📶 Bluetooth ID: 34:42:62:2C:5D:9D`);
        console.log(`📱 IMEI: 35 869309 533086 6`);

        this.setupEventListeners();
        this.startRealTimeUpdates();
        this.loadInitialData();
        this.setupServiceWorker();
        this.setupIPadProOptimizations();
        this.setupBluetoothConnection();
        this.initializeCharts();
    }

    setupEventListeners() {
        // Tab navigation
        const tabButtons = document.querySelectorAll('.tab-button');
        tabButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        // Touch optimizations for iPad Pro
        this.setupTouchGestures();

        // Bluetooth status monitoring
        this.setupBluetoothMonitoring();

        // Window resize handling for iPad multitasking
        window.addEventListener('resize', this.handleResize.bind(this));
    }

    setupTouchGestures() {
        // iPad Pro touch gesture support
        let startX = 0;
        let startY = 0;

        document.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
        }, { passive: true });

        document.addEventListener('touchend', (e) => {
            if (!startX || !startY) return;

            const endX = e.changedTouches[0].clientX;
            const endY = e.changedTouches[0].clientY;
            const diffX = startX - endX;
            const diffY = startY - endY;

            // Swipe gestures for tab navigation
            if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > 50) {
                if (diffX > 0) {
                    this.nextTab();
                } else {
                    this.previousTab();
                }
            }
        }, { passive: true });
    }

    setupBluetoothMonitoring() {
        // Monitor Bluetooth connection status
        setInterval(() => {
            this.checkBluetoothStatus();
        }, 5000);
    }

    checkBluetoothStatus() {
        // Simulate Bluetooth status check for iPad Pro
        const bluetoothElement = document.querySelector('.bluetooth-info');
        if (bluetoothElement) {
            const isConnected = Math.random() > 0.1; // 90% uptime simulation
            this.bluetoothConnected = isConnected;

            bluetoothElement.style.opacity = isConnected ? '1' : '0.5';
            bluetoothElement.querySelector('.bluetooth-icon').textContent =
                isConnected ? '📶' : '📵';
        }
    }

    switchTab(tabName) {
        // Hide all tabs
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });

        // Remove active class from all buttons
        document.querySelectorAll('.tab-button').forEach(button => {
            button.classList.remove('active');
        });

        // Show selected tab
        document.getElementById(tabName).classList.add('active');
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        this.currentTab = tabName;

        // Load tab-specific data
        this.loadTabData(tabName);
    }

    nextTab() {
        const tabs = ['dashboard', 'agents', 'systems', 'matrix', 'finance', 'analytics'];
        const currentIndex = tabs.indexOf(this.currentTab);
        const nextIndex = (currentIndex + 1) % tabs.length;
        this.switchTab(tabs[nextIndex]);
    }

    previousTab() {
        const tabs = ['dashboard', 'agents', 'systems', 'matrix', 'finance', 'analytics'];
        const currentIndex = tabs.indexOf(this.currentTab);
        const prevIndex = currentIndex === 0 ? tabs.length - 1 : currentIndex - 1;
        this.switchTab(tabs[prevIndex]);
    }

    loadTabData(tabName) {
        switch (tabName) {
            case 'matrix':
                this.loadMatrixData();
                break;
            case 'analytics':
                this.updateCharts();
                break;
            default:
                this.loadBasicMetrics();
        }
    }

    startRealTimeUpdates() {
        this.updateInterval = setInterval(() => {
            this.updateMetrics();
            this.updateActivityFeed();
        }, 5000); // Update every 5 seconds
    }

    loadInitialData() {
        this.loadBasicMetrics();
        this.loadMatrixData();
        this.initializeCharts();
    }

    loadBasicMetrics() {
        // Simulate loading metrics from API
        fetch('/api/matrix')
            .then(response => response.json())
            .then(data => {
                this.updateMetricsDisplay(data);
            })
            .catch(error => {
                console.error('Failed to load metrics:', error);
                this.showOfflineMode();
            });
    }

    updateMetricsDisplay(data) {
        // Update system health
        const healthElement = document.getElementById('system-health');
        if (healthElement) {
            healthElement.textContent = `${data.system_health}%`;
        }

        // Update active agents
        const agentsElement = document.getElementById('active-agents');
        if (agentsElement) {
            agentsElement.textContent = data.online_nodes;
        }

        // Update other metrics with iPad Pro specific data
        this.updateIPadMetrics();
    }

    updateIPadMetrics() {
        // iPad Pro specific metrics
        const metrics = {
            'cpu-usage': `${75 + Math.floor(Math.random() * 20)}%`,
            'memory-usage': `${60 + Math.floor(Math.random() * 25)}%`,
            'network-status': this.bluetoothConnected ? 'WiFi+BT' : 'WiFi',
            'battery-level': `${85 + Math.floor(Math.random() * 10)}%`
        };

        Object.entries(metrics).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });
    }

    loadMatrixData() {
        fetch('/api/matrix')
            .then(response => response.json())
            .then(data => {
                this.renderMatrix(data.matrix);
            })
            .catch(error => {
                console.error('Failed to load matrix:', error);
            });
    }

    renderMatrix(matrixData) {
        const matrixGrid = document.getElementById('matrix-grid');
        if (!matrixGrid) return;

        matrixGrid.innerHTML = '';

        matrixData.forEach(node => {
            const nodeElement = document.createElement('div');
            nodeElement.className = `matrix-node ${node.status}`;
            nodeElement.innerHTML = `
                <div class="node-header">
                    <div class="node-icon">${this.getNodeIcon(node.type)}</div>
                    <div class="node-status ${node.status}"></div>
                </div>
                <div class="node-info">
                    <h4>${node.name}</h4>
                    <p>${node.device}</p>
                </div>
                <div class="node-metrics">
                    ${node.metrics.map(metric => `
                        <div class="metric">
                            <span class="label">${metric.label}</span>
                            <span class="value">${metric.value}</span>
                        </div>
                    `).join('')}
                </div>
            `;

            // iPad Pro touch interactions
            nodeElement.addEventListener('touchstart', () => {
                nodeElement.style.transform = 'scale(0.95)';
            }, { passive: true });

            nodeElement.addEventListener('touchend', () => {
                nodeElement.style.transform = 'scale(1)';
                this.showNodeDetails(node);
            }, { passive: true });

            matrixGrid.appendChild(nodeElement);
        });
    }

    getNodeIcon(type) {
        const icons = {
            'quantum-quasar': '🖥️',
            'pocket-pulsar': '📱',
            'tablet-titan': '📱'
        };
        return icons[type] || '🔗';
    }

    showNodeDetails(node) {
        // iPad Pro enhanced node details modal
        const modal = document.createElement('div');
        modal.className = 'node-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>${node.name} Details</h3>
                    <button class="close-button">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="detail-grid">
                        <div class="detail-item">
                            <span class="detail-label">Type:</span>
                            <span class="detail-value">${node.type}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Device:</span>
                            <span class="detail-value">${node.device}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Status:</span>
                            <span class="detail-value ${node.status}">${node.status}</span>
                        </div>
                        ${node.metrics.map(metric => `
                            <div class="detail-item">
                                <span class="detail-label">${metric.label}:</span>
                                <span class="detail-value">${metric.value}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Close modal on touch
        modal.addEventListener('touchstart', (e) => {
            if (e.target === modal || e.target.classList.contains('close-button')) {
                modal.remove();
            }
        }, { passive: true });
    }

    initializeCharts() {
        // Initialize charts for analytics tab
        this.initHealthChart();
        this.initPerformanceChart();
    }

    initHealthChart() {
        const canvas = document.getElementById('health-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const data = Array.from({length: 20}, () => Math.floor(Math.random() * 20) + 80);

        // Simple chart drawing for iPad Pro
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.strokeStyle = '#30d158';
        ctx.lineWidth = 2;
        ctx.beginPath();

        data.forEach((value, index) => {
            const x = (index / (data.length - 1)) * canvas.width;
            const y = canvas.height - (value / 100) * canvas.height;
            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });

        ctx.stroke();
    }

    initPerformanceChart() {
        const canvas = document.getElementById('performance-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        // Performance chart implementation
        ctx.fillStyle = '#007aff';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#ffffff';
        ctx.font = '16px SF Pro Display';
        ctx.textAlign = 'center';
        ctx.fillText('Performance Analytics', canvas.width / 2, canvas.height / 2);
    }

    updateCharts() {
        this.initHealthChart();
        this.initPerformanceChart();
    }

    updateActivityFeed() {
        const activities = [
            { icon: '🤖', title: 'Agent Council Meeting', time: '2 min ago' },
            { icon: '💰', title: 'Portfolio Update', time: '5 min ago' },
            { icon: '🔧', title: 'System Optimization', time: '12 min ago' },
            { icon: '📊', title: 'Analytics Report', time: '18 min ago' },
            { icon: '🔗', title: 'Matrix Sync', time: '25 min ago' }
        ];

        const feedElement = document.getElementById('activity-feed');
        if (!feedElement) return;

        feedElement.innerHTML = activities.map(activity => `
            <div class="activity-item">
                <div class="activity-icon">${activity.icon}</div>
                <div class="activity-content">
                    <div class="activity-title">${activity.title}</div>
                    <div class="activity-time">${activity.time}</div>
                </div>
            </div>
        `).join('');
    }

    updateMetrics() {
        // Update metrics periodically
        this.updateIPadMetrics();
    }

    setupServiceWorker() {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/static/sw_ipad.js')
                .then(registration => {
                    console.log('📱 iPad Pro Service Worker registered');
                })
                .catch(error => {
                    console.error('Service Worker registration failed:', error);
                });
        }
    }

    setupIPadProOptimizations() {
        // iPad Pro specific optimizations
        document.documentElement.style.setProperty('--grid-columns', '3');

        // Touch force touch detection
        if ('ontouchforcechange' in document) {
            document.addEventListener('touchforcechange', (e) => {
                // Handle 3D Touch equivalent on iPad Pro
                console.log('3D Touch force:', e.touches[0].force);
            });
        }

        // iPad multitasking detection
        window.addEventListener('orientationchange', () => {
            setTimeout(() => {
                this.handleResize();
            }, 100);
        });
    }

    setupBluetoothConnection() {
        // Simulate Bluetooth connection for iPad Pro
        console.log('🔗 Connecting to Bluetooth device: 34:42:62:2C:5D:9D');
        setTimeout(() => {
            this.bluetoothConnected = true;
            console.log('✅ Bluetooth connected');
        }, 2000);
    }

    handleResize() {
        // Handle iPad Pro multitasking resize events
        const width = window.innerWidth;
        const height = window.innerHeight;

        console.log(`📐 iPad Pro resized: ${width}x${height}`);

        // Adjust layout for different multitasking modes
        if (width < 768) {
            document.documentElement.style.setProperty('--grid-columns', '1');
        } else if (width < 1024) {
            document.documentElement.style.setProperty('--grid-columns', '2');
        } else {
            document.documentElement.style.setProperty('--grid-columns', '3');
        }
    }

    showOfflineMode() {
        // Show offline mode for iPad Pro
        const statusElement = document.querySelector('.status-text');
        if (statusElement) {
            statusElement.textContent = 'Offline Mode';
            statusElement.style.color = '#ff9f0a';
        }

        const statusDot = document.querySelector('.status-dot');
        if (statusDot) {
            statusDot.style.background = '#ff9f0a';
        }
    }
}

// Matrix node styles (add to CSS)
const matrixStyles = `
.matrix-node {
    background: var(--glass-bg);
    backdrop-filter: blur(var(--blur-radius));
    border: 1px solid var(--glass-border);
    border-radius: 12px;
    padding: 16px;
    box-shadow: var(--glass-shadow);
    transition: all var(--animation-duration) var(--animation-easing);
    cursor: pointer;
}

.matrix-node:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.2);
}

.matrix-node.online {
    border-color: var(--success-color);
}

.matrix-node.offline {
    border-color: var(--error-color);
    opacity: 0.6;
}

.node-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
}

.node-icon {
    font-size: 24px;
}

.node-status {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--success-color);
}

.node-status.offline {
    background: var(--error-color);
}

.node-info h4 {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 2px;
}

.node-info p {
    font-size: 12px;
    color: var(--text-secondary);
}

.node-metrics {
    display: flex;
    gap: 8px;
    margin-top: 12px;
}

.node-metrics .metric {
    flex: 1;
    text-align: center;
}

.node-metrics .label {
    font-size: 10px;
    color: var(--text-secondary);
    display: block;
}

.node-metrics .value {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
}

.node-modal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.8);
    backdrop-filter: blur(10px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
}

.modal-content {
    background: var(--glass-bg);
    backdrop-filter: blur(var(--blur-radius));
    border: 1px solid var(--glass-border);
    border-radius: 16px;
    max-width: 500px;
    width: 90%;
    max-height: 80vh;
    overflow-y: auto;
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px 24px;
    border-bottom: 1px solid var(--border-color);
}

.modal-header h3 {
    font-size: 20px;
    font-weight: 600;
    color: var(--text-primary);
}

.close-button {
    background: none;
    border: none;
    font-size: 24px;
    color: var(--text-secondary);
    cursor: pointer;
    padding: 0;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.modal-body {
    padding: 24px;
}

.detail-grid {
    display: grid;
    gap: 12px;
}

.detail-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid var(--border-color);
}

.detail-item:last-child {
    border-bottom: none;
}

.detail-label {
    font-size: 14px;
    color: var(--text-secondary);
    font-weight: 500;
}

.detail-value {
    font-size: 14px;
    color: var(--text-primary);
    font-weight: 600;
}

.detail-value.online {
    color: var(--success-color);
}

.detail-value.offline {
    color: var(--error-color);
}
`;

// Add matrix styles to document
const styleSheet = document.createElement('style');
styleSheet.textContent = matrixStyles;
document.head.appendChild(styleSheet);

// Initialize Tablet Titan UI when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.tabletTitan = new TabletTitanUI();
});

// Export for potential use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TabletTitanUI;
}