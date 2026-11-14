"use client"

import type { Route } from "next"
import { useTranslations } from "next-intl"
import { ChevronDown } from "lucide-react"
import { useState } from "react"

import { PendingBadge } from "@/components/offline/offline-status"
import { cn } from "@/lib/utils"

import type { NavGroup as NavGroupDef } from "./nav-items"

interface Props {
  group: NavGroupDef
  /** 目前路徑，用於 active 樣式。 */
  pathname: string
  onSelect: (href: Route) => void
}

/** 行動 drawer 的二層群組（D8）：群組標題可收合，預設展開。 */
export function NavGroup({ group, pathname, onSelect }: Props) {
  const t = useTranslations()
  const [expanded, setExpanded] = useState(true)

  return (
    <div>
      <button
        type="button"
        data-testid={`nav-group-header-${group.id}`}
        aria-expanded={expanded}
        onClick={() => setExpanded((value) => !value)}
        className="text-muted-foreground hover:bg-accent/50 flex w-full items-center justify-between rounded-md px-3 py-2 text-xs font-semibold tracking-wide uppercase"
      >
        {t(group.labelKey as never)}
        <ChevronDown
          className={cn(
            "h-4 w-4 transition-transform",
            !expanded && "-rotate-90",
          )}
          aria-hidden="true"
        />
      </button>
      {expanded && (
        <div
          data-testid={`nav-group-items-${group.id}`}
          className="mt-1 flex flex-col gap-1"
        >
          {group.items.map((item) => {
            const active = pathname.startsWith(item.href)
            return (
              <button
                key={item.key}
                type="button"
                onClick={() => onSelect(item.href)}
                className={cn(
                  "rounded-md px-3 py-2 text-left text-sm",
                  active
                    ? "bg-accent text-accent-foreground"
                    : "hover:bg-accent hover:text-accent-foreground",
                )}
              >
                {t(item.labelKey as never)}{item.key === "items" && <PendingBadge />}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
