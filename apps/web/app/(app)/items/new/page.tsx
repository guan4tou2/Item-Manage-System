"use client"

import { useQuery } from "@tanstack/react-query"
import { useRouter, useSearchParams } from "next/navigation"
import { useTranslations } from "next-intl"
import { useEffect, useState } from "react"
import { toast } from "sonner"

import { ViewerNotice } from "@/components/common/viewer-notice"
import { BatchEntryCard } from "@/components/ai/batch-entry-card"
import { ItemForm, type ItemFormValues } from "@/components/items/item-form"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { listCustomFields, listItemTemplates } from "@/lib/api/customization"
import { useAccessToken } from "@/lib/auth/use-auth"
import { useReadOnly } from "@/lib/auth/use-readonly"
import { useCategories } from "@/lib/hooks/use-categories"
import { useCreateItem } from "@/lib/hooks/use-items"
import { useLocations } from "@/lib/hooks/use-locations"
import { useTags } from "@/lib/hooks/use-tags"
import { useAuthStore } from "@/lib/auth/auth-store"
import { submitItem } from "@/lib/offline/submission"
import { shouldQueue } from "@/lib/offline/queue"
import { OfflineStorageError } from "@/lib/offline/storage"
import { clearEditingPending, getEditingPending, offlineQueue, useOnline } from "@/lib/offline/runtime"

const empty: ItemFormValues = {
  name: "",
  description: "",
  barcode: "",
  cost: "",
  category_id: null,
  location_id: null,
  quantity: 1,
  notes: "",
  image_id: null,
  tag_names: [],
  custom_values: {},
}

export default function NewItemPage() {
  const t = useTranslations()
  const router = useRouter()
  const searchParams = useSearchParams()
  const barcodePrefill = searchParams.get("barcode")
  const token = useAccessToken()
  const readOnly = useReadOnly()
  const [saving, setSaving] = useState(false)
  const owner = useAuthStore((s) => s.user?.id)
  const [editing] = useState(() => getEditingPending(owner))
  const [clientId] = useState(() => editing?.client_id ?? crypto.randomUUID())
  const [trackBatches, setTrackBatches] = useState(editing?.trackBatches ?? false)
  const online = useOnline()
  const create = useCreateItem(clientId)
  useEffect(() => () => clearEditingPending(), [])
  const cats = useCategories()
  const locs = useLocations()
  const tags = useTags()
  const customFields = useQuery({
    queryKey: ["customization", "custom-fields"],
    queryFn: () => listCustomFields(token),
    enabled: token !== null,
  })
  const itemTemplates = useQuery({
    queryKey: ["customization", "item-templates"],
    queryFn: () => listItemTemplates(token),
    enabled: token !== null,
  })

  async function handleSubmit(values: ItemFormValues) {
    setSaving(true)
    try {
      const draft = { values, trackBatches, customFields: customFields.data ?? editing?.customFields ?? [] }
      const enqueue = async () => {
        if (!owner) throw new Error("missing owner")
        await offlineQueue.save({
          ...draft, client_id: clientId, owner_user_id: owner,
          created_at: editing?.created_at ?? new Date().toISOString(),
          status: "pending", error_code: null, attempts: 0,
        })
        clearEditingPending()
        toast.success(t("offline.saved"))
        router.push("/items")
      }
      if (!navigator.onLine) {
        await enqueue()
        return
      }
      let outcome
      try {
        outcome = await submitItem(draft, clientId, token, (body) => create.mutateAsync(body))
      } catch (error) {
        if (shouldQueue(error, true)) {
          await enqueue()
          return
        }
        throw error
      }
      if (editing) await offlineQueue.remove(editing.client_id)
      clearEditingPending()
      if (outcome.partial === "batch") toast.error(t("items.form.trackBatchesEnableFailed"))
      else if (outcome.partial === "custom") {
        toast.error(t("items.toast.saveFailed"))
        return
      } else toast.success(t("items.toast.created"))
      router.push(`/items/${outcome.item.id}`)
    } catch (error) {
      toast.error(t(error instanceof OfflineStorageError ? `offline.${error.code}` : "items.toast.saveFailed"))
    } finally {
      setSaving(false)
    }
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
              <BreadcrumbPage>{t("items.list.new")}</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
        <h1 className="text-2xl font-semibold">{t("items.list.new")}</h1>
        <ViewerNotice backHref="/items" backLabel={t("viewer.notice.backToList")} />
      </section>
    )
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
            <BreadcrumbPage>{t("items.list.new")}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
      <h1 className="text-2xl font-semibold">{t("items.list.new")}</h1>
      <div inert={!online || undefined} aria-disabled={!online || undefined} className={!online ? "opacity-50" : undefined}><BatchEntryCard /></div>
      {!online && <p className="text-sm text-muted-foreground">{t("offline.requiresConnection")}</p>}
      <ItemForm
        defaultValues={editing?.values ?? empty}
        onSubmit={handleSubmit}
        onCancel={() => router.push("/items")}
        submitting={saving || create.isPending}
        categories={cats.data ?? []}
        locations={locs.data ?? []}
        tagSuggestions={(tags.data ?? []).map((tag) => tag.name)}
        customFields={customFields.data ?? editing?.customFields ?? []}
        itemTemplates={itemTemplates.data ?? []}
        trackBatches={trackBatches}
        onTrackBatchesChange={setTrackBatches}
        barcodePrefill={barcodePrefill}
      />
    </section>
  )
}
