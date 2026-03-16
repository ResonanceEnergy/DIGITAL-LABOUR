// Service Worker for Tablet Titan iPad Pro PWA
// Handles caching, offline functionality, background sync, and iPad multitasking

const CACHE_NAME = 'tablet-titan-v1.0.0';
const STATIC_CACHE = 'tablet-titan-static-v1.0.0';
const DYNAMIC_CACHE = 'tablet-titan-dynamic-v1.0.0';
const MATRIX_CACHE = 'tablet-titan-matrix-v1.0.0';

// Assets to cache immediately for iPad Pro
const STATIC_ASSETS = [
    '/static/css/ipad.css',
    '/static/js/ipad.js',
    '/static/manifest_ipad.json',
    '/static/icons/icon-192.png',
    '/static/icons/icon-512.png',
    '/static/favicon.ico',
    '/ipad', // Main app route
    '/templates/ipad_dashboard.html'
];

// API endpoints that should be cached for offline use
const API_ENDPOINTS = [
    '/api/status',
    '/api/matrix',
    '/api/quasmem',
    '/api/agents',
    '/api/systems',
    '/api/finance',
    '/api/analytics'
];

// Matrix data cache for offline matrix visualization
const MATRIX_ENDPOINTS = [
    '/api/matrix'
];

// Install event - cache static assets
self.addEventListener('install', event => {
    console.log('Tablet Titan Service Worker installing...');
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => {
                console.log('Caching static assets for iPad Pro...');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => self.skipWaiting())
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('Tablet Titan Service Worker activating...');
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== STATIC_CACHE &&
                        cacheName !== DYNAMIC_CACHE &&
                        cacheName !== MATRIX_CACHE) {
                        console.log('Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
        .then(() => self.clients.claim())
    );
});

// Fetch event - handle requests with caching strategies
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);

    // Handle API requests with network-first strategy
    if (API_ENDPOINTS.some(endpoint => url.pathname.startsWith(endpoint))) {
        event.respondWith(networkFirstStrategy(request));
        return;
    }

    // Handle matrix data with special caching
    if (MATRIX_ENDPOINTS.some(endpoint => url.pathname.startsWith(endpoint))) {
        event.respondWith(matrixCacheStrategy(request));
        return;
    }

    // Handle static assets with cache-first strategy
    if (STATIC_ASSETS.some(asset => url.pathname === asset)) {
        event.respondWith(cacheFirstStrategy(request));
        return;
    }

    // Default strategy for other requests
    event.respondWith(networkFirstStrategy(request));
});

// Cache-first strategy for static assets
async function cacheFirstStrategy(request) {
    try {
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }

        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            const cache = await caches.open(STATIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch (error) {
        console.error('Cache-first strategy failed:', error);
        return new Response('Offline - Static asset not available', {
            status: 503,
            statusText: 'Service Unavailable'
        });
    }
}

// Network-first strategy for API calls
async function networkFirstStrategy(request) {
    try {
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            const cache = await caches.open(DYNAMIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch (error) {
        console.log('Network failed, trying cache:', error);
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }

        return new Response(JSON.stringify({
            error: 'Offline',
            message: 'Network unavailable, cached data not found',
            timestamp: new Date().toISOString()
        }), {
            status: 503,
            statusText: 'Service Unavailable',
            headers: { 'Content-Type': 'application/json' }
        });
    }
}

// Special caching strategy for matrix data
async function matrixCacheStrategy(request) {
    try {
        // Try network first
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            const cache = await caches.open(MATRIX_CACHE);
            cache.put(request, networkResponse.clone());

            // Also update all clients with fresh data
            self.clients.matchAll().then(clients => {
                clients.forEach(client => {
                    client.postMessage({
                        type: 'MATRIX_UPDATE',
                        data: networkResponse.clone().json()
                    });
                });
            });

            return networkResponse;
        }
    } catch (error) {
        console.log('Matrix network failed, using cache:', error);
    }

    // Fallback to cache
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
        return cachedResponse;
    }

    // Generate offline matrix data
    return new Response(JSON.stringify({
        matrix: [
            {
                type: 'quantum-quasar',
                status: 'offline',
                name: 'Quantum Quasar',
                device: 'Mac Workstation (Offline)',
                metrics: [
                    { label: 'CPU', value: 'N/A' },
                    { label: 'MEM', value: 'N/A' }
                ]
            },
            {
                type: 'pocket-pulsar',
                status: 'offline',
                name: 'Pocket Pulsar',
                device: 'iPhone (Offline)',
                metrics: [
                    { label: 'BAT', value: 'N/A' },
                    { label: 'NET', value: 'N/A' }
                ]
            },
            {
                type: 'tablet-titan',
                status: 'online',
                name: 'Tablet Titan',
                device: 'iPad Pro MU202VC/A',
                metrics: [
                    { label: 'BAT', value: '87%' },
                    { label: 'BT', value: '34:42:62:2C:5D:9D' }
                ]
            }
        ],
        total_nodes: 3,
        online_nodes: 1,
        system_health: 65,
        timestamp: new Date().toISOString(),
        offline: true
    }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
    });
}

// Background sync for offline actions
self.addEventListener('sync', event => {
    console.log('Background sync triggered:', event.tag);

    if (event.tag === 'matrix-sync') {
        event.waitUntil(syncMatrixData());
    }

    if (event.tag === 'agent-sync') {
        event.waitUntil(syncAgentData());
    }
});

// Sync matrix data when back online
async function syncMatrixData() {
    try {
        const response = await fetch('/api/matrix');
        if (response.ok) {
            const data = await response.json();
            // Update all clients with fresh data
            self.clients.matchAll().then(clients => {
                clients.forEach(client => {
                    client.postMessage({
                        type: 'MATRIX_SYNC_COMPLETE',
                        data: data
                    });
                });
            });
        }
    } catch (error) {
        console.error('Matrix sync failed:', error);
    }
}

// Sync agent data when back online
async function syncAgentData() {
    try {
        // Sync any pending agent actions
        console.log('Syncing agent data...');
        // Implementation would depend on specific agent sync requirements
    } catch (error) {
        console.error('Agent sync failed:', error);
    }
}

// Handle messages from the main thread
self.addEventListener('message', event => {
    const { type, data } = event.data;

    switch (type) {
        case 'SKIP_WAITING':
            self.skipWaiting();
            break;

        case 'GET_CACHE_INFO':
            getCacheInfo().then(info => {
                event.ports[0].postMessage(info);
            });
            break;

        case 'CLEAR_CACHE':
            clearAllCaches().then(() => {
                event.ports[0].postMessage({ success: true });
            });
            break;

        default:
            console.log('Unknown message type:', type);
    }
});

// Get cache information
async function getCacheInfo() {
    const cacheNames = await caches.keys();
    const info = {};

    for (const cacheName of cacheNames) {
        const cache = await caches.open(cacheName);
        const keys = await cache.keys();
        info[cacheName] = keys.length;
    }

    return info;
}

// Clear all caches
async function clearAllCaches() {
    const cacheNames = await caches.keys();
    await Promise.all(
        cacheNames.map(cacheName => caches.delete(cacheName))
    );
}

// Handle push notifications (if implemented)
self.addEventListener('push', event => {
    if (!event.data) return;

    const data = event.data.json();
    const options = {
        body: data.body,
        icon: '/static/icons/icon-192.png',
        badge: '/static/icons/icon-192.png',
        vibrate: [200, 100, 200],
        data: {
            url: data.url || '/ipad'
        },
        actions: [
            {
                action: 'view',
                title: 'View',
                icon: '/static/icons/view.png'
            },
            {
                action: 'dismiss',
                title: 'Dismiss'
            }
        ]
    };

    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

// Handle notification clicks
self.addEventListener('notificationclick', event => {
    event.notification.close();

    if (event.action === 'dismiss') return;

    const url = event.notification.data.url;
    event.waitUntil(
        clients.openWindow(url)
    );
});

// Periodic background fetch for matrix updates (if supported)
if ('periodicSync' in self.registration) {
    self.addEventListener('periodicsync', event => {
        if (event.tag === 'matrix-update') {
            event.waitUntil(updateMatrixInBackground());
        }
    });
}

async function updateMatrixInBackground() {
    try {
        const response = await fetch('/api/matrix');
        if (response.ok) {
            const data = await response.json();
            // Cache the updated data
            const cache = await caches.open(MATRIX_CACHE);
            cache.put('/api/matrix', new Response(JSON.stringify(data)));
        }
    } catch (error) {
        console.error('Background matrix update failed:', error);
    }
}

// Handle iPad Pro specific features
self.addEventListener('backgroundfetch', event => {
    if (event.tag === 'large-file-download') {
        event.waitUntil(handleLargeFileDownload(event));
    }
});

async function handleLargeFileDownload(event) {
    // Handle large file downloads for iPad Pro
    const records = await event.registration.matchAll();
    // Implementation for handling large downloads
    console.log('Handling large file download for iPad Pro');
}

// Error handling and logging
self.addEventListener('error', event => {
    console.error('Service Worker error:', event.error);
});

self.addEventListener('unhandledrejection', event => {
    console.error('Service Worker unhandled rejection:', event.reason);
});