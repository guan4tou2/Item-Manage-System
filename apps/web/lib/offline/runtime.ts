"use client"

import { useEffect, useState } from "react"
import { create } from "zustand"
import { useAuthStore } from "@/lib/auth/auth-store"
import { OfflineQueue } from "./queue"
import { IndexedDBStorage, OfflineStorageError, type PendingItem } from "./storage"

export const useOfflineState = create<{
  rows: PendingItem[]
  error: "unavailable" | "quota" | null
}>()(() => ({ rows: [], error: null }))

export function currentSession() {
  const { user, accessToken } = useAuthStore.getState()
  return user && accessToken ? { owner: user.id, token: accessToken } : null
}

export async function refreshOffline() {
  const owner = currentSession()?.owner
  if (!owner) { useOfflineState.setState({ rows: [], error: null }); return }
  try {
    const rows = await offlineQueue.storage.list(owner)
    if (currentSession()?.owner === owner) useOfflineState.setState({ rows, error: null })
  } catch (error) {
    if (currentSession()?.owner !== owner) return
    useOfflineState.setState({ rows: [], error: error instanceof OfflineStorageError ? error.code : "unavailable" })
  }
}

export const offlineQueue = new OfflineQueue(new IndexedDBStorage(), refreshOffline, undefined, (row) => editing?.client_id !== row.client_id)

export function usePendingItems() {
  const owner = useAuthStore((s) => s.user?.id)
  const rows = useOfflineState((s) => s.rows)
  return rows.filter((row) => row.owner_user_id === owner)
}

export function useOnline() {
  const [online, setOnline] = useState(true)
  useEffect(() => {
    const update = () => setOnline(navigator.onLine)
    update()
    window.addEventListener("online", update)
    window.addEventListener("offline", update)
    return () => {
      window.removeEventListener("online", update)
      window.removeEventListener("offline", update)
    }
  }, [])
  return online
}

// 編輯草稿只留在記憶體，不將物品內容放進 URL。
let editing: PendingItem | null = null
export function editPending(item: PendingItem) { editing = item }
export function getEditingPending(owner?: string) {
  return editing?.owner_user_id === owner ? editing : null
}
export function clearEditingPending() { editing = null }
