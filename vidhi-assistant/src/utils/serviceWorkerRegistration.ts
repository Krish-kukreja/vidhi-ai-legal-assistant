/**
 * Service Worker Registration Utility
 * Handles registration, updates, and offline queue management
 */

export interface QueuedAction {
  url: string;
  method?: string;
  headers?: Record<string, string>;
  body?: any;
  queuedAt?: number;
  id?: string;
}

export interface SyncResult {
  total: number;
  synced: number;
  failed: number;
  errors: Array<{ id: string; error: string }>;
}

/**
 * Register service worker
 */
export async function registerServiceWorker(): Promise<ServiceWorkerRegistration | null> {
  if (!('serviceWorker' in navigator)) {
    console.warn('Service Worker not supported in this browser');
    return null;
  }

  try {
    const registration = await navigator.serviceWorker.register('/service-worker.js', {
      scope: '/'
    });

    console.log('Service Worker registered:', registration.scope);

    // Check for updates
    registration.addEventListener('updatefound', () => {
      const newWorker = registration.installing;
      if (newWorker) {
        newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            // New service worker available
            console.log('New service worker available');
            notifyUpdate();
          }
        });
      }
    });

    return registration;
  } catch (error) {
    console.error('Service Worker registration failed:', error);
    return null;
  }
}

/**
 * Unregister service worker
 */
export async function unregisterServiceWorker(): Promise<boolean> {
  if (!('serviceWorker' in navigator)) {
    return false;
  }

  try {
    const registration = await navigator.serviceWorker.getRegistration();
    if (registration) {
      const success = await registration.unregister();
      console.log('Service Worker unregistered:', success);
      return success;
    }
    return false;
  } catch (error) {
    console.error('Service Worker unregistration failed:', error);
    return false;
  }
}

/**
 * Queue an action for offline processing
 */
export async function queueOfflineAction(action: QueuedAction): Promise<string> {
  if (!navigator.serviceWorker.controller) {
    throw new Error('Service Worker not active');
  }

  return new Promise((resolve, reject) => {
    const messageChannel = new MessageChannel();

    messageChannel.port1.onmessage = (event) => {
      if (event.data.success) {
        resolve(event.data.result);
      } else {
        reject(new Error(event.data.error));
      }
    };

    navigator.serviceWorker.controller.postMessage(
      {
        type: 'QUEUE_ACTION',
        data: action
      },
      [messageChannel.port2]
    );
  });
}

/**
 * Sync offline queue
 */
export async function syncOfflineQueue(): Promise<SyncResult> {
  if (!navigator.serviceWorker.controller) {
    throw new Error('Service Worker not active');
  }

  return new Promise((resolve, reject) => {
    const messageChannel = new MessageChannel();

    messageChannel.port1.onmessage = (event) => {
      if (event.data.success) {
        resolve(event.data.result);
      } else {
        reject(new Error(event.data.error));
      }
    };

    navigator.serviceWorker.controller.postMessage(
      {
        type: 'SYNC_QUEUE'
      },
      [messageChannel.port2]
    );
  });
}

/**
 * Clear all caches
 */
export async function clearAllCaches(): Promise<void> {
  if (!navigator.serviceWorker.controller) {
    throw new Error('Service Worker not active');
  }

  return new Promise((resolve, reject) => {
    const messageChannel = new MessageChannel();

    messageChannel.port1.onmessage = (event) => {
      if (event.data.success) {
        resolve();
      } else {
        reject(new Error(event.data.error));
      }
    };

    navigator.serviceWorker.controller.postMessage(
      {
        type: 'CLEAR_CACHE'
      },
      [messageChannel.port2]
    );
  });
}

/**
 * Check if online
 */
export function isOnline(): boolean {
  return navigator.onLine;
}

/**
 * Listen for online/offline events
 */
export function addConnectivityListener(
  onOnline: () => void,
  onOffline: () => void
): () => void {
  window.addEventListener('online', onOnline);
  window.addEventListener('offline', onOffline);

  // Return cleanup function
  return () => {
    window.removeEventListener('online', onOnline);
    window.removeEventListener('offline', onOffline);
  };
}

/**
 * Listen for service worker messages
 */
export function addServiceWorkerMessageListener(
  callback: (message: any) => void
): () => void {
  const handler = (event: MessageEvent) => {
    callback(event.data);
  };

  navigator.serviceWorker.addEventListener('message', handler);

  // Return cleanup function
  return () => {
    navigator.serviceWorker.removeEventListener('message', handler);
  };
}

/**
 * Notify user of service worker update
 */
function notifyUpdate() {
  // Dispatch custom event for UI to handle
  window.dispatchEvent(
    new CustomEvent('sw-update-available', {
      detail: {
        message: 'A new version is available. Please reload to update.'
      }
    })
  );
}

/**
 * Skip waiting and activate new service worker
 */
export async function skipWaitingAndActivate(): Promise<void> {
  if (!navigator.serviceWorker.controller) {
    return;
  }

  navigator.serviceWorker.controller.postMessage({
    type: 'SKIP_WAITING'
  });

  // Wait for new service worker to activate
  return new Promise((resolve) => {
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      resolve();
    });
  });
}

/**
 * Request background sync
 */
export async function requestBackgroundSync(tag: string = 'sync-offline-queue'): Promise<void> {
  if (!('serviceWorker' in navigator) || !('sync' in ServiceWorkerRegistration.prototype)) {
    console.warn('Background Sync not supported');
    return;
  }

  try {
    const registration = await navigator.serviceWorker.ready;
    await (registration as any).sync.register(tag);
    console.log('Background sync registered:', tag);
  } catch (error) {
    console.error('Background sync registration failed:', error);
  }
}
