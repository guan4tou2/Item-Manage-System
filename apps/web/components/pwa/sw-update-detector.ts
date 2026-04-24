/**
 * Wire a ServiceWorkerRegistration so that consumers get notified when a new
 * service worker is ready to take over.
 *
 * The SW never calls `skipWaiting()` on its own (see `public/sw.js`), so the
 * update flow is:
 *
 *   1. Browser fetches `/sw.js`, sees new byte content, installs it.
 *   2. New SW enters "waiting" state.
 *   3. This detector fires `onUpdateReady(waitingWorker)`.
 *   4. Caller shows a prompt; on accept, calls `applyUpdate(waitingWorker)`.
 *   5. Detector sees `controllerchange` and calls `onControllerChange()`.
 *   6. Caller reloads the page.
 *
 * Extracted as a pure function so we can unit-test the branching without
 * spinning up a real ServiceWorker.
 */

export interface UpdateDetectorOptions {
  onUpdateReady: (waiting: ServiceWorker) => void
  onControllerChange: () => void
}

/**
 * Wire update-ready + controllerchange handlers onto a registration.
 * Returns a cleanup function that detaches listeners.
 */
export function wireUpdateDetector(
  registration: ServiceWorkerRegistration,
  container: ServiceWorkerContainer,
  opts: UpdateDetectorOptions,
): () => void {
  // Case A: a worker is already waiting when we register (tab was opened
  // after the SW updated in a prior session).
  if (registration.waiting && container.controller) {
    opts.onUpdateReady(registration.waiting)
  }

  const onUpdateFound = () => {
    const installing = registration.installing
    if (!installing) return

    // Case B: a new worker starts installing while we're open. Watch for
    // its statechange to "installed" and ensure there's already a
    // controller (otherwise this is first install, not an update).
    const onStateChange = () => {
      if (installing.state === "installed" && container.controller) {
        opts.onUpdateReady(installing)
        installing.removeEventListener("statechange", onStateChange)
      }
    }
    installing.addEventListener("statechange", onStateChange)
  }

  registration.addEventListener("updatefound", onUpdateFound)

  const onControllerChange = () => {
    opts.onControllerChange()
  }
  container.addEventListener("controllerchange", onControllerChange)

  return () => {
    registration.removeEventListener("updatefound", onUpdateFound)
    container.removeEventListener("controllerchange", onControllerChange)
  }
}

/**
 * Trigger activation of a waiting worker. The SW will reply by taking over,
 * which will fire `controllerchange` on the container.
 */
export function applyUpdate(waiting: ServiceWorker): void {
  waiting.postMessage({ type: "SKIP_WAITING" })
}
