"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ListPlus, Copy } from "lucide-react"
import Link from "next/link"
import { useParams, useRouter } from "next/navigation"
import { useLocale, useTranslations } from "next-intl"
import { toast } from "sonner"

import { EditableOnly } from "@/components/common/editable-only"
import { DeleteItemDialog } from "@/components/items/delete-item-dialog"
import { FavoriteButton } from "@/components/items/favorite-button"
import { ItemCustomValuesDetail } from "@/components/items/item-custom-values-detail"
import { LabelBarcode } from "@/components/items/label-barcode"
import { AuthImage } from "@/components/common/auth-image"
import { LoanCard } from "@/components/collaboration/loan-card"
import { NewTransferDialog } from "@/components/collaboration/new-transfer-dialog"
import { ReadonlyBadge } from "@/components/collaboration/readonly-badge"
import { Badge } from "@/components/ui/badge"
import {
  Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import {
  createItemTemplate,
  listCustomFields,
  listItemCustomValues,
  type ItemCustomValueRead,
} from "@/lib/api/customization"
import type { ItemRead } from "@/lib/api/items"
import { useAuthStore } from "@/lib/auth/auth-store"
import { useAccessToken } from "@/lib/auth/use-auth"
import { useReadOnly } from "@/lib/auth/use-readonly"
import { useDeleteItem, useItem } from "@/lib/hooks/use-items"
import { formatCurrency } from "@/lib/format/currency"
import { truncatePath } from "@/lib/locations/tree"
import { usePreferences } from "@/lib/preferences/use-preferences"
import { BatchSection } from "@/components/items/batch-section"

function templatePayloadFromItem(item: ItemRead, customValues: ItemCustomValueRead[]) {
  const payload: Record<string, unknown> = {
    name: item.name,
    quantity: item.quantity,
  }
  if (item.description?.trim()) payload.description = item.description
  if (item.notes?.trim()) payload.notes = item.notes

  const tagNames = item.tags.map((tag) => tag.name).filter(Boolean)
  if (tagNames.length > 0) payload.tag_names = tagNames

  const customValueMap: Record<string, unknown> = {}
  for (const customValue of customValues) {
    if (customValue.value !== undefined && customValue.value !== null && customValue.value !== "") {
      customValueMap[String(customValue.custom_field_id)] = customValue.value
    }
  }
  if (Object.keys(customValueMap).length > 0) payload.custom_values = customValueMap

  return payload
}

export default function ItemDetailPage() {
  const t = useTranslations()
  const router = useRouter()
  const queryClient = useQueryClient()
  const params = useParams<{ id: string }>()
  const id = params?.id ?? ""
  const item = useItem(id)
  const del = useDeleteItem()
  const token = useAccessToken()
  const locale = useLocale()
  const prefs = usePreferences()
  const currency = prefs.data?.currency ?? "TWD"
  const readOnly = useReadOnly()
  const currentUserId = useAuthStore((s) => s.user?.id ?? "")
  const isOwner = item.data?.owner_id === currentUserId
  const customFields = useQuery({
    queryKey: ["customization", "custom-fields"],
    queryFn: () => listCustomFields(token),
    enabled: token !== null && isOwner,
  })
  const customValues = useQuery({
    queryKey: ["items", id, "custom-values"],
    queryFn: () => listItemCustomValues(id, token),
    enabled: token !== null && !!id && isOwner,
  })
  const saveTemplate = useMutation({
    mutationFn: () => {
      if (!item.data) throw new Error("missing item")
      return createItemTemplate(
        {
          name: t("items.detail.templateName", { name: item.data.name }),
          payload: templatePayloadFromItem(item.data, customValues.data ?? []),
        },
        token,
      )
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["customization", "item-templates"] })
      toast.success(t("items.detail.templateSaved"))
    },
    onError: () => toast.error(t("items.detail.templateSaveFailed")),
  })

  async function handleDelete() {
    try {
      await del.mutateAsync(id)
      toast.success(t("items.toast.deleted"))
      router.push("/items")
    } catch {
      toast.error(t("items.toast.saveFailed"))
    }
  }

  async function copyBarcode(code: string) {
    try {
      await navigator.clipboard.writeText(code)
      toast.success(t("items.detail.barcodeCopied"))
    } catch {
      toast.error(t("items.detail.barcodeCopyFailed"))
    }
  }

  if (item.isLoading) {
    return (
      <section className="space-y-6 p-6">
        <Skeleton className="h-64 w-full max-w-2xl" />
      </section>
    )
  }
  if (item.isError || !item.data) {
    return (
      <section className="space-y-6 p-6">
        <p className="text-muted-foreground">{t("items.detail.notFound")}</p>
      </section>
    )
  }

  const i = item.data
  return (
    <section className="space-y-6 p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem><BreadcrumbLink href="/items">{t("nav.items")}</BreadcrumbLink></BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem><BreadcrumbPage>{i.name}</BreadcrumbPage></BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <div className="flex flex-wrap items-center justify-between gap-2">
        {/* min-w-0＋overflow-wrap:anywhere：沒有斷字機會的長名稱（條碼、代號）在手機寬度也要能折行，不可撐出水平捲軸 */}
        <div className="flex min-w-0 items-center gap-2">
          <h1 className="min-w-0 text-2xl font-semibold [overflow-wrap:anywhere]">{i.name}</h1>
          {isOwner ? (
            <EditableOnly>
              <FavoriteButton itemId={i.id} isFavorite={i.is_favorite} />
            </EditableOnly>
          ) : null}
        </div>
        <div className="flex w-full flex-wrap gap-2 sm:w-auto sm:justify-end">
          {isOwner ? (
            <>
              <EditableOnly>
                <Button asChild variant="outline">
                  <Link href={`/items/${i.id}/edit`}>{t("items.detail.edit")}</Link>
                </Button>
              </EditableOnly>
              {/* 列印標籤為讀取性操作，viewer 維持可用（登錄決策） */}
              <Button asChild variant="outline">
                <Link href={`/items/${i.id}/label` as never}>{t("items.detail.printLabel")}</Link>
              </Button>
              <EditableOnly>
                <>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => saveTemplate.mutate()}
                    disabled={saveTemplate.isPending || customValues.isLoading}
                  >
                    <ListPlus className="mr-2 h-4 w-4" aria-hidden="true" />
                    {saveTemplate.isPending
                      ? t("items.detail.savingTemplate")
                      : t("items.detail.saveAsTemplate")}
                  </Button>
                  <NewTransferDialog itemId={i.id} />
                  <DeleteItemDialog onConfirm={handleDelete} pending={del.isPending} />
                </>
              </EditableOnly>
            </>
          ) : (
            <ReadonlyBadge ownerUsername={i.owner_username} />
          )}
        </div>
      </div>

      {i.image_id ? (
        <AuthImage
          imageId={i.image_id}
          alt={i.name}
          className="max-h-64 max-w-full rounded-[0.25rem] border object-contain"
        />
      ) : null}

      <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2 max-w-2xl">
        <div>
          <dt className="text-sm text-muted-foreground">{t("items.form.description")}</dt>
          <dd>{i.description || "—"}</dd>
        </div>
        {i.barcode ? (
          <div>
            <dt className="text-sm text-muted-foreground">{t("items.form.barcode")}</dt>
            <dd className="flex items-center gap-1">
              <span className="font-mono">{i.barcode}</span>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                className="h-7 px-2"
                aria-label={t("items.detail.copyBarcode")}
                onClick={() => void copyBarcode(i.barcode as string)}
              >
                <Copy className="h-4 w-4" />
              </Button>
            </dd>
            {/* Phase 37：條碼圖（Code128）；不可編碼時只留下方文字 */}
            <LabelBarcode value={i.barcode} />
          </div>
        ) : null}
        <div>
          <dt className="text-sm text-muted-foreground">{t("items.form.quantity")}</dt>
          <dd className="tabular-nums">{i.quantity}</dd>
        </div>
        <div>
          <dt className="text-sm text-muted-foreground">{t("items.form.cost")}</dt>
          <dd className="tabular-nums" data-testid="item-cost">
            {prefs.isPending ? (
              <Skeleton className="h-4 w-20" />
            ) : (
              formatCurrency(i.cost, currency, locale)
            )}
          </dd>
        </div>
        <div>
          <dt className="text-sm text-muted-foreground">{t("items.form.category")}</dt>
          <dd>{i.category?.name ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-sm text-muted-foreground">{t("items.form.location")}</dt>
          <dd>
            {i.location ? (
              <span
                className="font-mono text-sm"
                title={i.location.path}
                data-testid="item-location-path"
              >
                {truncatePath(i.location.path)}
              </span>
            ) : (
              "—"
            )}
          </dd>
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

      {i.track_batches ? <BatchSection itemId={i.id} canEdit={isOwner && !readOnly} defaultCost={i.cost} currency={currency} /> : null}

      {isOwner ? (
        <ItemCustomValuesDetail
          customFields={customFields.data ?? []}
          values={customValues.data ?? []}
          loading={customFields.isLoading || customValues.isLoading}
        />
      ) : null}

      {isOwner && !readOnly ? (
        <div className="max-w-2xl">
          <LoanCard itemId={i.id} />
        </div>
      ) : null}

      {readOnly ? (
        <p
          role="status"
          data-testid="viewer-item-notice"
          className="sticky bottom-3 max-w-2xl rounded-md border bg-background/95 px-4 py-3 text-sm text-muted-foreground shadow-xs backdrop-blur-sm supports-[backdrop-filter]:bg-background/85"
        >
          {t("viewer.itemNotice")}
        </p>
      ) : null}
    </section>
  )
}
