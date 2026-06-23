"use client"

import { useRouter } from "next/navigation"
import { useEffect, useState, type ReactNode } from "react"

import { AppShell } from "@/components/shell/app-shell"
import { Skeleton } from "@/components/ui/skeleton"
import { useAuthStore } from "@/lib/auth/auth-store"
import { useAccessToken } from "@/lib/auth/use-auth"

export default function AppLayout({ children }: { children: ReactNode }) {
  const token = useAccessToken()
  const router = useRouter()
  const [hydrated, setHydrated] = useState(false)

  useEffect(() => {
    const persistApi = useAuthStore.persist
    if (!persistApi || persistApi.hasHydrated()) {
      setHydrated(true)
      return
    }
    return persistApi.onFinishHydration(() => setHydrated(true))
  }, [])

  useEffect(() => {
    // Second-layer guard: once persist finishes, if we still have no token,
    // redirect. Only runs post-hydration so cold loads with a valid cookie
    // aren't bounced to /login.
    if (hydrated && token === null) {
      router.replace("/login")
    }
  }, [hydrated, token, router])

  if (!hydrated || !token) {
    return (
      <main className="flex min-h-screen items-center justify-center p-6">
        <Skeleton className="h-32 w-full max-w-md" />
      </main>
    )
  }

  return <AppShell>{children}</AppShell>
}
