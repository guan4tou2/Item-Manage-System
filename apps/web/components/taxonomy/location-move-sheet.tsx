"use client"

import { Search } from "lucide-react"
import { useTranslations } from "next-intl"
import { useMemo, useState } from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { canMove, searchNodes, type TreeFlatNode } from "@/lib/locations/tree"

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  node: TreeFlatNode | null
  flat: TreeFlatNode[]
  onConfirm: (parentId: number | null) => void
  pending?: boolean
}

/** 行動版搬移：bottom sheet ＋ 扁平搜尋（顯示完整路徑）；自身／子孫標示不可選。 */
export function LocationMoveSheet({
  open,
  onOpenChange,
  node,
  flat,
  onConfirm,
  pending = false,
}: Props) {
  const t = useTranslations()
  const [query, setQuery] = useState("")
  const targets = useMemo(() => {
    if (!node) return []
    return searchNodes(flat, query).filter((candidate) => candidate.id !== node.id)
  }, [flat, node, query])

  if (!node) return null

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="bottom" className="max-h-[80vh] overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{t("locations.move.title", { name: node.name })}</SheetTitle>
        </SheetHeader>
        <div className="space-y-3 py-3">
          <div className="relative">
            <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={t("locations.move.searchPlaceholder")}
              aria-label={t("locations.move.searchPlaceholder")}
              className="pl-8"
            />
          </div>
          <ul className="space-y-1">
            {canMove(flat, node.id, null) ? (
              <li>
                <Button
                  type="button"
                  variant="outline"
                  className="w-full justify-start"
                  disabled={pending}
                  onClick={() => onConfirm(null)}
                >
                  {t("locations.move.toRoot")}
                </Button>
              </li>
            ) : null}
            {targets.map((candidate) => {
              const allowed = canMove(flat, node.id, candidate.id)
              return (
                <li key={candidate.id}>
                  <Button
                    type="button"
                    variant="ghost"
                    className="w-full justify-start"
                    disabled={!allowed || pending}
                    aria-disabled={!allowed}
                    title={allowed ? undefined : t("locations.tree.invalidTarget")}
                    onClick={() => onConfirm(candidate.id)}
                  >
                    <span className="truncate">{candidate.path}</span>
                    {!allowed ? (
                      <span className="ml-2 shrink-0 text-xs text-muted-foreground">
                        {t("locations.move.invalid")}
                      </span>
                    ) : null}
                  </Button>
                </li>
              )
            })}
          </ul>
        </div>
      </SheetContent>
    </Sheet>
  )
}
