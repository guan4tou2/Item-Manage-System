"use client"

import type { Route } from "next"
import { useRouter } from "next/navigation"
import { useTranslations } from "next-intl"
import { Menu } from "lucide-react"
import { useCallback, useState } from "react"

import { Button } from "@/components/ui/button"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"

import { NAV_ITEMS } from "./nav-items"

export function MobileNav() {
  const t = useTranslations()
  const router = useRouter()
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
          className="md:hidden"
          aria-label={t("a11y.openMenu")}
        >
          <Menu className="h-5 w-5" />
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-64">
        <SheetHeader>
          <SheetTitle>{t("appName")}</SheetTitle>
        </SheetHeader>
        <nav className="mt-6 flex flex-col gap-1">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.key}
              type="button"
              onClick={() => onSelect(item.href)}
              className="rounded-md px-3 py-2 text-left text-sm hover:bg-accent hover:text-accent-foreground"
            >
              {t(item.labelKey as never)}
            </button>
          ))}
        </nav>
      </SheetContent>
    </Sheet>
  )
}
