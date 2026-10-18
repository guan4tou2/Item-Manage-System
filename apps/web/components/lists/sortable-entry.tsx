"use client"

import { useSortable } from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"

import { ListEntryRow } from "@/components/lists/list-entry-row"
import type { ListEntry } from "@/lib/api/lists"

interface Props {
  entry: ListEntry
  onToggle: (id: string) => void
  onDelete: (id: string) => void
  /** Phase 30：唯讀檢視（停用排序、不顯示拖放把手） */
  readOnly?: boolean
}

export function SortableEntry({ entry, onToggle, onDelete, readOnly = false }: Props) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({
    id: entry.id,
    disabled: readOnly,
  })
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }
  return (
    <div ref={setNodeRef} style={style}>
      <ListEntryRow
        entry={entry}
        onToggle={onToggle}
        onDelete={onDelete}
        readOnly={readOnly}
        dragHandleProps={readOnly ? undefined : { ...attributes, ...listeners }}
      />
    </div>
  )
}
