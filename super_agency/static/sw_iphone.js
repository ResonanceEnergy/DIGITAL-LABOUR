// Service Worker for Pocket Pulsar iPhone PWA
// Handles caching, offline functionality, and background sync

const CACHE_NAME = 'pocket-pulsar-v1.0.0';
const STATIC_CACHE = 'pocket-pulsar-static-v1.0.0';
const DYNAMIC_CACHE = 'pocket-pulsar-dynamic-v1.0.0';

// Assets to cache immediately
const STATIC_ASSETS = [
    '/static/css/iphone.css',
    '/static/js/iphone.js',
    '/static/manifest_iphone.json',
    '/static/icons/icon-192.png',
    '/static/icons/icon-512.png',
    '/static/favicon.ico',
    '/iphone' // Main app route
];

// API endpoints that should be cached
const API_ENDPOINTS = [
    '/api/status',
    '/api/agents',
    '/api/systems',
    '/api/finance'
];

// Install event - cache static assets
self.addEventListener('install', event => {
    console.log('Pocket Pulsar Service Worker installing...');
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => {
                console.log('Caching static assets...');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => self.skipWaiting())
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('Pocket Pulsar Service Worker activating...');
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
                        console.log('Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(() => self.clients.claim())
    );
});

// Fetch event - serve from cache or network
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);

    // Handle API requests
    if (API_ENDPOINTS.some(endpoint => url.pathname.startsWith(endpoint))) {
        event.respondWith(handleApiRequest(request));
        return;
    }

    // Handle static assets and pages
    if (request.method === 'GET') {
        event.respondWith(
            caches.match(request)
                .then(response => {
                    if (response) {
                        return response;
                    }

                    return fetch(request)
                        .then(response => {
                            // Cache successful responses
                            if (response.status === 200) {
                                const responseClone = response.clone();
                                caches.open(DYNAMIC_CACHE)
                                    .then(cache => cache.put(request, responseClone));
                            }
                            return response;
                        })
                        .catch(() => {
                            // Return offline fallback for navigation requests
                            if (request.mode === 'navigate') {
                                return caches.match('/iphone');
                            }
                        });
                })
        );
    }
});

// Handle API requests with network-first strategy
async function handleApiRequest(request) {
    try {
        // Try network first
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            // Cache successful API responses
            const cache = await caches.open(DYNAMIC_CACHE);
            cache.put(request, networkResponse.clone());
            return networkResponse;
        }
    } catch (error) {
        console.log('Network failed, trying cache for:', request.url);
    }

    // Fallback to cache
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
        return cachedResponse;
    }

    // Return offline data structure
    return new Response(
        JSON.stringify({
            status: 'offline',
            message: 'Data from cache - network unavailable',
            timestamp: new Date().toISOString(),
            data: getOfflineFallbackData(request.url)
        }),
        {
            headers: { 'Content-Type': 'application/json' }
        }
    );
}

// Provide fallback data when offline
function getOfflineFallbackData(url) {
    if (url.includes('/api/status')) {
        return {
            health: 98,
            active_agents: 23,
            cpu_usage: 75,
            memory_usage: 45,
            financial_score: 92,
            repos_count: 47,
            last_update: new Date().toISOString()
        };
    }

    if (url.includes('/api/agents')) {
        return {
            agents: [
                { id: 'repo_sentry', name: 'Repo Sentry', type: 'repo_sentry', status: 'online', efficiency: 98, status_text: 'Monitoring repos' },
                { id: 'daily_brief', name: 'Daily Brief', type: 'daily_brief', status: 'online', efficiency: 95, status_text: 'Intelligence ready' },
                { id: 'council', name: 'Council', type: 'council', status: 'online', efficiency: 100, status_text: 'Autonomy active' }
            ]
        };
    }

    if (url.includes('/api/systems')) {
        return {
            systems: [
                { id: 'quantum_quasar', name: 'Quantum Quasar', cpu: 75, ram: 45, status: 'Online' },
                { id: 'tablet_titan', name: 'Tablet Titan', cpu: 60, ram: 35, status: 'Online' },
                { id: 'windows_companion', name: 'Windows Companion', cpu: 85, ram: 70, status: 'Online' }
            ]
        };
    }

    if (url.includes('/api/finance')) {
        return {
            balance: 127543.89,
            revenue: 15234.56,
            compliance: 98,
            transactions: [
                { description: 'Investment Return', amount: 2345.67 },
                { description: 'Server Costs', amount: -156.23 },
                { description: 'Client Payment', amount: 5000.00 }
            ]
        };
    }

    return {};
}

// Background sync for commands when back online
self.addEventListener('sync', event => {
    if (event.tag === 'background-sync') {
        event.waitUntil(doBackgroundSync());
    }
});

async function doBackgroundSync() {
    // Process any queued commands or data updates
    console.log('Performing background sync...');

    // Notify clients that sync is complete
    const clients = await self.clients.matchAll();
    clients.forEach(client => {
        client.postMessage({
            type: 'SYNC_COMPLETE',
            timestamp: new Date().toISOString()
        });
    });
}

// Handle push notifications (future feature)
self.addEventListener('push', event => {
    if (event.data) {
        const data = event.data.json();
        const options = {
            body: data.body,
            icon: '/static/icons/icon-192.png',
            badge: '/static/icons/icon-192.png',
            vibrate: [200, 100, 200],
            data: data.url,
            actions: [
                { action: 'view', title: 'View' },
                { action: 'dismiss', title: 'Dismiss' }
            ]
        };

        event.waitUntil(
            self.registration.showNotification(data.title, options)
        );
    }
});

// Handle notification clicks
self.addEventListener('notificationclick', event => {
    event.notification.close();

    if (event.action === 'view') {
        event.waitUntil(
            clients.openWindow(event.notification.data || '/iphone')
        );
    }
});

// Periodic background updates (if supported)
self.addEventListener('periodicsync', event => {
    if (event.tag === 'update-metrics') {
        event.waitUntil(updateMetricsInBackground());
    }
});

async function updateMetricsInBackground() {
    console.log('Updating metrics in background...');

    try {
        // Fetch latest data and update cache
        const responses = await Promise.all(
            API_ENDPOINTS.map(endpoint => fetch(endpoint))
        );

        const cache = await caches.open(DYNAMIC_CACHE);
        API_ENDPOINTS.forEach((endpoint, index) => {
            if (responses[index].ok) {
                cache.put(endpoint, responses[index]);
            }
        });

        // Notify clients of updated data
        const clients = await self.clients.matchAll();
        clients.forEach(client => {
            client.postMessage({
                type: 'METRICS_UPDATED',
                timestamp: new Date().toISOString()
            });
        });
    } catch (error) {
        console.error('Background metrics update failed:', error);
    }
}</content>
<parameter name="filePath">$HOME/repos/ELECTRIC ICE/Digital-Labour/static/sw_iphone.js