const CACHE_NAME = 'item-manage-v2';
const STATIC_ASSETS = [
  '/',
  '/signin',
  '/static/offline.html',
  '/static/manifest.json',
  '/static/css/bootstrap.min.css',
  '/static/css/main.css',
  '/static/css/navbar.css',
  '/static/js/bootstrap.bundle.min.js',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/static/icons/apple-touch-icon.png'
];

// Install Event - Cache Static Assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activate Event - Clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch Event - Network First for HTML/API, Cache First for specific static assets
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Skip non-GET requests
  if (event.request.method !== 'GET') return;

  // Static Assets: Cache First
  if (url.pathname.startsWith('/static/') || 
      url.hostname.includes('cdnjs') || 
      url.hostname.includes('fonts')) {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        return cached || fetch(event.request).then((response) => {
          return caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, response.clone());
            return response;
          });
        });
      })
    );
    return;
  }

  // Others (HTML, API): Network First
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response.ok && event.request.mode === 'navigate') {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
        }
        return response;
      })
      .catch(() => {
        if (event.request.mode === 'navigate') {
          return caches.match(event.request).then((cachedPage) => {
            return cachedPage || caches.match('/static/offline.html');
          });
        }
        return caches.match(event.request);
      })
  );
});
