"use client"

import { zodResolver } from "@hookform/resolvers/zod"
import { useTranslations } from "next-intl"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { toast } from "sonner"
import { z } from "zod"

import { ImageUpload } from "./image-upload"
import { TagMultiSelect } from "./tag-multi-select"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { suggestFromImage } from "@/lib/api/ai"
import type { CategoryTreeNode } from "@/lib/api/categories"
import type { LocationRead } from "@/lib/api/locations"
import { useAccessToken } from "@/lib/auth/use-auth"

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
}

function flattenCategories(nodes: CategoryTreeNode[], depth = 0): Array<{ id: number; label: string }> {
  const out: Array<{ id: number; label: string }> = []
  for (const n of nodes) {
    out.push({ id: n.id, label: `${"— ".repeat(depth)}${n.name}` })
    if (n.children && n.children.length > 0) out.push(...flattenCategories(n.children, depth + 1))
  }
  return out
}

export function ItemForm({
  defaultValues, onSubmit, onCancel, submitting,
  categories, locations, tagSuggestions,
}: Props) {
  const t = useTranslations()
  const token = useAccessToken()
  const [aiBusy, setAiBusy] = useState(false)
  const form = useForm<ItemFormValues>({
    resolver: zodResolver(itemFormSchema),
    defaultValues,
  })
  const flatCats = flattenCategories(categories)

  const runAiSuggest = async () => {
    const imageId = form.getValues("image_id")
    if (!imageId) {
      toast.error("請先上傳圖片")
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
      toast.success("AI 已填入建議欄位")
    } catch (e: unknown) {
      const err = e as { body?: { detail?: string } }
      toast.error(err.body?.detail ?? "AI 辨識失敗")
    } finally {
      setAiBusy(false)
    }
  }

  return (
    <form
      onSubmit={form.handleSubmit(onSubmit)}
      className="space-y-4 max-w-xl"
      aria-label="item-form"
    >
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

      <div>
        <Label htmlFor="notes">{t("items.form.notes")}</Label>
        <Textarea id="notes" rows={2} {...form.register("notes")} />
      </div>

      <div>
        <Label>圖片</Label>
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
            {aiBusy ? "AI 辨識中…" : "✨ 使用 AI 辨識填入"}
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
