"use client"

import { useQuery } from "@tanstack/react-query"

import * as api from "@/lib/api/barcodes"
import { useAccessToken } from "@/lib/auth/use-auth"

const LOOKUP_STALE_TIME = 5 * 60_000

/**
 * 條碼 lookup（內查＋外查）。`code` 為 canonical 條碼字串；
 * server 端快取 30 天為權威，此處短 staleTime 僅避免畫面內重複請求。
 */
export function useBarcodeLookup(code: string | null) {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["barcode-lookup", code],
    queryFn: () => api.lookupBarcode(code as string, token),
    enabled: token !== null && !!code,
    retry: false,
    staleTime: LOOKUP_STALE_TIME,
  })
}
