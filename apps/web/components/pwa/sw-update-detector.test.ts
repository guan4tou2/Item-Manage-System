import { describe, expect, it, vi } from "vitest"

import { applyUpdate, wireUpdateDetector } from "./sw-update-detector"

type Listener = (ev?: unknown) => void

function makeFakeWorker(initialState = "installing") {
  const listeners = new Map<string, Set<Listener>>()
  const worker = {
    state: initialState,
    postMessage: vi.fn(),
    addEventListener: vi.fn((type: string, fn: Listener) => {
      if (!listeners.has(type)) listeners.set(type, new Set())
      listeners.get(type)!.add(fn)
    }),
    removeEventListener: vi.fn((type: string, fn: Listener) => {
      listeners.get(type)?.delete(fn)
    }),
    dispatch(type: string) {
      listeners.get(type)?.forEach((fn) => fn())
    },
    setState(state: string) {
      worker.state = state
    },
  }
  return worker
}

function makeFakeRegistration(opts: {
  waiting?: ReturnType<typeof makeFakeWorker> | null
  installing?: ReturnType<typeof makeFakeWorker> | null
}) {
  const listeners = new Map<string, Set<Listener>>()
  return {
    waiting: opts.waiting ?? null,
    installing: opts.installing ?? null,
    addEventListener: vi.fn((type: string, fn: Listener) => {
      if (!listeners.has(type)) listeners.set(type, new Set())
      listeners.get(type)!.add(fn)
    }),
    removeEventListener: vi.fn((type: string, fn: Listener) => {
      listeners.get(type)?.delete(fn)
    }),
    dispatch(type: string) {
      listeners.get(type)?.forEach((fn) => fn())
    },
  }
}

function makeFakeContainer(hasController: boolean) {
  const listeners = new Map<string, Set<Listener>>()
  return {
    controller: hasController ? ({} as ServiceWorker) : null,
    addEventListener: vi.fn((type: string, fn: Listener) => {
      if (!listeners.has(type)) listeners.set(type, new Set())
      listeners.get(type)!.add(fn)
    }),
    removeEventListener: vi.fn((type: string, fn: Listener) => {
      listeners.get(type)?.delete(fn)
    }),
    dispatch(type: string) {
      listeners.get(type)?.forEach((fn) => fn())
    },
  }
}

describe("wireUpdateDetector", () => {
  it("fires onUpdateReady immediately when a waiting SW is already present", () => {
    const waiting = makeFakeWorker("installed")
    const reg = makeFakeRegistration({ waiting })
    const container = makeFakeContainer(true)
    const onUpdateReady = vi.fn()
    const onControllerChange = vi.fn()

    wireUpdateDetector(
      reg as unknown as ServiceWorkerRegistration,
      container as unknown as ServiceWorkerContainer,
      { onUpdateReady, onControllerChange },
    )

    expect(onUpdateReady).toHaveBeenCalledTimes(1)
    expect(onUpdateReady).toHaveBeenCalledWith(waiting)
  })

  it("does not fire onUpdateReady on first install (no controller yet)", () => {
    const waiting = makeFakeWorker("installed")
    const reg = makeFakeRegistration({ waiting })
    const container = makeFakeContainer(false)
    const onUpdateReady = vi.fn()
    const onControllerChange = vi.fn()

    wireUpdateDetector(
      reg as unknown as ServiceWorkerRegistration,
      container as unknown as ServiceWorkerContainer,
      { onUpdateReady, onControllerChange },
    )

    expect(onUpdateReady).not.toHaveBeenCalled()
  })

  it("fires onUpdateReady after updatefound + statechange → installed", () => {
    const installing = makeFakeWorker("installing")
    const reg = makeFakeRegistration({ installing })
    const container = makeFakeContainer(true)
    const onUpdateReady = vi.fn()

    wireUpdateDetector(
      reg as unknown as ServiceWorkerRegistration,
      container as unknown as ServiceWorkerContainer,
      { onUpdateReady, onControllerChange: vi.fn() },
    )

    // Simulate updatefound → SW reaches "installed"
    reg.dispatch("updatefound")
    installing.setState("installed")
    installing.dispatch("statechange")

    expect(onUpdateReady).toHaveBeenCalledTimes(1)
    expect(onUpdateReady).toHaveBeenCalledWith(installing)
  })

  it("does not re-fire onUpdateReady on every statechange", () => {
    const installing = makeFakeWorker("installing")
    const reg = makeFakeRegistration({ installing })
    const container = makeFakeContainer(true)
    const onUpdateReady = vi.fn()

    wireUpdateDetector(
      reg as unknown as ServiceWorkerRegistration,
      container as unknown as ServiceWorkerContainer,
      { onUpdateReady, onControllerChange: vi.fn() },
    )

    reg.dispatch("updatefound")
    installing.setState("installed")
    installing.dispatch("statechange")
    // Later events (e.g. "activated") should not re-fire
    installing.setState("activated")
    installing.dispatch("statechange")
    installing.setState("redundant")
    installing.dispatch("statechange")

    expect(onUpdateReady).toHaveBeenCalledTimes(1)
  })

  it("fires onControllerChange when container emits controllerchange", () => {
    const reg = makeFakeRegistration({})
    const container = makeFakeContainer(true)
    const onControllerChange = vi.fn()

    wireUpdateDetector(
      reg as unknown as ServiceWorkerRegistration,
      container as unknown as ServiceWorkerContainer,
      { onUpdateReady: vi.fn(), onControllerChange },
    )
    container.dispatch("controllerchange")

    expect(onControllerChange).toHaveBeenCalledTimes(1)
  })

  it("cleanup function detaches both listeners", () => {
    const reg = makeFakeRegistration({})
    const container = makeFakeContainer(true)

    const cleanup = wireUpdateDetector(
      reg as unknown as ServiceWorkerRegistration,
      container as unknown as ServiceWorkerContainer,
      { onUpdateReady: vi.fn(), onControllerChange: vi.fn() },
    )
    cleanup()

    expect(reg.removeEventListener).toHaveBeenCalledWith(
      "updatefound",
      expect.any(Function),
    )
    expect(container.removeEventListener).toHaveBeenCalledWith(
      "controllerchange",
      expect.any(Function),
    )
  })
})

describe("applyUpdate", () => {
  it("posts a SKIP_WAITING message to the waiting SW", () => {
    const waiting = makeFakeWorker("installed")
    applyUpdate(waiting as unknown as ServiceWorker)
    expect(waiting.postMessage).toHaveBeenCalledWith({ type: "SKIP_WAITING" })
  })
})
