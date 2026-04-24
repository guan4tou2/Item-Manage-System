"use client"

import { useEffect, useState } from "react"
import { useQuery } from "@tanstack/react-query"

import * as api from "@/lib/api/labels"
import { useAccessToken } from "@/lib/auth/use-auth"

export function useItemLabel(itemId: string) {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["label", itemId],
    queryFn: () => api.getItemLabel(itemId, token),
    enabled: token !== null && !!itemId,
    staleTime: 60_000,
  })
}

export function useItemQrObjectUrl(itemId: string): string | null {
  const token = useAccessToken()
  const [url, setUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!itemId || token === null) return
    let active = true
    let created: string | null = null
    api
      .getItemQrBlob(itemId, token)
      .then((blob) => {
        if (!active) return
        created = URL.createObjectURL(blob)
        setUrl(created)
      })
      .catch(() => {
        if (active) setUrl(null)
      })
    return () => {
      active = false
      if (created) URL.revokeObjectURL(created)
    }
  }, [itemId, token])

  return url
}
