import { ApiError, NetworkError } from "@/lib/api/client"
import { submitItem } from "./submission"
import type { OfflineStorage, PendingItem } from "./storage"

export function shouldQueue(error: unknown, online: boolean): boolean {
  return !(error instanceof ApiError) && (!online || error instanceof NetworkError)
}

export function failureCode(error: ApiError): string {
  const body = error.body as { detail?: unknown; code?: string } | null
  const detail = body?.detail
  if (typeof detail === "string" && detail.includes("location_id")) return "location"
  if (typeof detail === "string" && detail.includes("category_id")) return "category"
  return (detail as { code?: string } | null)?.code ?? body?.code ?? String(error.status)
}

export class OfflineQueue {
  private flight: Promise<void> | null = null
  private activeOwner: string | undefined
  constructor(
    public storage: OfflineStorage,
    private changed: () => Promise<void> = async () => {},
    private send = submitItem,
    private canSync: (row: PendingItem) => boolean = () => true,
  ) {}

  async save(item: PendingItem) {
    await this.storage.put(item)
    await this.changed()
  }
  async remove(id: string) {
    await this.storage.remove(id)
    await this.changed()
  }

  sync(
    session: () => { owner: string; token: string } | null,
    report: (result: { synced: number; failed: number; partial: string[] }) => void,
  ): Promise<void> {
    if (this.flight) {
      if (session()?.owner !== this.activeOwner) {
        return this.flight.then(() => this.sync(session, report))
      }
      return this.flight
    }
    this.activeOwner = session()?.owner
    this.flight = this.run(session, report).finally(() => { this.flight = null })
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
      // 上一筆送出期間可能已捨棄或編輯下一筆，不可重放舊快照。
      const row = (await this.storage.list(initial.owner)).find((item) => item.client_id === queued.client_id)
      if (!row) continue
      const auth = session()
      if (!auth || auth.owner !== initial.owner || !navigator.onLine) break
      if (row.status === "failed" || !this.canSync(row)) continue
      // 上次分頁關閉留下的 syncing 也使用原 key 安全重放。
      await this.save({ ...row, status: "syncing" })
      const latest = session()
      if (!latest || latest.owner !== initial.owner || !this.canSync(row)) {
        await this.save({ ...row, status: "pending" })
        break
      }
      try {
        const outcome = await this.send(row, row.client_id, auth.token)
        await this.remove(row.client_id)
        result.synced++
        if (outcome.partial) result.partial.push(outcome.item.id)
      } catch (error) {
        const next = { ...row, status: "pending" as PendingItem["status"] }
        if (error instanceof ApiError) {
          if (error.status === 401) {
            await this.save(next)
            break
          }
          if (error.status >= 500) {
            next.attempts++
            next.error_code = "server"
            if (next.attempts >= 5) next.status = "failed"
          } else {
            next.status = "failed"
            next.error_code = failureCode(error)
          }
        } else if (!(error instanceof NetworkError)) {
          next.status = "failed"
          next.error_code = "unknown"
        }
        await this.save(next)
        if (next.status === "failed" || (error instanceof ApiError && error.status >= 500)) result.failed++
        // 網路中斷不繼續轟炸下一筆。
        if (error instanceof NetworkError) break
      }
    }
    if (session()?.owner === initial.owner) report(result)
  }
}
