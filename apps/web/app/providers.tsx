"use client"

import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { usePathname } from "next/navigation"
import { ThemeProvider } from "next-themes"
import { useState, type ReactNode } from "react"

import { useTokenCookieSync } from "@/lib/auth/cookie-sync"
import { ApiError } from "@/lib/api/client"
import { Toaster } from "@/components/ui/sonner"
import { LocaleSync } from "@/lib/locale/locale-sync"
import { ThemeSync } from "@/lib/theme/theme-sync"

function GlobalSyncers() {
  useTokenCookieSync()
  return null
}

export function Providers({ children }: { children: ReactNode }) {
  const pathname = usePathname()
  const isPublicShare = pathname === "/share"
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60_000,
            refetchOnWindowFocus: false,
            // 4xx（404/401/403…）是確定性結果，重試只會延後錯誤 UI
            // （例如「找不到此物品」預設要等約 7 秒重試完才顯示）。
            retry: (failureCount, error) => {
              if (error instanceof ApiError && error.status < 500) return false
              return failureCount < 2
            },
          },
        },
      }),
  )

  return (
    <QueryClientProvider client={client}>
      <ThemeProvider
        attribute="class"
        defaultTheme="system"
        enableSystem
        disableTransitionOnChange
      >
        {!isPublicShare && <>
          <GlobalSyncers />
          <ThemeSync />
          <LocaleSync />
        </>}
        {children}
        <Toaster richColors closeButton />
      </ThemeProvider>
    </QueryClientProvider>
  )
}
