"use client"

import { useRouter } from "next/navigation"
import { useEffect, type ReactNode } from "react"

import { useAccessToken } from "@/lib/auth/use-auth"
import { Skeleton } from "@/components/ui/skeleton"

export default function AppLayout({ children }: { children: ReactNode }) {
  const token = useAccessToken()
  const router = useRouter()

  useEffect(() => {
    // Second-layer guard: if token clears during SPA navigation, redirect
    if (token === null) {
      router.replace("/login")
    }
  }, [token, router])

  if (!token) {
    return (
      <main className="flex min-h-screen items-center justify-center p-6">
        <Skeleton className="h-32 w-full max-w-md" />
      </main>
    )
  }

  // Note: AppShell will replace this wrapper in Task 16
  return <div className="min-h-screen">{children}</div>
}
