"use client"

import type { Route } from "next"
import { usePathname, useRouter } from "next/navigation"
import { useTranslations } from "next-intl"
import { Menu } from "lucide-react"
import { useCallback, useState } from "react"

import { Button } from "@/components/ui/button"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"

import { NavGroup } from "./nav-group"
import { NAV_GROUPS } from "./nav-items"

export function MobileNav() {
  const t = useTranslations()
  const router = useRouter()
  const pathname = usePathname()
  const [open, setOpen] = useState(false)

  const onSelect = useCallback(
    (href: Route) => {
      setOpen(false)
      router.push(href)
    },
    [router],
  )

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="lg:hidden"
          aria-label={t("a11y.openMenu")}
        >
          <Menu className="h-5 w-5" />
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-64" closeLabel={t("a11y.closeMenu")}>
        <SheetHeader>
          <SheetTitle>{t("appName")}</SheetTitle>
          <SheetDescription className="sr-only">
            {t("a11y.mobileNavigationDescription")}
          </SheetDescription>
        </SheetHeader>
        <nav className="mt-6 flex flex-col gap-4">
          {NAV_GROUPS.map((group) => (
            <NavGroup
              key={group.id}
              group={group}
              pathname={pathname}
              onSelect={onSelect}
            />
          ))}
        </nav>
      </SheetContent>
    </Sheet>
  )
}
