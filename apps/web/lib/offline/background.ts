/** Unsupported browsers and registration failures keep foreground sync working. */
export async function registerOfflineSync() {
  try {
    if (!("serviceWorker" in navigator)) return
    const registration = await navigator.serviceWorker.getRegistration()
    const sync = (registration as (ServiceWorkerRegistration & { sync?: { register(tag: string): Promise<void> } }) | undefined)?.sync
    if (sync) await sync.register("ims-offline-sync")
  } catch { /* best effort */ }
}
