"use client"

import { useSortable } from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"

import { ListEntryRow } from "@/components/lists/list-entry-row"
import type { ListEntry } from "@/lib/api/lists"

interface Props {
  entry: ListEntry
  onToggle: (id: string) => void
  onDelete: (id: string) => void
}

export function SortableEntry({ entry, onToggle, onDelete }: Props) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({
    id: entry.id,
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
        dragHandleProps={{ ...attributes, ...listeners }}
      />
    </div>
  )
}
