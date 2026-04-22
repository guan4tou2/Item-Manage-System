"use client"

import Link from "next/link"
import { useParams, useRouter } from "next/navigation"
import { useTranslations } from "next-intl"
import { toast } from "sonner"

import { DeleteItemDialog } from "@/components/items/delete-item-dialog"
import { Badge } from "@/components/ui/badge"
import {
  Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useDeleteItem, useItem } from "@/lib/hooks/use-items"

export default function ItemDetailPage() {
  const t = useTranslations()
  const router = useRouter()
  const params = useParams<{ id: string }>()
  const id = params?.id ?? ""
  const item = useItem(id)
  const del = useDeleteItem()

  async function handleDelete() {
    try {
      await del.mutateAsync(id)
      toast.success(t("items.toast.deleted"))
      router.push("/items")
    } catch {
      toast.error(t("items.toast.saveFailed"))
    }
  }

  if (item.isLoading) {
    return (
      <section className="space-y-4 p-6">
        <Skeleton className="h-64 w-full max-w-2xl" />
      </section>
    )
  }
  if (item.isError || !item.data) {
    return (
      <section className="space-y-4 p-6">
        <p className="text-muted-foreground">{t("items.detail.notFound")}</p>
      </section>
    )
  }

  const i = item.data
  return (
    <section className="space-y-4 p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem><BreadcrumbLink href="/items">{t("nav.items")}</BreadcrumbLink></BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem><BreadcrumbPage>{i.name}</BreadcrumbPage></BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold">{i.name}</h1>
        <div className="flex gap-2">
          <Button asChild variant="outline">
            <Link href={`/items/${i.id}/edit`}>{t("items.detail.edit")}</Link>
          </Button>
          <DeleteItemDialog onConfirm={handleDelete} pending={del.isPending} />
        </div>
      </div>

      <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2 max-w-2xl">
        <div>
          <dt className="text-sm text-muted-foreground">{t("items.form.description")}</dt>
          <dd>{i.description || "—"}</dd>
        </div>
        <div>
          <dt className="text-sm text-muted-foreground">{t("items.form.quantity")}</dt>
          <dd className="tabular-nums">{i.quantity}</dd>
        </div>
        <div>
          <dt className="text-sm text-muted-foreground">{t("items.form.category")}</dt>
          <dd>{i.category?.name ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-sm text-muted-foreground">{t("items.form.location")}</dt>
          <dd>{i.location ? [i.location.floor, i.location.room, i.location.zone].filter(Boolean).join(" / ") : "—"}</dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="text-sm text-muted-foreground">{t("items.form.tags")}</dt>
          <dd className="space-x-1">
            {i.tags.length === 0 ? "—" : i.tags.map((tag) => <Badge key={tag.id} variant="secondary">{tag.name}</Badge>)}
          </dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="text-sm text-muted-foreground">{t("items.form.notes")}</dt>
          <dd className="whitespace-pre-wrap">{i.notes || "—"}</dd>
        </div>
      </dl>
    </section>
  )
}
