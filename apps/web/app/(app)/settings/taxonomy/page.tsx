"use client"

import { useTranslations } from "next-intl"

import { CategoriesPanel } from "@/components/taxonomy/categories-panel"
import { LocationsPanel } from "@/components/taxonomy/locations-panel"
import {
  Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

export default function TaxonomyPage() {
  const t = useTranslations()
  return (
    <section className="space-y-4 p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem><BreadcrumbLink href="/settings">{t("nav.settings")}</BreadcrumbLink></BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem><BreadcrumbPage>{t("nav.taxonomy")}</BreadcrumbPage></BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
      <h1 className="text-2xl font-semibold">{t("taxonomy.title")}</h1>

      <Tabs defaultValue="categories">
        <TabsList>
          <TabsTrigger value="categories">{t("taxonomy.tabs.categories")}</TabsTrigger>
          <TabsTrigger value="locations">{t("taxonomy.tabs.locations")}</TabsTrigger>
        </TabsList>
        <TabsContent value="categories"><CategoriesPanel /></TabsContent>
        <TabsContent value="locations"><LocationsPanel /></TabsContent>
      </Tabs>
    </section>
  )
}
