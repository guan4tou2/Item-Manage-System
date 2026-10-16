"use client"

import { useTranslations } from "next-intl"
import { useState } from "react"

import { LocationSelect } from "@/components/locations/location-select"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import type { TreeFlatNode } from "@/lib/locations/tree"

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  node: TreeFlatNode | null
  itemCount: number
  childCount: number
  /** 把該節點的直接物品搬到目標節點（重用 items bulk 端點）。 */
  onMoveItems?: (targetId: number) => void
  /** 展開並聚焦第一個子節點。 */
  onFocusFirstChild?: () => void
  onDelete: () => void
  pending?: boolean
  movingItems?: boolean
}

/**
 * 刪除限制對話框（§5.4）：顯示「此位置有 N 件物品」／子節點數，
 * 提供「先搬移物品」（搬移對話框）與「先處理子節點」。
 */
export function LocationDeleteDialog({
  open,
  onOpenChange,
  node,
  itemCount,
  childCount,
  onMoveItems,
  onFocusFirstChild,
  onDelete,
  pending = false,
  movingItems = false,
}: Props) {
  const t = useTranslations()
  const [target, setTarget] = useState<number | null>(null)
  const blocked = itemCount > 0 || childCount > 0

  if (!node) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("locations.delete.title", { name: node.name })}</DialogTitle>
          <DialogDescription>
            {itemCount > 0
              ? t("locations.delete.itemsBody", { count: itemCount })
              : null}
            {itemCount > 0 && childCount > 0 ? " " : null}
            {childCount > 0
              ? t("locations.delete.childrenBody", { count: childCount })
              : null}
            {!blocked ? t("locations.delete.confirm") : null}
          </DialogDescription>
        </DialogHeader>

        {itemCount > 0 ? (
          <div className="space-y-2 rounded-md border p-3">
            <p className="text-sm font-medium">{t("locations.delete.moveFirst")}</p>
            <LocationSelect
              value={target}
              onChange={setTarget}
              allowNone={false}
              label={t("locations.delete.targetLabel")}
              testId="delete-move-target"
            />
            <Button
              type="button"
              size="sm"
              disabled={target === null || movingItems}
              onClick={() => {
                if (target !== null && onMoveItems) onMoveItems(target)
              }}
            >
              {t("locations.delete.moveItems", { count: itemCount })}
            </Button>
          </div>
        ) : null}

        {childCount > 0 && onFocusFirstChild ? (
          <Button type="button" variant="outline" size="sm" onClick={onFocusFirstChild}>
            {t("locations.delete.handleChildren")}
          </Button>
        ) : null}

        <DialogFooter>
          <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
            {t("items.form.cancel")}
          </Button>
          <Button
            type="button"
            variant="destructive"
            disabled={blocked || pending}
            onClick={onDelete}
          >
            {t("locations.tree.delete")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
