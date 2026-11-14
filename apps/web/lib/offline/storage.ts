import type { ItemSubmission } from "./submission"

export interface PendingItem extends ItemSubmission {
  client_id: string
  owner_user_id: string
  created_at: string
  status: "pending" | "syncing" | "failed"
  error_code: string | null
  attempts: number
}

/** 僅以完整紀錄讀寫；測試可注入記憶體實作。 */
export interface OfflineStorage {
  list(owner: string): Promise<PendingItem[]>
  put(item: PendingItem): Promise<void>
  remove(id: string): Promise<void>
}

export class OfflineStorageError extends Error {
  constructor(public code: "unavailable" | "quota") { super(code) }
}

function storageError(error: unknown): OfflineStorageError {
  return new OfflineStorageError(
    (error as { name?: string })?.name === "QuotaExceededError" ? "quota" : "unavailable",
  )
}

export class IndexedDBStorage implements OfflineStorage {
  private async open(): Promise<IDBDatabase> {
    try {
      return await new Promise((resolve, reject) => {
        const request = indexedDB.open("ims-offline", 1)
        request.onupgradeneeded = () => {
          request.result.createObjectStore("pending-items", { keyPath: "client_id" })
        }
        request.onsuccess = () => resolve(request.result)
        request.onerror = () => reject(request.error)
        request.onblocked = () => reject(new Error("blocked"))
      })
    } catch (error) { throw storageError(error) }
  }

  private async run<T>(mode: IDBTransactionMode, action: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
    const db = await this.open()
    try {
      return await new Promise<T>((resolve, reject) => {
        const tx = db.transaction("pending-items", mode)
        const request = action(tx.objectStore("pending-items"))
        tx.oncomplete = () => resolve(request.result)
        tx.onabort = () => reject(tx.error ?? request.error)
        tx.onerror = () => reject(tx.error ?? request.error)
      })
    } catch (error) { throw storageError(error) }
    finally { db.close() }
  }

  async list(owner: string) {
    const rows = await this.run<PendingItem[]>("readonly", (store) => store.getAll())
    return rows.filter((row) => row.owner_user_id === owner)
      .sort((a, b) => a.created_at.localeCompare(b.created_at))
  }
  async put(item: PendingItem) { await this.run("readwrite", (store) => store.put(item)) }
  async remove(id: string) { await this.run("readwrite", (store) => store.delete(id)) }
}
