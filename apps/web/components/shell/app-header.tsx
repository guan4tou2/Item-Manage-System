"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useTranslations } from "next-intl"
import { ChevronDown } from "lucide-react"

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { cn } from "@/lib/utils"

import { InstallPwaButton } from "@/components/pwa/install-pwa-button"

import { MobileNav } from "./mobile-nav"
import { NAV_ITEMS, STATS_MENU_ITEMS } from "./nav-items"
import { NotificationBell } from "./notification-bell"
import { UserMenu } from "./user-menu"

/** 桌面「統計」第二層下拉（D8）；/statistics 與 /reports 皆視為 active。 */
function StatsMenu() {
  const t = useTranslations()
  const pathname = usePathname()
  const active = STATS_MENU_ITEMS.some((item) => pathname.startsWith(item.href))

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className={cn(
          "flex items-center gap-1 rounded-md px-3 py-1.5 text-sm transition-colors",
          active
            ? "bg-accent text-accent-foreground"
            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
        )}
      >
        {t("nav.statistics")}
        <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start">
        {STATS_MENU_ITEMS.map((item) => (
          <DropdownMenuItem key={item.key} asChild>
            <Link href={item.href}>{t(item.labelKey as never)}</Link>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

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
      <nav className="ml-6 hidden min-w-0 items-center gap-1 overflow-x-auto lg:flex">
        {NAV_ITEMS.map((item) => {
          if (item.key === "statistics") {
            return <StatsMenu key={item.key} />
          }
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
        <InstallPwaButton />
        <NotificationBell />
        <UserMenu />
      </div>
    </header>
  )
}
