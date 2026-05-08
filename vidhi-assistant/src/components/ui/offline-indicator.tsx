/**
 * Offline Indicator Component
 * Shows connection status and sync progress
 */

import React, { useEffect, useState } from 'react';
import { Alert, AlertDescription } from './alert';
import { Badge } from './badge';
import { Button } from './button';
import { Progress } from './progress';
import {
  isOnline,
  addConnectivityListener,
  addServiceWorkerMessageListener,
  syncOfflineQueue,
  requestBackgroundSync
} from '../../utils/serviceWorkerRegistration';
import type { SyncResult } from '../../utils/serviceWorkerRegistration';

export function OfflineIndicator() {
  const [online, setOnline] = useState(isOnline());
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null);
  const [showSyncResult, setShowSyncResult] = useState(false);

  useEffect(() => {
    // Listen for connectivity changes
    const removeConnectivityListener = addConnectivityListener(
      () => {
        setOnline(true);
        // Automatically sync when coming online
        handleSync();
      },
      () => {
        setOnline(false);
      }
    );

    // Listen for service worker messages
    const removeMessageListener = addServiceWorkerMessageListener((message) => {
      if (message.type === 'SYNC_COMPLETE') {
        setSyncing(false);
        setSyncResult(message.result);
        setShowSyncResult(true);
        setTimeout(() => setShowSyncResult(false), 5000);
      }
    });

    return () => {
      removeConnectivityListener();
      removeMessageListener();
    };
  }, []);

  const handleSync = async () => {
    setSyncing(true);
    try {
      // Try background sync first
      await requestBackgroundSync();
      
      // If background sync not supported, sync manually
      const result = await syncOfflineQueue();
      setSyncResult(result);
      setShowSyncResult(true);
      setTimeout(() => setShowSyncResult(false), 5000);
    } catch (error) {
      console.error('Sync failed:', error);
    } finally {
      setSyncing(false);
    }
  };

  if (online && !syncing && !showSyncResult) {
    return null;
  }

  return (
    <div className="fixed top-4 right-4 z-50 max-w-md">
      {!online && (
        <Alert variant="destructive" className="mb-2">
          <AlertDescription className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
              You are offline
            </span>
            <Badge variant="outline">Offline Mode</Badge>
          </AlertDescription>
        </Alert>
      )}

      {syncing && (
        <Alert className="mb-2">
          <AlertDescription>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span>Syncing queued actions...</span>
                <Badge variant="secondary">Syncing</Badge>
              </div>
              <Progress value={undefined} className="w-full" />
            </div>
          </AlertDescription>
        </Alert>
      )}

      {showSyncResult && syncResult && (
        <Alert variant={syncResult.failed === 0 ? 'default' : 'destructive'} className="mb-2">
          <AlertDescription>
            <div className="space-y-1">
              <div className="font-medium">
                {syncResult.failed === 0 ? 'Sync Complete' : 'Sync Completed with Errors'}
              </div>
              <div className="text-sm">
                {syncResult.synced} of {syncResult.total} actions synced
                {syncResult.failed > 0 && ` (${syncResult.failed} failed)`}
              </div>
            </div>
          </AlertDescription>
        </Alert>
      )}

      {online && !syncing && (
        <Button
          variant="outline"
          size="sm"
          onClick={handleSync}
          className="w-full"
        >
          Sync Now
        </Button>
      )}
    </div>
  );
}

/**
 * Cached Content Badge
 * Shows when content is from cache
 */
export function CachedContentBadge() {
  return (
    <Badge variant="secondary" className="ml-2">
      <span className="mr-1">📦</span>
      Cached Content
    </Badge>
  );
}

/**
 * Hook to detect if response is from cache
 */
export function useIsCached(response: Response | null): boolean {
  if (!response) return false;
  return response.headers.get('X-From-Cache') === 'true';
}
