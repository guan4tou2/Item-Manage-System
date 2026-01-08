# PWA Development Skill

## Description
Progressive Web App development and testing for Item Management System.

## Trigger Phrases
- "pwa"
- "offline"
- "service worker"
- "manifest"

## When to Use
When you need to:
- Implement PWA features
- Test offline functionality
- Configure service worker
- Update web manifest
- Test PWA installation
- Optimize for mobile
- Test service worker updates
- Debug offline caching

## Available Tools
- Bash (for PWA tools)
- Read/Write (for manifest and service worker)
- Playwright/Puppeteer (for PWA testing)
- Grep (for finding PWA-related code)

## MUST DO
1. Ensure web manifest is complete and valid
2. Register service worker correctly
3. Cache critical resources for offline use
4. Implement proper cache strategies
5. Test offline functionality thoroughly
6. Test PWA installation on mobile
7. Update service worker with proper versioning
8. Handle service worker updates gracefully
9. Implement push notifications (if needed)
10. Test on multiple browsers (Chrome, Safari, Firefox)

## MUST NOT DO
- Do NOT cache sensitive data (user sessions, API tokens)
- Do NOT cache API responses that change frequently
- Do NOT ignore service worker errors
- Do NOT use cache-first for all resources
- Do NOT forget to update service worker version
- Do NOT break existing PWA functionality

## Context
- Flask web application
- Already has PWA support (manifest.json, service-worker.js)
- Bootstrap 5 UI framework
- Vanilla JavaScript
- Supports offline functionality
- Installable as mobile app

## Web Manifest

### manifest.json
```json
{
  "name": "Item Management System",
  "short_name": "Item Manager",
  "description": "Manage your items with expiration tracking and notifications",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#007bff",
  "orientation": "portrait",
  "scope": "/",
  "icons": [
    {
      "src": "/static/icons/icon-72x72.png",
      "sizes": "72x72",
      "type": "image/png"
    },
    {
      "src": "/static/icons/icon-96x96.png",
      "sizes": "96x96",
      "type": "image/png"
    },
    {
      "src": "/static/icons/icon-128x128.png",
      "sizes": "128x128",
      "type": "image/png"
    },
    {
      "src": "/static/icons/icon-144x144.png",
      "sizes": "144x144",
      "type": "image/png"
    },
    {
      "src": "/static/icons/icon-152x152.png",
      "sizes": "152x152",
      "type": "image/png"
    },
    {
      "src": "/static/icons/icon-192x192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/static/icons/icon-384x384.png",
      "sizes": "384x384",
      "type": "image/png"
    },
    {
      "src": "/static/icons/icon-512x512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ],
  "categories": ["productivity", "utilities"],
  "shortcuts": [
    {
      "name": "Add Item",
      "short_name": "Add",
      "description": "Quick add a new item",
      "url": "/items/new",
      "icons": [{ "src": "/static/icons/icon-96x96.png", "sizes": "96x96" }]
    }
  ]
}
```

### Manifest Validation
```bash
# Using online validator
# Visit: https://manifest-validator.appspot.com/
# Or use Lighthouse

# Using Node.js
npm install -g web-manifest-validator
web-manifest-validator static/manifest.json
```

## Service Worker

### service-worker.js
```javascript
const CACHE_NAME = 'item-manager-v1';
const STATIC_CACHE = 'static-v1';
const API_CACHE = 'api-v1';

// Cache critical static assets
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/static/css/bootstrap.min.css',
  '/static/css/style.css',
  '/static/js/app.js',
  '/static/js/notifications.js',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png',
  '/manifest.json'
];

self.addEventListener('install', (event) => {
  console.log('[Service Worker] Installing...');

  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    }).then(() => {
      return self.skipWaiting();
    })
  );
});

self.addEventListener('activate', (event) => {
  console.log('[Service Worker] Activating...');

  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== STATIC_CACHE && cacheName !== API_CACHE) {
            console.log('[Service Worker] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      return self.clients.claim();
    })
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Cache-first for static assets
  if (request.method === 'GET' && STATIC_ASSETS.includes(url.pathname)) {
    event.respondWith(
      caches.open(STATIC_CACHE).then((cache) => {
        return cache.match(request).then((response) => {
          if (response) {
            return response;
          }
          return fetch(request).then((response) => {
            cache.put(request, response.clone());
            return response;
          });
        });
      })
    );
    return;
  }

  // Network-first for API requests
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      caches.open(API_CACHE).then((cache) => {
        return fetch(request).then((response) => {
          // Only cache successful GET requests
          if (response.status === 200 && request.method === 'GET') {
            cache.put(request, response.clone());
          }
          return response;
        }).catch(() => {
          // Fallback to cache if network fails
          return cache.match(request);
        });
      })
    );
    return;
  }

  // Default to network
  event.respondWith(fetch(request));
});

// Handle background sync
self.addEventListener('sync', (event) => {
  console.log('[Service Worker] Background sync:', event.tag);

  if (event.tag === 'sync-items') {
    event.waitUntil(syncItems());
  }
});

async function syncItems() {
  try {
    const itemsResponse = await fetch('/api/items');
    const items = await itemsResponse.json();

    // Store in IndexedDB for offline access
    const db = await openDB();
    const tx = db.transaction('items', 'readwrite');
    const store = tx.objectStore('items');

    await store.clear();
    for (const item of items) {
      await store.put(item);
    }

    console.log('[Service Worker] Synced', items.length, 'items');
  } catch (error) {
    console.error('[Service Worker] Sync failed:', error);
  }
}

function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('item-manager-db', 1);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains('items')) {
        db.createObjectStore('items', { keyPath: 'ItemID' });
      }
    };
  });
}
```

## Service Worker Registration

### In HTML
```html
<script>
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/service-worker.js')
        .then((registration) => {
          console.log('[App] Service Worker registered:', registration.scope);

          // Check for updates
          registration.onupdatefound = () => {
            const installingWorker = registration.installing;
            installingWorker.onstatechange = () => {
              if (installingWorker.state === 'installed' && navigator.serviceWorker.controller) {
                // Show update notification
                showUpdateNotification();
              }
            };
          };

          // Listen for controller change
          navigator.serviceWorker.addEventListener('controllerchange', () => {
            window.location.reload();
          });
        })
        .catch((error) => {
          console.error('[App] Service Worker registration failed:', error);
        });
    });
  } else {
    console.warn('[App] Service Worker not supported');
  }
</script>
```

### In Flask Route
```python
@app.route('/service-worker.js')
def service_worker():
    """Serve service worker with correct headers"""
    response = send_from_directory('static', 'service-worker.js')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Service-Worker-Allowed'] = '/'
    return response
```

## PWA Testing

### Lighthouse Audit
```bash
# Using Chrome DevTools
1. Open DevTools
2. Go to Lighthouse tab
3. Select "Progressive Web App"
4. Click "Generate report"

# Using CLI
npm install -g lighthouse
lighthouse http://localhost:8080 --view
```

### Offline Testing
```bash
# Using Chrome DevTools
1. Open DevTools
2. Go to Network tab
3. Check "Offline" checkbox
4. Reload page
5. Test functionality

# Or use Chrome DevTools -> Application -> Service Workers
# Check "Offline" for service worker
```

### Install Testing
```bash
# Desktop (Chrome)
1. Open Chrome
2. Click install icon in address bar
3. Verify app launches in standalone mode
4. Check window chrome (should be minimal)

# Mobile (Chrome)
1. Open Chrome on mobile
2. Tap menu -> "Add to Home screen"
3. Verify app installs as PWA
4. Test offline functionality

# iOS (Safari)
1. Open Safari on iOS
2. Tap Share button -> "Add to Home Screen"
3. Verify app installs with proper icon
4. Test functionality
```

### Service Worker Testing
```javascript
// In browser console
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.getRegistrations().then((registrations) => {
    console.log('Registered Service Workers:', registrations);
  });

  navigator.serviceWorker.ready.then((registration) => {
    console.log('Service Worker ready:', registration);

    // Test messaging
    registration.active.postMessage({ type: 'test' });
  });
}

// Listen for messages
navigator.serviceWorker.addEventListener('message', (event) => {
  console.log('Message from Service Worker:', event.data);
});
```

## Cache Strategies

### Cache-First (Static Assets)
```javascript
// Best for: CSS, JS, images
// Speed: Fast (cached)
// Freshness: Stale (needs update)

event.respondWith(
  caches.match(request).then((cached) => {
    return cached || fetch(request).then((response) => {
      const clone = response.clone();
      caches.open(STATIC_CACHE).then((cache) => {
        cache.put(request, clone);
      });
      return response;
    });
  })
);
```

### Network-First (API Calls)
```javascript
// Best for: API endpoints, dynamic content
// Speed: Medium (network)
// Freshness: Fresh (always latest)

event.respondWith(
  fetch(request).then((response) => {
    if (response.status === 200) {
      const clone = response.clone();
      caches.open(API_CACHE).then((cache) => {
        cache.put(request, clone);
      });
    }
    return response;
  }).catch(() => {
    return caches.match(request);
  })
);
```

### Stale-While-Revalidate (Hybrid)
```javascript
// Best for: Content that needs fresh data but can show stale
// Speed: Fast (immediate cache)
// Freshness: Updates in background

event.respondWith(
  caches.open(STATIC_CACHE).then((cache) => {
    return cache.match(request).then((cached) => {
      const fetchPromise = fetch(request).then((response) => {
        cache.put(request, response.clone());
        return response;
      });

      return cached || fetchPromise;
    });
  })
);
```

## Push Notifications

### VAPID Keys Generation
```bash
# Generate VAPID keys
npm install -g web-push
web-push generate-vapid-keys

# Output:
# Public Key: XXX
# Private Key: YYY
```

### Subscribe to Push
```javascript
// In main app
if ('serviceWorker' in navigator && 'PushManager' in window) {
  navigator.serviceWorker.ready.then((registration) => {
    return registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: '<YOUR_PUBLIC_VAPID_KEY>'
    });
  }).then((subscription) => {
    // Send subscription to server
    fetch('/api/notifications/subscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(subscription)
    });
  });
}
```

## Offline Support

### Offline Detection
```javascript
window.addEventListener('online', () => {
  console.log('[App] Online');
  document.body.classList.remove('offline');
  // Sync data
});

window.addEventListener('offline', () => {
  console.log('[App] Offline');
  document.body.classList.add('offline');
  // Show offline notification
});
```

### Offline UI Indicator
```css
/* Add to CSS */
body.offline::before {
  content: "You are offline. Some features may not work.";
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  background: #ffc107;
  color: #000;
  padding: 10px;
  text-align: center;
  z-index: 9999;
}
```

### IndexedDB for Offline Data
```javascript
const DB_NAME = 'item-manager-offline';
const DB_VERSION = 1;

async function saveOfflineData(key, data) {
  const db = await openDB();
  const tx = db.transaction('offline', 'readwrite');
  const store = tx.objectStore('offline');
  await store.put({ key, data, timestamp: Date.now() });
}

async function getOfflineData(key) {
  const db = await openDB();
  const tx = db.transaction('offline', 'readonly');
  const store = tx.objectStore('offline');
  return await store.get(key);
}

function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains('offline')) {
        db.createObjectStore('offline', { keyPath: 'key' });
      }
    };
  });
}
```

## PWA Checklist
- [ ] Web manifest is valid and complete
- [ ] Service worker is registered correctly
- [ ] Critical assets are cached
- [ ] Offline functionality works
- [ ] PWA installs on desktop
- [ ] PWA installs on mobile (iOS and Android)
- [ ] Icons are correctly sized
- [ ] Theme color matches app design
- [ ] Start URL is correct
- [ ] Display mode is appropriate (standalone)
- [ ] Service worker updates handled
- [ ] Cache strategies are appropriate
- [ ] No console errors
- [ ] Lighthouse score > 90
- [ ] Background sync configured (if needed)
- [ ] Push notifications working (if needed)
- [ ] IndexedDB for offline data (if needed)

## PWA Tools
- **Lighthouse** - PWA audit and scoring
- **PWA Builder** - Online PWA testing tool
- **Service Worker Simulator** - Test service worker logic
- **Manifest Validator** - Validate manifest.json
- **Workbox** - Service worker library
- **web-push** - Push notification library

## Troubleshooting

### Service Worker Not Updating
```javascript
// Force update
navigator.serviceWorker.getRegistrations().then((registrations) => {
  for (const registration of registrations) {
    registration.update();
  }
});
```

### Cache Not Clearing
```bash
# Clear all caches
navigator.serviceWorker.getRegistrations().then((registrations) => {
  for (const registration of registrations) {
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => caches.delete(cacheName))
      );
    }).then(() => {
      return registration.unregister();
    });
  }
});
```
