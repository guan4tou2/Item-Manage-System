"use client"

import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core"
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable"
import { useParams, useRouter } from "next/navigation"
import { useState } from "react"
import { useTranslations } from "next-intl"

import { KindBadge } from "@/components/lists/kind-badge"
import { SortableEntry } from "@/components/lists/sortable-entry"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import {
  useCreateEntry,
  useDeleteEntry,
  useDeleteList,
  useList,
  useReorderEntries,
  useToggleEntry,
} from "@/lib/hooks/use-lists"
import type { ListKind } from "@/lib/api/lists"

export default function ListDetailPage() {
  const t = useTranslations()
  const params = useParams()
  const router = useRouter()
  const listId = String(params.id)

  const query = useList(listId)
  const createEntry = useCreateEntry(listId)
  const toggleEntry = useToggleEntry(listId)
  const deleteEntry = useDeleteEntry(listId)
  const deleteList = useDeleteList()
  const reorder = useReorderEntries(listId)

  const [newName, setNewName] = useState("")

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  )

  if (query.isLoading) {
    return (
      <section className="space-y-4 p-6">
        <Skeleton className="h-8 w-60" />
        <Skeleton className="h-32 w-full" />
      </section>
    )
  }
  if (!query.data) {
    return (
      <section className="p-6 text-muted-foreground">List not found.</section>
    )
  }

  const list = query.data
  const kind = list.kind as ListKind

  const onDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (!over || active.id === over.id) return
    const ids = list.entries.map((e) => e.id)
    const from = ids.indexOf(String(active.id))
    const to = ids.indexOf(String(over.id))
    if (from === -1 || to === -1) return
    const next = [...ids]
    const [moved] = next.splice(from, 1)
    if (moved === undefined) return
    next.splice(to, 0, moved)
    reorder.mutate(next)
  }

  const onAdd = () => {
    const name = newName.trim()
    if (!name) return
    createEntry.mutate({ name, is_done: false })
    setNewName("")
  }

  const spent = list.entries
    .filter((e) => e.is_done && e.price !== null)
    .reduce((acc, e) => acc + Number(e.price) * (e.quantity ?? 1), 0)

  return (
    <section className="space-y-6 p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink href="/lists">{t("lists.title")}</BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>{list.title}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold">{list.title}</h1>
          <div className="flex items-center gap-2">
            <KindBadge kind={kind} />
            <span className="text-sm text-muted-foreground">
              {t("lists.detail.entryCount", {
                count: list.entry_count,
                done: list.done_count,
              })}
            </span>
          </div>
          {kind === "travel" && list.start_date && list.end_date ? (
            <p className="text-sm text-muted-foreground">
              {t("lists.detail.dateRange", {
                start: list.start_date,
                end: list.end_date,
              })}
            </p>
          ) : null}
          {kind === "shopping" && list.budget !== null ? (
            <div className="text-sm">
              <span className="text-muted-foreground">
                {t("lists.detail.budget", { amount: list.budget })} ·{" "}
                {t("lists.detail.spent", { amount: spent.toFixed(2) })}
              </span>
              {spent > Number(list.budget) ? (
                <span className="ml-2 text-destructive">
                  {t("lists.detail.overBudget", {
                    amount: (spent - Number(list.budget)).toFixed(2),
                  })}
                </span>
              ) : null}
            </div>
          ) : null}
        </div>

        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="outline" size="sm">
              {t("lists.actions.delete")}
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>{t("lists.actions.confirmDelete")}</AlertDialogTitle>
              <AlertDialogDescription>
                {t("lists.actions.confirmDeleteBody")}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>{t("lists.new.cancel")}</AlertDialogCancel>
              <AlertDialogAction
                onClick={async () => {
                  await deleteList.mutateAsync(listId)
                  router.push("/lists")
                }}
              >
                {t("lists.actions.delete")}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>

      <div className="rounded-lg border">
        {list.entries.length === 0 ? (
          <p className="p-6 text-center text-sm text-muted-foreground">
            {t("lists.entry.empty")}
          </p>
        ) : (
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={onDragEnd}
          >
            <SortableContext
              items={list.entries.map((e) => e.id)}
              strategy={verticalListSortingStrategy}
            >
              <ul>
                {list.entries.map((entry) => (
                  <SortableEntry
                    key={entry.id}
                    entry={entry}
                    onToggle={(id) => toggleEntry.mutate(id)}
                    onDelete={(id) => deleteEntry.mutate(id)}
                  />
                ))}
              </ul>
            </SortableContext>
          </DndContext>
        )}

        <div className="border-t p-4">
          <form
            onSubmit={(e) => {
              e.preventDefault()
              onAdd()
            }}
            className="flex gap-2"
          >
            <Input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder={t("lists.entry.placeholder")}
            />
            <Button type="submit" disabled={!newName.trim() || createEntry.isPending}>
              {t("lists.new.create")}
            </Button>
          </form>
        </div>
      </div>
    </section>
  )
}
