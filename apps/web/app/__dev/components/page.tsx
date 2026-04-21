import { notFound } from "next/navigation"

import { DevThemeToggle } from "./dev-theme-toggle"
import { FeedbackSection } from "./sections/feedback"
import { FormsSection } from "./sections/forms"
import { OverlaysSection } from "./sections/overlays"

export const dynamic = "force-dynamic"

export default function ComponentsShowcasePage() {
  if (
    process.env.NODE_ENV === "production" &&
    process.env.NEXT_PUBLIC_ENABLE_DEV_ROUTES !== "1"
  ) {
    notFound()
  }
  return (
    <main className="mx-auto w-full max-w-5xl space-y-12 px-6 py-10">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">UI 元件展示</h1>
          <p className="text-sm text-muted-foreground">
            開發模式專屬頁面；生產環境預設 404。
          </p>
        </div>
        <DevThemeToggle />
      </header>
      <FormsSection />
      <OverlaysSection />
      <FeedbackSection />
    </main>
  )
}
