/* ═══════════════════════════════════════════════════════════
   MATRIX MAXIMIZER — Service Worker (Phase 3: PWA)
   Offline caching with stale-while-revalidate strategy
   ═══════════════════════════════════════════════════════════ */
const CACHE_NAME = 'matrix-v3';
const OFFLINE_URL = '/';

// Assets to pre-cache for offline
const PRECACHE = [
  '/',
  '/static/manifest.json',
  '/static/icons/icon-192.svg',
  '/static/icons/icon-512.svg',
  'https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js'
];

// API paths that should cache last-known response
const API_CACHE_PATHS = [
  '/api/matrix',
  '/api/alerts',
  '/api/metrics-info'
];

// ── Install: pre-cache shell ───────────────────────────
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting())
  );
});

// ── Activate: clean old caches ──────────────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

// ── Fetch: stale-while-revalidate for APIs, cache-first for assets
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Skip SSE stream — must not be cached
  if (url.pathname === '/api/stream') return;

  // Skip non-GET
  if (event.request.method !== 'GET') return;

  // API requests: network-first, fall back to cached
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          // Cache successful API responses
          if (response.ok && API_CACHE_PATHS.includes(url.pathname)) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
          }
          return response;
        })
        .catch(() => {
          // Offline: return cached API response if available
          return caches.match(event.request).then(cached => {
            if (cached) return cached;
            return new Response(JSON.stringify({
              offline: true,
              message: 'Offline — showing last known data'
            }), {
              headers: { 'Content-Type': 'application/json' }
            });
          });
        })
    );
    return;
  }

  // Static assets + page: cache-first, then network
  event.respondWith(
    caches.match(event.request)
      .then(cached => {
        const networkFetch = fetch(event.request)
          .then(response => {
            if (response.ok) {
              const clone = response.clone();
              caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
            }
            return response;
          })
          .catch(() => cached);

        return cached || networkFetch;
      })
  );
});

// ── Push notifications for critical alerts ──────────────
self.addEventListener('push', event => {
  if (!event.data) return;
  try {
    const data = event.data.json();
    event.waitUntil(
      self.registration.showNotification(data.title || 'MATRIX MAXIMIZER', {
        body: data.message || 'Alert',
        icon: '/static/icons/icon-192.svg',
        badge: '/static/icons/icon-192.svg',
        tag: data.id || 'matrix-alert',
        data: { url: '/' },
        vibrate: [200, 100, 200]
      })
    );
  } catch (e) {
    console.error('Push parse error:', e);
  }
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: 'window' })
      .then(windowClients => {
        // Focus existing window or open new one
        for (const client of windowClients) {
          if (client.url.includes('/') && 'focus' in client) {
            return client.focus();
          }
        }
        return clients.openWindow('/');
      })
  );
});
