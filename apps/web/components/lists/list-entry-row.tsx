"use client"

import { X } from "lucide-react"
import { useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { cn } from "@/lib/utils"
import type { ListEntry } from "@/lib/api/lists"

interface Props {
  entry: ListEntry
  onToggle: (id: string) => void
  onDelete: (id: string) => void
  dragHandleProps?: React.HTMLAttributes<HTMLElement>
}

export function ListEntryRow({ entry, onToggle, onDelete, dragHandleProps }: Props) {
  const t = useTranslations()
  return (
    <li
      className={cn(
        "flex items-center gap-3 border-b px-4 py-2",
        entry.is_done && "opacity-60",
      )}
    >
      {dragHandleProps ? (
        <span
          {...dragHandleProps}
          className="cursor-grab select-none text-muted-foreground"
          aria-label="Drag to reorder"
        >
          ⋮⋮
        </span>
      ) : null}
      <Checkbox
        checked={entry.is_done}
        onCheckedChange={() => onToggle(entry.id)}
        aria-label={entry.name}
      />
      <div className="flex-1 space-y-1">
        <div className="flex items-center gap-2">
          <span className={cn("font-medium", entry.is_done && "line-through")}>
            {entry.name}
          </span>
          {entry.quantity !== null ? (
            <span className="text-xs text-muted-foreground">× {entry.quantity}</span>
          ) : null}
          {entry.price !== null ? (
            <span className="text-xs text-muted-foreground">${entry.price}</span>
          ) : null}
        </div>
        {entry.note ? (
          <p className="text-xs text-muted-foreground">{entry.note}</p>
        ) : null}
      </div>
      <Button
        variant="ghost"
        size="icon"
        aria-label={t("lists.actions.delete")}
        onClick={() => onDelete(entry.id)}
      >
        <X className="h-4 w-4" />
      </Button>
    </li>
  )
}
