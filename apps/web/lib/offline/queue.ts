import { API_BASE, apiFetch, ApiError, NetworkError } from "@/lib/api/client"
import { executeItem, applyResult, type OfflineStep } from "./engine"
import { buildSteps, mergePending } from "./steps"
import { registerOfflineSync } from "./background"
import type { OfflineStorage, PendingItem } from "./storage"
export { failureCode } from "./engine"

export function shouldQueue(error: unknown, online: boolean): boolean {
  return !(error instanceof ApiError) && (!online || error instanceof NetworkError)
}
export async function requestStep(step: OfflineStep, token: string) {
  try {
    const response = await apiFetch(step.path, {
      method: step.method, headers: step.headers,
      body: step.body === undefined ? undefined : JSON.stringify(step.body), accessToken: token,
    })
    return { status: response.status, body: await response.json().catch(() => null) }
  } catch (error) {
    if (error instanceof ApiError) return { status: error.status, body: error.body }
    throw error
  }
}

export class OfflineQueue {
  private flight: Promise<void> | null = null
  private activeOwner: string | undefined
  constructor(
    public storage: OfflineStorage,
    private changed: () => Promise<void> = async () => {},
    private request = requestStep,
    private canSync: (row: PendingItem) => boolean = () => true,
  ) {}

  async save(item: PendingItem) {
    const merged = mergePending(item, await this.storage.list(item.owner_user_id))
    await this.persist({ ...merged, kind: merged.kind ?? "create",
      api_base: merged.api_base ?? new URL(API_BASE, location.origin).href.replace(/\/$/, ""),
      steps: buildSteps(merged),
    })
    void registerOfflineSync()
  }
  private async persist(item: PendingItem) {
    await this.storage.put(item)
    await this.changed()
  }
  async remove(id: string) {
    await this.storage.remove(id)
    await this.changed()
  }
  /** Explicit conflict resolution replaces the base version, bypassing D7. */
  async resolveConflict(row: PendingItem) {
    const version = (row.server as { updated_at?: unknown } | null)?.updated_at
    if (typeof version !== "string") return
    const next: PendingItem = { ...row, base_updated_at: version, status: "pending", error_code: null, attempts: 0, server: undefined }
    next.steps = buildSteps(next)
    await this.persist(next)
    void registerOfflineSync()
  }

  sync(
    session: () => { owner: string; token: string } | null,
    report: (result: { synced: number; failed: number; partial: string[] }) => void,
  ): Promise<void> {
    if (this.flight) {
      if (session()?.owner !== this.activeOwner) return this.flight.then(() => this.sync(session, report))
      return this.flight
    }
    this.activeOwner = session()?.owner
    const run = () => this.run(session, report)
    this.flight = (navigator.locks
      ? navigator.locks.request("ims-offline-sync", { ifAvailable: true }, (lock) => lock ? run() : Promise.resolve())
      : run()).finally(() => { this.flight = null })
    return this.flight
  }

  private async run(
    session: () => { owner: string; token: string } | null,
    report: (result: { synced: number; failed: number; partial: string[] }) => void,
  ) {
    const initial = session()
    if (!initial || !navigator.onLine) return
    const rows = await this.storage.list(initial.owner)
    const result = { synced: 0, failed: 0, partial: [] as string[] }
    for (const queued of rows) {
      const row = (await this.storage.list(initial.owner)).find((item) => item.client_id === queued.client_id)
      if (!row) continue
      const auth = session()
      if (!auth || auth.owner !== initial.owner || !navigator.onLine) break
      if (!["pending", "syncing"].includes(row.status) || !this.canSync(row)) continue
      // Legacy records receive steps on the page; the worker skips them.
      const prepared = { ...row, kind: row.kind ?? "create", steps: row.steps ?? buildSteps(row),
        api_base: row.api_base ?? new URL(API_BASE, location.origin).href.replace(/\/$/, ""),
        status: "syncing" as const }
      await this.persist(prepared)
      const latest = session()
      if (!latest || latest.owner !== initial.owner || !this.canSync(row)) {
        await this.persist({ ...prepared, status: "pending" })
        break
      }
      const outcome = await executeItem(prepared, (step) => this.request(step, latest.token))
      const next = applyResult(prepared, outcome)
      if (next) {
        await this.persist(next)
        if (["failed", "conflict", "server"].includes(outcome.type)) result.failed++
      } else {
        await this.remove(row.client_id)
        result.synced++
        if (outcome.type === "partial" && outcome.item_id) result.partial.push(outcome.item_id)
      }
      if (outcome.type === "network" || outcome.type === "unauthorized" || (outcome.type === "partial" && outcome.network)) break
    }
    if (session()?.owner === initial.owner) report(result)
  }
}
