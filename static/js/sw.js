// Service Worker - 物品管理系統
// ===============================

const CACHE_NAME = 'item-manager-v1';
const STATIC_ASSETS = [
  '/',
  '/static/css/main.css',
  '/static/js/main.js',
  '/static/img/placeholder.svg',
  '/static/img/error.svg',
  '/manifest.json'
];

// Install Event - Cache Static Assets
self.addEventListener('install', (event) => {
  console.log('[SW] Installing Service Worker...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

// Activate Event - Clean Old Caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating Service Worker...');
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => name !== CACHE_NAME)
            .map((name) => {
              console.log('[SW] Deleting old cache:', name);
              return caches.delete(name);
            })
        );
      })
      .then(() => self.clients.claim())
  );
});

// Fetch Event - Serve from Cache, Fallback to Network
self.addEventListener('fetch', (event) => {
  // Skip non-GET requests
  if (event.request.method !== 'GET') {
    return;
  }

  event.respondWith(
    caches.match(event.request)
      .then((cachedResponse) => {
        if (cachedResponse) {
          return cachedResponse;
        }

        return fetch(event.request)
          .then((response) => {
            // Don't cache non-successful responses
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }

            // Clone response for caching
            const responseToCache = response.clone();
            caches.open(CACHE_NAME)
              .then((cache) => {
                cache.put(event.request, responseToCache);
              });

            return response;
          })
          .catch(() => {
            // Return offline page if available
            return caches.match('/');
          });
      })
  );
});

// Push Event - Handle Push Notifications
self.addEventListener('push', (event) => {
  console.log('[SW] Push received:', event);

  const data = event.data ? event.data.json() : {};
  
  const options = {
    body: data.body || '您有新的通知',
    icon: '/static/brand/icon-192.png',
    badge: '/static/brand/badge-72.png',
    vibrate: [100, 50, 100],
    data: {
      url: data.url || '/',
      id: data.id
    },
    actions: [
      { action: 'open', title: '查看' },
      { action: 'dismiss', title: '關閉' }
    ],
    tag: data.tag || 'default',
    renotify: true
  };

  event.waitUntil(
    self.registration.showNotification(data.title || '物品管理系統', options)
  );
});

// Notification Click Event
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification clicked:', event);
  event.notification.close();

  const url = event.notification.data?.url || '/';

  if (event.action === 'dismiss') {
    return;
  }

  // Open or focus window
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((clientList) => {
        // Focus existing window
        for (const client of clientList) {
          if (client.url === url && 'focus' in client) {
            return client.focus();
          }
        }
        // Open new window
        if (clients.openWindow) {
          return clients.openWindow(url);
        }
      })
  );
});

// Notification Close Event
self.addEventListener('notificationclose', (event) => {
  console.log('[SW] Notification closed:', event);
  // You could send analytics here
});

// Background Sync Event (for offline functionality)
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync:', event.tag);

  if (event.tag === 'sync-items') {
    event.waitUntil(syncItems());
  }
});

// Sync Items Function
async function syncItems() {
  // This would sync offline changes when back online
  console.log('[SW] Syncing items...');
  // Implementation depends on your offline strategy
}

// Message Event - Communication with Main Thread
self.addEventListener('message', (event) => {
  console.log('[SW] Message received:', event.data);

  if (event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data.type === 'CLEAR_CACHE') {
    event.waitUntil(
      caches.keys().then((cacheNames) => {
        return Promise.all(
          cacheNames.map((name) => caches.delete(name))
        );
      })
    );
  }
});

console.log('[SW] Service Worker loaded');