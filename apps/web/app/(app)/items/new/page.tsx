"use client"

import { useQuery } from "@tanstack/react-query"
import { useRouter, useSearchParams } from "next/navigation"
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
import { createBatch } from "@/lib/api/batches"
import { listCustomFields, listItemTemplates, saveItemCustomValues } from "@/lib/api/customization"
import { useAccessToken } from "@/lib/auth/use-auth"
import { useReadOnly } from "@/lib/auth/use-readonly"
import { useCategories } from "@/lib/hooks/use-categories"
import { useCreateItem } from "@/lib/hooks/use-items"
import { useLocations } from "@/lib/hooks/use-locations"
import { useTags } from "@/lib/hooks/use-tags"
import { itemCostPayload } from "@/lib/items/cost"

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
  const [trackBatches, setTrackBatches] = useState(false)
  const create = useCreateItem()
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
      const created = await create.mutateAsync({
        name: values.name,
        description: values.description || undefined,
        barcode: values.barcode || undefined,
        cost: itemCostPayload(values.cost),
        category_id: values.category_id ?? undefined,
        location_id: values.location_id ?? undefined,
        quantity: values.quantity,
        notes: values.notes || undefined,
        image_id: values.image_id ?? undefined,
        tag_names: values.tag_names,
      })
      if (trackBatches) {
        // 開啟追蹤：建立第一批（省略 quantity → 沿用既有數量併入無到期日批次）
        try {
          await createBatch(created.id, {}, token)
        } catch {
          toast.error(t("items.form.trackBatchesEnableFailed"))
          router.push(`/items/${created.id}`)
          return
        }
      }
      await saveItemCustomValues(
        created.id,
        customFields.data ?? [],
        values.custom_values,
        token,
      )
      toast.success(t("items.toast.created"))
      router.push(`/items/${created.id}`)
    } catch {
      toast.error(t("items.toast.saveFailed"))
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
      <ItemForm
        defaultValues={empty}
        onSubmit={handleSubmit}
        onCancel={() => router.push("/items")}
        submitting={saving || create.isPending}
        categories={cats.data ?? []}
        locations={locs.data ?? []}
        tagSuggestions={(tags.data ?? []).map((tag) => tag.name)}
        customFields={customFields.data ?? []}
        itemTemplates={itemTemplates.data ?? []}
        trackBatches={trackBatches}
        onTrackBatchesChange={setTrackBatches}
        barcodePrefill={barcodePrefill}
      />
    </section>
  )
}
