"use client"

import { useTranslations } from "next-intl"

import { LocationsPanel } from "@/components/taxonomy/locations-panel"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
} from "@/components/ui/breadcrumb"

export default function LocationsPage() {
  const t = useTranslations()
  return (
    <section className="space-y-4 p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbPage>{t("nav.locations")}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
      <h1 className="text-2xl font-semibold">{t("nav.locations")}</h1>
      <LocationsPanel />
    </section>
  )
}
