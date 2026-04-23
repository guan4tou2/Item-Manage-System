"use client"

import { useTranslations } from "next-intl"

import { CategoriesPanel } from "@/components/taxonomy/categories-panel"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
} from "@/components/ui/breadcrumb"

export default function CategoriesPage() {
  const t = useTranslations()
  return (
    <section className="space-y-4 p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbPage>{t("nav.categories")}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
      <h1 className="text-2xl font-semibold">{t("nav.categories")}</h1>
      <CategoriesPanel />
    </section>
  )
}
