"use client"

import { zodResolver } from "@hookform/resolvers/zod"
import { CheckCircle2, RotateCcw, Sparkles } from "lucide-react"
import { useTranslations } from "next-intl"
import { useRef, useState } from "react"
import { useForm, type Path } from "react-hook-form"
import { toast } from "sonner"
import { z } from "zod"

import { ImageUpload } from "./image-upload"
import { TagMultiSelect } from "./tag-multi-select"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { suggestFromImage } from "@/lib/api/ai"
import { getApiErrorDetail } from "@/lib/api/client"
import type { CategoryTreeNode } from "@/lib/api/categories"
import type { CustomFieldRead, ItemTemplateRead } from "@/lib/api/customization"
import type { LocationRead } from "@/lib/api/locations"
import { useAccessToken } from "@/lib/auth/use-auth"

const customValueSchema = z.union([z.string(), z.number(), z.boolean(), z.null()])

export const itemFormSchema = z.object({
  name: z.string().min(1, "nameRequired").max(200, "nameMax"),
  description: z.string().optional(),
  category_id: z.number().nullable(),
  location_id: z.number().nullable(),
  quantity: z.preprocess(
    (v) => (typeof v === "string" && v.trim() === "" ? undefined : v),
    z.coerce
      .number({ required_error: "quantityRequired", invalid_type_error: "quantityRequired" })
      .int("quantityInteger")
      .min(0, "quantityMin"),
  ),
  notes: z.string().optional(),
  image_id: z.string().nullable().optional(),
  tag_names: z.array(z.string()),
  custom_values: z.record(customValueSchema).default({}),
})
export type ItemFormValues = z.infer<typeof itemFormSchema>

interface Props {
  defaultValues: ItemFormValues
  onSubmit: (values: ItemFormValues) => void | Promise<void>
  onCancel: () => void
  submitting: boolean
  categories: CategoryTreeNode[]
  locations: LocationRead[]
  tagSuggestions: string[]
  customFields?: CustomFieldRead[]
  itemTemplates?: ItemTemplateRead[]
}

interface AppliedField {
  path: Path<ItemFormValues>
  label: string
  before: unknown
  applied: unknown
  restoreEmptyString?: boolean
}

interface AppliedTemplateState {
  id: number
  name: string
  fields: AppliedField[]
}

function flattenCategories(nodes: CategoryTreeNode[], depth = 0): Array<{ id: number; label: string }> {
  const out: Array<{ id: number; label: string }> = []
  for (const n of nodes) {
    out.push({ id: n.id, label: `${"— ".repeat(depth)}${n.name}` })
    if (n.children && n.children.length > 0) out.push(...flattenCategories(n.children, depth + 1))
  }
  return out
}

function valuesEqual(a: unknown, b: unknown) {
  return JSON.stringify(a) === JSON.stringify(b)
}

export function ItemForm({
  defaultValues, onSubmit, onCancel, submitting,
  categories, locations, tagSuggestions, customFields = [], itemTemplates = [],
}: Props) {
  const t = useTranslations()
  const token = useAccessToken()
  const [aiBusy, setAiBusy] = useState(false)
  const [appliedTemplate, setAppliedTemplate] = useState<AppliedTemplateState | null>(null)
  const templateButtonRefs = useRef(new Map<number, HTMLButtonElement | null>())
  const form = useForm<ItemFormValues>({
    resolver: zodResolver(itemFormSchema),
    defaultValues,
  })
  const flatCats = flattenCategories(categories)

  const runAiSuggest = async () => {
    const imageId = form.getValues("image_id")
    if (!imageId) {
      toast.error(t("items.form.uploadImageFirst"))
      return
    }
    setAiBusy(true)
    try {
      const result = await suggestFromImage(imageId, token)
      form.setValue("name", result.name)
      if (result.description) form.setValue("description", result.description)
      const existing = form.getValues("tag_names") ?? []
      const merged = Array.from(new Set([...existing, ...result.tag_suggestions]))
      form.setValue("tag_names", merged)
      toast.success(t("items.form.aiSuggested"))
    } catch (e: unknown) {
      toast.error(getApiErrorDetail(e) ?? t("items.form.aiFailed"))
    } finally {
      setAiBusy(false)
    }
  }

  const applyTemplate = (template: ItemTemplateRead) => {
    const payload = template.payload
    const appliedFields: AppliedField[] = []
    const applyField = (
      path: Path<ItemFormValues>,
      value: unknown,
      label: string,
      options: { restoreEmptyString?: boolean } = {},
    ) => {
      appliedFields.push({
        path,
        label,
        before: form.getValues(path),
        applied: value,
        restoreEmptyString: options.restoreEmptyString,
      })
      form.setValue(path, value as never, { shouldDirty: true, shouldTouch: true })
    }

    if (typeof payload.name === "string") {
      applyField("name", payload.name, t("items.form.name"))
    }
    if (typeof payload.description === "string") {
      applyField("description", payload.description, t("items.form.description"))
    }
    if (typeof payload.quantity === "number") {
      applyField("quantity", payload.quantity, t("items.form.quantity"))
    } else if (typeof payload.quantity === "string" && payload.quantity.trim() !== "") {
      const quantity = Number(payload.quantity)
      if (Number.isFinite(quantity)) {
        applyField("quantity", quantity, t("items.form.quantity"))
      }
    }
    if (typeof payload.notes === "string") {
      applyField("notes", payload.notes, t("items.form.notes"))
    }
    if (Array.isArray(payload.tag_names)) {
      applyField(
        "tag_names",
        payload.tag_names.filter((tag): tag is string => typeof tag === "string"),
        t("items.form.tags"),
      )
    }
    if (payload.custom_values && typeof payload.custom_values === "object" && !Array.isArray(payload.custom_values)) {
      for (const [fieldId, value] of Object.entries(payload.custom_values)) {
        if (
          typeof value === "string" ||
          typeof value === "number" ||
          typeof value === "boolean" ||
          value === null
        ) {
          const customField = customFields.find((field) => String(field.id) === fieldId)
          applyField(
            `custom_values.${fieldId}` as Path<ItemFormValues>,
            value,
            customField?.name ?? t("items.form.customFields"),
            { restoreEmptyString: customField?.field_type !== "bool" },
          )
        }
      }
    }
    setAppliedTemplate({ id: template.id, name: template.name, fields: appliedFields })
  }

  const clearAppliedTemplate = () => {
    if (!appliedTemplate) return
    const templateId = appliedTemplate.id
    for (const field of appliedTemplate.fields) {
      if (valuesEqual(form.getValues(field.path), field.applied)) {
        const value =
          field.restoreEmptyString && (field.before === null || field.before === undefined)
            ? ""
            : field.before
        form.setValue(field.path, value as never, { shouldDirty: true, shouldTouch: true })
      }
    }
    setAppliedTemplate(null)
    window.setTimeout(() => {
      templateButtonRefs.current.get(templateId)?.focus()
    }, 0)
  }

  return (
    <form
      onSubmit={form.handleSubmit(onSubmit)}
      className="space-y-4 max-w-xl"
      aria-label="item-form"
    >
      {itemTemplates.length > 0 ? (
        <section className="space-y-2 rounded-md border bg-muted/30 p-3">
          <div className="flex items-center justify-between gap-3">
            <Label className="text-sm font-semibold">{t("items.form.templates")}</Label>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={clearAppliedTemplate}
              disabled={!appliedTemplate}
            >
              <RotateCcw className="h-4 w-4" />
              {t("items.form.clearTemplateValues")}
            </Button>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            {itemTemplates.map((template) => (
              <Button
                key={template.id}
                ref={(node) => {
                  templateButtonRefs.current.set(template.id, node)
                }}
                type="button"
                size="sm"
                variant={appliedTemplate?.id === template.id ? "secondary" : "outline"}
                aria-pressed={appliedTemplate?.id === template.id}
                className="min-w-0 justify-start"
                onClick={() => applyTemplate(template)}
              >
                <span className="truncate">{template.name}</span>
              </Button>
            ))}
          </div>
          {appliedTemplate ? (
            <div role="status" className="rounded-md border bg-background px-3 py-2 text-sm">
              <p className="flex items-center gap-2 font-medium">
                <CheckCircle2 className="h-4 w-4 text-primary" />
                {t("items.form.templateApplied", { name: appliedTemplate.name })}
              </p>
              <p className="mt-1 text-muted-foreground">
                {t("items.form.templateAppliedFields", {
                  count: appliedTemplate.fields.length,
                  fields: appliedTemplate.fields.map((field) => field.label).join(", "),
                })}
              </p>
            </div>
          ) : null}
        </section>
      ) : null}

      <div>
        <Label htmlFor="name">{t("items.form.name")}</Label>
        <Input id="name" {...form.register("name")} />
        {form.formState.errors.name && (
          <p role="alert" className="mt-1 text-sm text-destructive">
            {t(`items.form.validation.${form.formState.errors.name.message}`)}
          </p>
        )}
      </div>

      <div>
        <Label htmlFor="description">{t("items.form.description")}</Label>
        <Textarea id="description" rows={3} {...form.register("description")} />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label>{t("items.form.category")}</Label>
          <Select
            value={form.watch("category_id")?.toString() ?? "none"}
            onValueChange={(v) => form.setValue("category_id", v === "none" ? null : Number(v))}
          >
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="none">{t("items.form.noneOption")}</SelectItem>
              {flatCats.map((c) => (
                <SelectItem key={c.id} value={String(c.id)}>{c.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <Label>{t("items.form.location")}</Label>
          <Select
            value={form.watch("location_id")?.toString() ?? "none"}
            onValueChange={(v) => form.setValue("location_id", v === "none" ? null : Number(v))}
          >
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="none">{t("items.form.noneOption")}</SelectItem>
              {locations.map((l) => (
                <SelectItem key={l.id} value={String(l.id)}>
                  {[l.floor, l.room, l.zone].filter(Boolean).join(" / ")}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div>
        <Label htmlFor="quantity">{t("items.form.quantity")}</Label>
        <Input
          id="quantity"
          type="number"
          min={0}
          {...form.register("quantity")}
        />
        {form.formState.errors.quantity && (
          <p role="alert" className="mt-1 text-sm text-destructive">
            {t(`items.form.validation.${form.formState.errors.quantity.message}`)}
          </p>
        )}
      </div>

      <div>
        <Label>{t("items.form.tags")}</Label>
        <TagMultiSelect
          value={form.watch("tag_names")}
          onChange={(next) => form.setValue("tag_names", next)}
          suggestions={tagSuggestions}
        />
      </div>

      {customFields.length > 0 ? (
        <section className="space-y-3 rounded-md border p-4">
          <div>
            <h2 className="text-sm font-semibold">{t("items.form.customFields")}</h2>
            <p className="text-muted-foreground mt-1 text-sm">
              {t("items.form.customFieldsDescription")}
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {customFields.map((field) => {
              const fieldPath = `custom_values.${field.id}` as const
              const fieldId = `custom-field-${field.id}`

              if (field.field_type === "bool") {
                return (
                  <div key={field.id} className="flex items-center gap-2 rounded-md border px-3 py-2">
                    <Checkbox
                      id={fieldId}
                      checked={form.watch(fieldPath) === true}
                      onCheckedChange={(checked) => {
                        form.setValue(fieldPath, checked === true, { shouldDirty: true })
                      }}
                    />
                    <Label htmlFor={fieldId} className="leading-5">
                      {field.name}
                    </Label>
                  </div>
                )
              }

              const inputType =
                field.field_type === "number"
                  ? "number"
                  : field.field_type === "date"
                    ? "date"
                    : "text"
              const registerOptions =
                field.field_type === "number"
                  ? {
                      setValueAs: (value: string) =>
                        value.trim() === "" ? null : Number(value),
                    }
                  : {
                      setValueAs: (value: string) => (value.trim() === "" ? null : value),
                    }

              return (
                <div key={field.id}>
                  <Label htmlFor={fieldId}>{field.name}</Label>
                  <Input
                    id={fieldId}
                    type={inputType}
                    {...form.register(fieldPath, registerOptions)}
                  />
                </div>
              )
            })}
          </div>
        </section>
      ) : null}

      <div>
        <Label htmlFor="notes">{t("items.form.notes")}</Label>
        <Textarea id="notes" rows={2} {...form.register("notes")} />
      </div>

      <div>
        <Label>{t("items.form.image")}</Label>
        <ImageUpload
          imageId={form.watch("image_id") ?? null}
          onChange={(id) => form.setValue("image_id", id)}
        />
        <div className="mt-2">
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={aiBusy || !form.watch("image_id")}
            onClick={runAiSuggest}
          >
            {aiBusy ? t("items.form.aiRecognizing") : <><Sparkles className="mr-1 h-4 w-4" />{t("items.form.aiRecognize")}</>}
          </Button>
        </div>
      </div>

      <div className="flex gap-2">
        <Button type="submit" disabled={submitting}>
          {submitting ? t("items.form.saving") : t("items.form.save")}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel}>
          {t("items.form.cancel")}
        </Button>
      </div>
    </form>
  )
}
