"use client"

import { useQuery, useQueryClient } from "@tanstack/react-query"
import Link from "next/link"
import { useParams, useRouter } from "next/navigation"
import { useTranslations } from "next-intl"
import { useEffect, useState } from "react"
import { toast } from "sonner"

import { useOfflineSync } from "@/components/offline/offline-status"
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
import { useAuthStore } from "@/lib/auth/auth-store"
import { clearEditingPending, getEditingPending, offlineQueue, useOnline, usePendingItems } from "@/lib/offline/runtime"
import { shouldQueue } from "@/lib/offline/queue"
import { OfflineStorageError } from "@/lib/offline/storage"
import { updateBody } from "@/lib/offline/steps"
import { optimisticItem } from "@/lib/offline/optimistic"

export default function EditItemPage() {
  const t = useTranslations()
  const router = useRouter()
  const params = useParams<{ id: string }>()
  const id = params?.id ?? ""
  const token = useAccessToken()
  const owner = useAuthStore((s) => s.user?.id)
  const online = useOnline()
  const pending = usePendingItems().find((row) => row.item_id === id && (row.kind === "update" || row.kind === "delete"))
  const [editing] = useState(() => {
    const row = getEditingPending(owner)
    return row?.kind === "update" && row.item_id === id ? row : null
  })
  useEffect(() => () => clearEditingPending(), [])
  const readOnly = useReadOnly()
  const queryClient = useQueryClient()
  const sync = useOfflineSync()
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

  if (pending?.kind === "delete") {
    return <section className="space-y-4 p-6"><p role="status" className="text-sm text-muted-foreground">{t("offline.pendingDeletion")}</p><Link href="/items" className="inline-flex min-h-11 items-center text-primary underline">{t("viewer.notice.backToList")}</Link></section>
  }

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

  const defaults: ItemFormValues = editing?.values ?? pending?.values ?? {
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

  const tracking = trackingOverride ?? editing?.trackBatches ?? pending?.trackBatches ?? item.data.track_batches

  async function enableTracking() {
    if (!navigator.onLine) return
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
      // 離線時導頁需要向伺服器抓頁面資料，會失敗；只有確定連得上才導回詳情頁。
      const enqueue = async (reachable: boolean) => {
        if (!owner || !item.data) throw new Error("missing item or owner")
        await offlineQueue.save({
          kind: "update", item_id: id, item_name: values.name,
          base_updated_at: editing?.base_updated_at ?? item.data.updated_at,
          client_id: editing?.client_id ?? crypto.randomUUID(), owner_user_id: owner,
          created_at: editing?.created_at ?? new Date().toISOString(),
          status: "pending", error_code: null, attempts: 0,
          values, trackBatches: tracking, customFields: customFields.data ?? editing?.customFields ?? [],
        })
        await queryClient.cancelQueries({ queryKey: ["items", id] })
        queryClient.setQueryData(["items", id], optimisticItem(item.data, values, cats.data ?? [], locs.data ?? []))
        queryClient.setQueryData(["items", id, "custom-values"], Object.entries(values.custom_values).map(([field, value]) => ({ custom_field_id: Number(field), value })))
        clearEditingPending()
        toast.success(t("offline.saved"))
        if (reachable) {
          router.push(`/items/${id}`)
          void sync()
        }
      }
      // Resending a failed draft must replace its queued record, retaining its original base.
      if (!navigator.onLine || editing || pending) { await enqueue(navigator.onLine); return }
      try {
        await update.mutateAsync(updateBody(values, tracking))
      } catch (error) {
        if (shouldQueue(error, true)) { await enqueue(false); return }
        throw error
      }
      await saveItemCustomValues(id, customFields.data ?? [], values.custom_values, token)
      await queryClient.invalidateQueries({ queryKey: ["items", id, "custom-values"] })
      toast.success(t("items.toast.updated"))
      router.push(`/items/${id}`)
    } catch (error) {
      toast.error(t(error instanceof OfflineStorageError ? `offline.${error.code}` : "items.toast.saveFailed"))
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
      {pending && <p role="status" className="text-sm text-muted-foreground">{t("offline.unsyncedChanges")}</p>}
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
        disableEnableTracking={!online}
        onTrackBatchesChange={(next) => {
          if (next && online) void enableTracking()
        }}
      />
    </section>
  )
}
