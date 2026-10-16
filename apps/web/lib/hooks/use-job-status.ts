"use client"

import { useQuery } from "@tanstack/react-query"

import * as api from "@/lib/api/jobs"
import { useAccessToken } from "@/lib/auth/use-auth"
import { STALE_TIME } from "./constants"

export function useJobStatus(jobName: string) {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["job-status", jobName],
    queryFn: () => api.getJobStatus(jobName, token),
    enabled: token !== null,
    staleTime: STALE_TIME,
  })
}
