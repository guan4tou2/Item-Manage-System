const CACHE_NAME = 'item-manage-v1';
const STATIC_ASSETS = [
  '/',
  '/static/css/bootstrap.min.css',
  '/static/css/main.css',
  '/static/css/navbar.css',
  '/static/js/bootstrap.bundle.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css',
  'https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700;900&display=swap'
];

// Install Event - Cache Static Assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
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
        // Optional: Cache successful page visits for offline fallback
        // if (response.status === 200) {
        //   const responseClone = response.clone();
        //   caches.open(CACHE_NAME).then((cache) => {
        //     cache.put(event.request, responseClone);
        //   });
        // }
        return response;
      })
      .catch(() => {
        // Fallback to cache if network fails
        return caches.match(event.request);
      })
  );
});
