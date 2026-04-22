"use client"

import { useQuery } from "@tanstack/react-query"

import * as api from "@/lib/api/tags"
import { useAccessToken } from "@/lib/auth/use-auth"

export function useTags(q: string | undefined = undefined) {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["tags", q ?? ""],
    queryFn: () => api.listTags(q, token),
    enabled: token !== null,
  })
}
