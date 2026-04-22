"use client"

import { useRouter } from "next/navigation"
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
import { useCategories } from "@/lib/hooks/use-categories"
import { useCreateItem } from "@/lib/hooks/use-items"
import { useLocations } from "@/lib/hooks/use-locations"
import { useTags } from "@/lib/hooks/use-tags"

const empty: ItemFormValues = {
  name: "",
  description: "",
  category_id: null,
  location_id: null,
  quantity: 1,
  notes: "",
  tag_names: [],
}

export default function NewItemPage() {
  const t = useTranslations()
  const router = useRouter()
  const create = useCreateItem()
  const cats = useCategories()
  const locs = useLocations()
  const tags = useTags()

  async function handleSubmit(values: ItemFormValues) {
    const created = await create.mutateAsync({
      name: values.name,
      description: values.description || undefined,
      category_id: values.category_id ?? undefined,
      location_id: values.location_id ?? undefined,
      quantity: values.quantity,
      notes: values.notes || undefined,
      tag_names: values.tag_names,
    })
    toast.success(t("items.toast.created"))
    router.push(`/items/${created.id}`)
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
            <BreadcrumbPage>{t("items.list.new")}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
      <h1 className="text-2xl font-semibold">{t("items.list.new")}</h1>
      <ItemForm
        defaultValues={empty}
        onSubmit={handleSubmit}
        onCancel={() => router.push("/items")}
        submitting={create.isPending}
        categories={cats.data ?? []}
        locations={locs.data ?? []}
        tagSuggestions={(tags.data ?? []).map((tag) => tag.name)}
      />
    </section>
  )
}
