"use client"

import { Luggage, ShoppingCart, Star, List as ListIcon, type LucideIcon } from "lucide-react"
import { useTranslations } from "next-intl"

import { Badge } from "@/components/ui/badge"
import type { ListKind } from "@/lib/api/lists"

const ICONS: Record<ListKind, LucideIcon> = {
  travel: Luggage,
  shopping: ShoppingCart,
  collection: Star,
  generic: ListIcon,
}

interface Props {
  kind: ListKind
}

export function KindBadge({ kind }: Props) {
  const t = useTranslations()
  const Icon = ICONS[kind]
  return (
    <Badge variant="secondary" className="gap-1">
      <Icon className="h-3.5 w-3.5" aria-hidden />
      {t(`lists.kind.${kind}`)}
    </Badge>
  )
}
