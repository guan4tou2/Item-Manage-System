"use client"

import { useTranslations } from "next-intl"

import type { CustomFieldRead, ItemCustomValueRead } from "@/lib/api/customization"

interface Props {
  customFields: CustomFieldRead[]
  values: ItemCustomValueRead[]
  loading?: boolean
}

function hasValue(value: unknown) {
  return value !== null && value !== undefined && value !== ""
}

export function ItemCustomValuesDetail({ customFields, values, loading = false }: Props) {
  const t = useTranslations()

  if (customFields.length === 0) return null

  const valuesByField = new Map(values.map((value) => [value.custom_field_id, value.value]))
  const filledFields = customFields
    .map((field) => ({ field, value: valuesByField.get(field.id) }))
    .filter(({ value }) => hasValue(value))

  const formatValue = (value: unknown) => {
    if (typeof value === "boolean") {
      return value ? t("items.detail.booleanYes") : t("items.detail.booleanNo")
    }
    return String(value)
  }

  return (
    <section className="max-w-2xl space-y-3 rounded-md border p-4">
      <h2 className="text-sm font-semibold">{t("items.detail.customFields")}</h2>
      {loading ? (
        <p className="text-sm text-muted-foreground">{t("items.detail.customFieldsLoading")}</p>
      ) : filledFields.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("items.detail.noCustomValues")}</p>
      ) : (
        <dl className="grid gap-3 sm:grid-cols-2">
          {filledFields.map(({ field, value }) => (
            <div key={field.id}>
              <dt className="text-sm text-muted-foreground">{field.name}</dt>
              <dd className="break-words">{formatValue(value)}</dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  )
}
