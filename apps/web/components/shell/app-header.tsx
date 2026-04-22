"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useTranslations } from "next-intl"

import { cn } from "@/lib/utils"

import { MobileNav } from "./mobile-nav"
import { NAV_ITEMS } from "./nav-items"
import { UserMenu } from "./user-menu"

export function AppHeader() {
  const t = useTranslations()
  const pathname = usePathname()

  return (
    <header className="sticky top-0 z-40 flex h-14 items-center gap-4 border-b bg-background px-4 md:px-6">
      <MobileNav />
      <Link
        href="/dashboard"
        className="flex items-center font-semibold tracking-tight"
      >
        {t("appName")}
      </Link>
      <nav className="ml-6 hidden items-center gap-1 md:flex">
        {NAV_ITEMS.map((item) => {
          const active = pathname.startsWith(item.href)
          return (
            <Link
              key={item.key}
              href={item.href}
              className={cn(
                "rounded-md px-3 py-1.5 text-sm transition-colors",
                active
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
              )}
            >
              {t(item.labelKey as never)}
            </Link>
          )
        })}
      </nav>
      <div className="ml-auto flex items-center gap-2">
        <UserMenu />
      </div>
    </header>
  )
}
