import type { ReactNode } from "react"

import { AppHeader } from "./app-header"
import { ScanFab } from "./scan-fab"

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <AppHeader />
      <main className="flex-1">{children}</main>
      <ScanFab />
    </div>
  )
}
