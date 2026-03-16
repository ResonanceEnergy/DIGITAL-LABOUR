// DIGITAL LABOUR Mobile JavaScript
// Touch interactions, PWA features, and real-time updates

class MobileCommandCenter {
    constructor() {
        this.statusIndicator = document.getElementById('connection-status');
        this.statusInterval = null;
        this.pullToRefreshEnabled = false;
        this.init();
    }

    init() {
        this.setupServiceWorker();
        this.setupPullToRefresh();
        this.setupTouchEvents();
        this.startStatusUpdates();
        this.loadInitialData();
    }

    setupServiceWorker() {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/static/sw.js')
                .then(registration => {
                    console.log('Service Worker registered:', registration);
                })
                .catch(error => {
                    console.log('Service Worker registration failed:', error);
                });
        }
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

            if (pullDistance > 80 && window.scrollY === 0) {
                isPulling = true;
                e.preventDefault();
                this.showPullIndicator(pullDistance);
            }
        });

        document.addEventListener('touchend', () => {
            if (isPulling && currentY - startY > 100) {
                this.refreshStatus();
                this.hidePullIndicator();
            }
            isPulling = false;
        });
    }

    showPullIndicator(distance) {
        if (!this.pullIndicator) {
            this.pullIndicator = document.createElement('div');
            this.pullIndicator.className = 'pull-indicator';
            this.pullIndicator.innerHTML = '🔄 Pull to refresh';
            document.body.appendChild(this.pullIndicator);
        }
        this.pullIndicator.style.transform = `translateY(${Math.min(distance - 80, 60)}px)`;
    }

    hidePullIndicator() {
        if (this.pullIndicator) {
            this.pullIndicator.style.transform = 'translateY(-100%)';
            setTimeout(() => {
                if (this.pullIndicator) {
                    document.body.removeChild(this.pullIndicator);
                    this.pullIndicator = null;
                }
            }, 300);
        }
    }

    setupTouchEvents() {
        // Add touch feedback to buttons
        document.querySelectorAll('.command-btn, .refresh-btn').forEach(btn => {
            btn.addEventListener('touchstart', () => {
                btn.classList.add('touch-active');
            });

            btn.addEventListener('touchend', () => {
                btn.classList.remove('touch-active');
            });
        });

        // Prevent zoom on double tap
        let lastTouchEnd = 0;
        document.addEventListener('touchend', (e) => {
            const now = Date.now();
            if (now - lastTouchEnd <= 300) {
                e.preventDefault();
            }
            lastTouchEnd = now;
        }, false);
    }

    startStatusUpdates() {
        this.refreshStatus();
        this.statusInterval = setInterval(() => {
            this.refreshStatus();
        }, 30000); // Update every 30 seconds
    }

    async refreshStatus() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();

            this.updateStatusIndicator(true);
            this.updateServiceStatuses(data);
            this.updateSystemInfo(data.system);

        } catch (error) {
            console.error('Status update failed:', error);
            this.updateStatusIndicator(false);
        }
    }

    updateStatusIndicator(connected) {
        const indicator = this.statusIndicator;
        const dot = indicator.querySelector('.status-dot');
        const text = indicator.querySelector('.status-text');

        if (connected) {
            indicator.className = 'status-indicator status-connected';
            text.textContent = 'Connected';
        } else {
            indicator.className = 'status-indicator status-disconnected';
            text.textContent = 'Disconnected';
        }
    }

    updateServiceStatuses(data) {
        Object.keys(data).forEach(service => {
            if (service === 'system') return;

            const element = document.querySelector(`[data-service="${service}"]`);
            if (element) {
                const statusElement = element.querySelector('.service-status');
                const status = data[service].status;

                statusElement.textContent = status.charAt(0).toUpperCase() + status.slice(1);
                statusElement.className = `service-status ${status}`;
            }
        });
    }

    updateSystemInfo(system) {
        // Update timestamp or other system info if needed
        console.log('System info:', system);
    }

    async executeCommand(command) {
        const btn = event.target;
        btn.classList.add('loading');
        btn.disabled = true;

        try {
            const response = await fetch(`/api/command/${command}`);
            const data = await response.json();

            if (data.status === 'executed') {
                this.showNotification(`✅ ${command.replace('_', ' ').toUpperCase()} executed`, 'success');
                setTimeout(() => this.refreshStatus(), 2000);
            } else {
                this.showNotification(`❌ Command failed: ${data.error}`, 'error');
            }
        } catch (error) {
            this.showNotification(`❌ Network error: ${error.message}`, 'error');
        } finally {
            btn.classList.remove('loading');
            btn.disabled = false;
        }
    }

    async loadLogs() {
        const service = document.getElementById('log-service').value;
        const container = document.getElementById('logs-container');

        container.innerHTML = '<div class="log-entry">Loading logs...</div>';

        try {
            const response = await fetch(`/api/logs/${service}`);
            const data = await response.json();

            container.innerHTML = data.logs.map(log =>
                `<div class="log-entry">${log.trim()}</div>`
            ).join('');

        } catch (error) {
            container.innerHTML = `<div class="log-entry">❌ Failed to load logs: ${error.message}</div>`;
        }
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;

        // Add to page
        document.body.appendChild(notification);

        // Animate in
        setTimeout(() => notification.classList.add('show'), 10);

        // Remove after 3 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                if (notification.parentNode) {
                    document.body.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }

    loadInitialData() {
        this.loadLogs();
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.mobileCC = new MobileCommandCenter();
});

// Global functions for HTML onclick handlers
function refreshStatus() {
    window.mobileCC.refreshStatus();
}

function executeCommand(command) {
    window.mobileCC.executeCommand(command);
}

function loadLogs() {
    window.mobileCC.loadLogs();
}

// PWA install prompt
let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;

    // Show install button if desired
    console.log('PWA install prompt available');
});

// Service worker update handling
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.addEventListener('controllerchange', () => {
        window.location.reload();
    });
}</content>
<parameter name="filePath">C:/Dev/DIGITAL-LABOUR/static/js/mobile.js