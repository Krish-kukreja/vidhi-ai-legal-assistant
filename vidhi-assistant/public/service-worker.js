/**
 * VIDHI Service Worker
 * Enables offline functionality with caching and queue management
 */

const CACHE_VERSION = 'vidhi-v1';
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const API_CACHE = `${CACHE_VERSION}-api`;
const AUDIO_CACHE = `${CACHE_VERSION}-audio`;
const MESSAGE_CACHE = `${CACHE_VERSION}-messages`;

// Static assets to cache on install
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/robots.txt',
  '/placeholder.svg'
];

// Cache size limits
const MAX_MESSAGE_CACHE = 50;
const MAX_AUDIO_CACHE = 10;

// IndexedDB configuration
const DB_NAME = 'vidhi-offline';
const DB_VERSION = 1;
const QUEUE_STORE = 'offline-queue';
const MAX_QUEUE_SIZE = 100;

/**
 * Service Worker Installation
 * Cache static assets
 */
self.addEventListener('install', (event) => {
  console.log('[Service Worker] Installing...');
  
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('[Service Worker] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => {
        console.log('[Service Worker] Installation complete');
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('[Service Worker] Installation failed:', error);
      })
  );
});

/**
 * Service Worker Activation
 * Clean up old caches
 */
self.addEventListener('activate', (event) => {
  console.log('[Service Worker] Activating...');
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((cacheName) => {
              // Delete old cache versions
              return cacheName.startsWith('vidhi-') && cacheName !== STATIC_CACHE &&
                     cacheName !== API_CACHE && cacheName !== AUDIO_CACHE &&
                     cacheName !== MESSAGE_CACHE;
            })
            .map((cacheName) => {
              console.log('[Service Worker] Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            })
        );
      })
      .then(() => {
        console.log('[Service Worker] Activation complete');
        return self.clients.claim();
      })
  );
});

/**
 * Fetch Event Handler
 * Implement cache strategies
 */
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }
  
  // Static assets: Cache-first
  if (STATIC_ASSETS.some(asset => url.pathname === asset || url.pathname.endsWith(asset))) {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
    return;
  }
  
  // Audio files: Cache-first with network update
  if (url.pathname.includes('/audio/') || url.pathname.endsWith('.mp3')) {
    event.respondWith(cacheFirstWithUpdate(request, AUDIO_CACHE, MAX_AUDIO_CACHE));
    return;
  }
  
  // API calls: Network-first with cache fallback
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(request, API_CACHE));
    return;
  }
  
  // Chat messages: Network-first with cache
  if (url.pathname.includes('/chat')) {
    event.respondWith(networkFirst(request, MESSAGE_CACHE));
    return;
  }
  
  // Default: Network-first
  event.respondWith(networkFirst(request, API_CACHE));
});

/**
 * Cache-first strategy
 * Serve from cache, fall back to network
 */
async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  
  if (cached) {
    console.log('[Service Worker] Cache hit:', request.url);
    return cached;
  }
  
  console.log('[Service Worker] Cache miss, fetching:', request.url);
  try {
    const response = await fetch(request);
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    console.error('[Service Worker] Fetch failed:', error);
    return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
  }
}

/**
 * Cache-first with background update
 * Serve from cache immediately, update cache in background
 */
async function cacheFirstWithUpdate(request, cacheName, maxItems) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  
  // Fetch in background to update cache
  const fetchPromise = fetch(request)
    .then(async (response) => {
      if (response.ok) {
        // Limit cache size
        const keys = await cache.keys();
        if (keys.length >= maxItems) {
          // Delete oldest entry
          await cache.delete(keys[0]);
        }
        cache.put(request, response.clone());
      }
      return response;
    })
    .catch((error) => {
      console.error('[Service Worker] Background fetch failed:', error);
    });
  
  // Return cached version immediately if available
  if (cached) {
    console.log('[Service Worker] Cache hit (updating in background):', request.url);
    return cached;
  }
  
  // Wait for network if not cached
  console.log('[Service Worker] Cache miss, waiting for network:', request.url);
  return fetchPromise;
}

/**
 * Network-first strategy
 * Try network, fall back to cache
 */
async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  
  try {
    const response = await fetch(request);
    if (response.ok) {
      // Cache successful responses
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    console.log('[Service Worker] Network failed, trying cache:', request.url);
    const cached = await cache.match(request);
    
    if (cached) {
      // Add header to indicate cached response
      const headers = new Headers(cached.headers);
      headers.set('X-From-Cache', 'true');
      
      return new Response(cached.body, {
        status: cached.status,
        statusText: cached.statusText,
        headers: headers
      });
    }
    
    return new Response(
      JSON.stringify({ error: 'Offline and no cached data available' }),
      { status: 503, statusText: 'Service Unavailable', headers: { 'Content-Type': 'application/json' } }
    );
  }
}

/**
 * Message Event Handler
 * Handle messages from clients
 */
self.addEventListener('message', (event) => {
  const { type, data } = event.data;
  
  switch (type) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;
      
    case 'QUEUE_ACTION':
      queueOfflineAction(data)
        .then(() => {
          event.ports[0].postMessage({ success: true });
        })
        .catch((error) => {
          event.ports[0].postMessage({ success: false, error: error.message });
        });
      break;
      
    case 'SYNC_QUEUE':
      syncOfflineQueue()
        .then((result) => {
          event.ports[0].postMessage({ success: true, result });
        })
        .catch((error) => {
          event.ports[0].postMessage({ success: false, error: error.message });
        });
      break;
      
    case 'CLEAR_CACHE':
      clearAllCaches()
        .then(() => {
          event.ports[0].postMessage({ success: true });
        })
        .catch((error) => {
          event.ports[0].postMessage({ success: false, error: error.message });
        });
      break;
      
    default:
      console.warn('[Service Worker] Unknown message type:', type);
  }
});

/**
 * Queue an action for offline processing
 */
async function queueOfflineAction(action) {
  const db = await openDatabase();
  const tx = db.transaction(QUEUE_STORE, 'readwrite');
  const store = tx.objectStore(QUEUE_STORE);
  
  // Check queue size
  const count = await store.count();
  if (count >= MAX_QUEUE_SIZE) {
    // Remove oldest action
    const cursor = await store.openCursor();
    if (cursor) {
      await cursor.delete();
    }
  }
  
  // Add action with timestamp
  const queuedAction = {
    ...action,
    queuedAt: Date.now(),
    id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  };
  
  await store.add(queuedAction);
  console.log('[Service Worker] Action queued:', queuedAction.id);
  
  return queuedAction.id;
}

/**
 * Sync offline queue
 */
async function syncOfflineQueue() {
  const db = await openDatabase();
  const tx = db.transaction(QUEUE_STORE, 'readonly');
  const store = tx.objectStore(QUEUE_STORE);
  const actions = await store.getAll();
  
  console.log(`[Service Worker] Syncing ${actions.length} queued actions`);
  
  const results = {
    total: actions.length,
    synced: 0,
    failed: 0,
    errors: []
  };
  
  for (const action of actions) {
    try {
      // Send action to server
      const response = await fetch(action.url, {
        method: action.method || 'POST',
        headers: action.headers || { 'Content-Type': 'application/json' },
        body: action.body ? JSON.stringify(action.body) : undefined
      });
      
      if (response.ok) {
        // Remove from queue on success
        const deleteTx = db.transaction(QUEUE_STORE, 'readwrite');
        await deleteTx.objectStore(QUEUE_STORE).delete(action.id);
        results.synced++;
        console.log('[Service Worker] Action synced:', action.id);
      } else {
        results.failed++;
        results.errors.push({ id: action.id, error: `HTTP ${response.status}` });
      }
    } catch (error) {
      results.failed++;
      results.errors.push({ id: action.id, error: error.message });
      console.error('[Service Worker] Sync failed for action:', action.id, error);
    }
  }
  
  return results;
}

/**
 * Open IndexedDB database
 */
function openDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      
      // Create object store for offline queue
      if (!db.objectStoreNames.contains(QUEUE_STORE)) {
        const store = db.createObjectStore(QUEUE_STORE, { keyPath: 'id' });
        store.createIndex('queuedAt', 'queuedAt', { unique: false });
      }
    };
  });
}

/**
 * Clear all caches
 */
async function clearAllCaches() {
  const cacheNames = await caches.keys();
  await Promise.all(
    cacheNames
      .filter(name => name.startsWith('vidhi-'))
      .map(name => caches.delete(name))
  );
  console.log('[Service Worker] All caches cleared');
}

/**
 * Background Sync Event
 * Sync offline queue when connectivity is restored
 */
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-offline-queue') {
    console.log('[Service Worker] Background sync triggered');
    event.waitUntil(
      syncOfflineQueue()
        .then((result) => {
          console.log('[Service Worker] Background sync complete:', result);
          // Notify clients
          return self.clients.matchAll().then((clients) => {
            clients.forEach((client) => {
              client.postMessage({
                type: 'SYNC_COMPLETE',
                result
              });
            });
          });
        })
        .catch((error) => {
          console.error('[Service Worker] Background sync failed:', error);
        })
    );
  }
});

console.log('[Service Worker] Loaded');
