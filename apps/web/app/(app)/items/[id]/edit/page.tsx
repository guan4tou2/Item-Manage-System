"use client"

import { useParams, useRouter } from "next/navigation"
import { useTranslations } from "next-intl"
import { toast } from "sonner"

import { ItemForm, type ItemFormValues } from "@/components/items/item-form"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Skeleton } from "@/components/ui/skeleton"
import { useCategories } from "@/lib/hooks/use-categories"
import { useItem, useUpdateItem } from "@/lib/hooks/use-items"
import { useLocations } from "@/lib/hooks/use-locations"
import { useTags } from "@/lib/hooks/use-tags"

export default function EditItemPage() {
  const t = useTranslations()
  const router = useRouter()
  const params = useParams<{ id: string }>()
  const id = params?.id ?? ""
  const item = useItem(id)
  const update = useUpdateItem(id)
  const cats = useCategories()
  const locs = useLocations()
  const tags = useTags()

  if (item.isError) {
    return (
      <section className="space-y-4 p-6">
        <p className="text-muted-foreground">{t("items.detail.notFound")}</p>
      </section>
    )
  }
  if (item.isLoading || !item.data) {
    return (
      <section className="space-y-4 p-6">
        <Skeleton className="h-64 w-full max-w-xl" />
      </section>
    )
  }

  const defaults: ItemFormValues = {
    name: item.data.name,
    description: item.data.description ?? "",
    category_id: item.data.category?.id ?? null,
    location_id: item.data.location?.id ?? null,
    quantity: item.data.quantity,
    notes: item.data.notes ?? "",
    tag_names: item.data.tags.map((tag) => tag.name),
  }

  async function handleSubmit(values: ItemFormValues) {
    try {
      await update.mutateAsync({
        name: values.name,
        description: values.description || null,
        category_id: values.category_id,
        location_id: values.location_id,
        quantity: values.quantity,
        notes: values.notes || null,
        tag_names: values.tag_names,
      })
      toast.success(t("items.toast.updated"))
      router.push(`/items/${id}`)
    } catch {
      toast.error(t("items.toast.saveFailed"))
    }
  }

  return (
    <section className="space-y-4 p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink href="/items">{t("nav.items")}</BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbLink href={`/items/${id}`}>{item.data.name}</BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>{t("items.detail.edit")}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
      <h1 className="text-2xl font-semibold">{t("items.detail.edit")}</h1>
      <ItemForm
        defaultValues={defaults}
        onSubmit={handleSubmit}
        onCancel={() => router.push(`/items/${id}`)}
        submitting={update.isPending}
        categories={cats.data ?? []}
        locations={locs.data ?? []}
        tagSuggestions={(tags.data ?? []).map((tag) => tag.name)}
      />
    </section>
  )
}
