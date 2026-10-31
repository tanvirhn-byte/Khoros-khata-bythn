// Khoroch er Khata - Progressive Web App Service Worker (Phase 12)
const CACHE_NAME = 'kh-pwa-v12';

// Essential application shell assets to precache
const PRECACHE_ASSETS = [
  './',
  'index.html',
  'manifest.json',
  'icon-192.png',
  'icon-512.png',
  'icon-maskable-192.png',
  'icon-maskable-512.png',
  'apple-touch-icon.png'
];

// Install event: cache app shell and optionally wait for skipWaiting
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      // Precache individual assets gracefully (some fonts or icons may fail on isolated origins)
      return Promise.allSettled(
        PRECACHE_ASSETS.map(asset =>
          cache.add(asset).catch(err => {
            console.warn('[SW] Precache failed for:', asset, err);
          })
        )
      );
    }).then(() => {
      // Allow new service worker to prepare without immediately hijacking active users
    })
  );
});

// Activate event: clean up older cache versions, claim clients
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.map(key => {
          if (key !== CACHE_NAME && (key.startsWith('kh-') || key.startsWith('khoroch-'))) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Message listener: allow client to prompt skipWaiting during safe update window
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

// Fetch event: Network-first for dynamic assets, cache-first for static shell, never cache API
self.addEventListener('fetch', event => {
  const req = event.request;
  const url = new URL(req.url);

  // 1. Never cache non-GET requests
  if (req.method !== 'GET') {
    return;
  }

  // 2. Never cache backend API or admin endpoints
  if (
    url.pathname.endsWith('api.php') ||
    url.pathname.endsWith('admin.php') ||
    url.searchParams.has('a') ||
    url.pathname.includes('/api/') ||
    req.headers.has('Authorization')
  ) {
    return;
  }

  // 3. For navigation requests (loading index.html), attempt network then cache fallback
  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req)
        .then(res => {
          if (res && res.status === 200) {
            const clone = res.clone();
            caches.open(CACHE_NAME).then(c => c.put(req, clone));
          }
          return res;
        })
        .catch(() => {
          return caches.match(req).then(cached => {
            return cached || caches.match('index.html') || caches.match('./');
          });
        })
    );
    return;
  }

  // 4. For static assets (CSS, JS, images, fonts): Cache-first with network fallback
  event.respondWith(
    caches.match(req).then(cached => {
      if (cached) {
        // Return cached and update in background if online
        fetch(req).then(res => {
          if (res && res.status === 200 && (res.type === 'basic' || res.type === 'cors')) {
            const clone = res.clone();
            caches.open(CACHE_NAME).then(c => c.put(req, clone));
          }
        }).catch(() => {/* offline */});
        return cached;
      }

      // Not in cache, fetch from network and store
      return fetch(req)
        .then(res => {
          if (res && res.status === 200 && (res.type === 'basic' || res.type === 'cors')) {
            const clone = res.clone();
            caches.open(CACHE_NAME).then(c => c.put(req, clone));
          }
          return res;
        })
        .catch(err => {
          // If asset is an image or document, fallback safely
          if (req.destination === 'image') {
            return caches.match('icon-192.png');
          }
          throw err;
        });
    })
  );
});
