"use client"

import { useQuery, useQueryClient } from "@tanstack/react-query"
import { useParams, useRouter } from "next/navigation"
import { useTranslations } from "next-intl"
import { useState } from "react"
import { toast } from "sonner"

import { ViewerNotice } from "@/components/common/viewer-notice"
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
import {
  listCustomFields,
  listItemCustomValues,
  saveItemCustomValues,
} from "@/lib/api/customization"
import { getApiErrorDetail } from "@/lib/api/client"
import { useAccessToken } from "@/lib/auth/use-auth"
import { useReadOnly } from "@/lib/auth/use-readonly"
import { useCreateBatch } from "@/lib/hooks/use-batches"
import { useCategories } from "@/lib/hooks/use-categories"
import { useItem, useUpdateItem } from "@/lib/hooks/use-items"
import { useLocations } from "@/lib/hooks/use-locations"
import { useTags } from "@/lib/hooks/use-tags"
import { itemCostPayload } from "@/lib/items/cost"

export default function EditItemPage() {
  const t = useTranslations()
  const router = useRouter()
  const params = useParams<{ id: string }>()
  const id = params?.id ?? ""
  const token = useAccessToken()
  const readOnly = useReadOnly()
  const queryClient = useQueryClient()
  const [saving, setSaving] = useState(false)
  const [trackingOverride, setTrackingOverride] = useState<boolean | null>(null)
  const item = useItem(id)
  const update = useUpdateItem(id)
  const enableBatches = useCreateBatch(id)
  const cats = useCategories()
  const locs = useLocations()
  const tags = useTags()
  const customFields = useQuery({
    queryKey: ["customization", "custom-fields"],
    queryFn: () => listCustomFields(token),
    enabled: token !== null,
  })
  const customValues = useQuery({
    queryKey: ["items", id, "custom-values"],
    queryFn: () => listItemCustomValues(id, token),
    enabled: token !== null && !!id,
  })

  if (item.isError) {
    return (
      <section className="space-y-6 p-6">
        <p className="text-muted-foreground">{t("items.detail.notFound")}</p>
      </section>
    )
  }
  if (item.isLoading || customFields.isLoading || customValues.isLoading || !item.data) {
    return (
      <section className="space-y-6 p-6">
        <Skeleton className="h-64 w-full max-w-xl" />
      </section>
    )
  }

  if (readOnly) {
    return (
      <section className="space-y-6 p-6">
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
        <ViewerNotice
          backHref={`/items/${id}`}
          backLabel={t("items.detail.backToItem")}
        />
      </section>
    )
  }

  const customValueDefaults = (customValues.data ?? []).reduce<ItemFormValues["custom_values"]>(
    (acc, value) => {
      acc[String(value.custom_field_id)] = value.value as ItemFormValues["custom_values"][string]
      return acc
    },
    {},
  )

  const defaults: ItemFormValues = {
    name: item.data.name,
    description: item.data.description ?? "",
    barcode: item.data.barcode ?? "",
    cost: item.data.cost ?? "",
    category_id: item.data.category?.id ?? null,
    location_id: item.data.location?.id ?? null,
    quantity: item.data.quantity,
    notes: item.data.notes ?? "",
    image_id: item.data.image_id ?? null,
    tag_names: item.data.tags.map((tag) => tag.name),
    custom_values: customValueDefaults,
  }

  const tracking = trackingOverride ?? item.data.track_batches

  async function enableTracking() {
    // 編輯既有物品：開啟當下即 POST batches（省略 quantity → 沿用既有數量併入第一批）
    try {
      await enableBatches.mutateAsync({})
      setTrackingOverride(true)
      toast.success(t("items.form.trackBatchesEnabled"))
    } catch (error) {
      toast.error(getApiErrorDetail(error) ?? t("items.form.trackBatchesEnableFailed"))
    }
  }

  async function handleSubmit(values: ItemFormValues) {
    setSaving(true)
    try {
      await update.mutateAsync({
        name: values.name,
        description: values.description || null,
        barcode: values.barcode || null,
        cost: itemCostPayload(values.cost),
        category_id: values.category_id,
        location_id: values.location_id,
        // tracked 物品不得改 quantity（API 409）；追蹤中一律略過
        ...(tracking ? {} : { quantity: values.quantity }),
        notes: values.notes || null,
        image_id: values.image_id ?? null,
        tag_names: values.tag_names,
      })
      await saveItemCustomValues(id, customFields.data ?? [], values.custom_values, token)
      await queryClient.invalidateQueries({ queryKey: ["items", id, "custom-values"] })
      toast.success(t("items.toast.updated"))
      router.push(`/items/${id}`)
    } catch {
      toast.error(t("items.toast.saveFailed"))
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="space-y-6 p-6">
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
        submitting={saving || update.isPending}
        categories={cats.data ?? []}
        locations={locs.data ?? []}
        tagSuggestions={(tags.data ?? []).map((tag) => tag.name)}
        customFields={customFields.data ?? []}
        trackBatches={tracking}
        trackBatchesLocked={tracking}
        onTrackBatchesChange={(next) => {
          if (next) void enableTracking()
        }}
      />
    </section>
  )
}
