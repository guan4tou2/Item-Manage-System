"use client"

import { ScanLine } from "lucide-react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { useTranslations } from "next-intl"

/**
 * 行動版掃描 FAB（§5.7）：僅 `md` 以下顯示，避開底部安全區；
 * 已在 `/scan` 頁時不顯示（避免指向當前頁）。
 */
export function ScanFab() {
  const t = useTranslations()
  const pathname = usePathname()
  if (pathname === "/scan") return null

  return (
    <Link
      href={"/scan" as never}
      aria-label={t("scan.fabAria")}
      className="fixed right-4 bottom-[calc(1rem+env(safe-area-inset-bottom))] z-40 grid h-14 w-14 place-items-center rounded-full bg-primary text-primary-foreground shadow-lg transition-colors hover:bg-primary/90 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 md:hidden"
    >
      <ScanLine className="h-6 w-6" />
    </Link>
  )
}
