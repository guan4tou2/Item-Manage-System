import { Suspense } from "react"
import { useTranslations } from "next-intl"

import {
  Breadcrumb, BreadcrumbItem, BreadcrumbList, BreadcrumbPage,
} from "@/components/ui/breadcrumb"
import { Skeleton } from "@/components/ui/skeleton"
import { ItemsListClient } from "./items-list-client"

export default function ItemsPage() {
  const t = useTranslations()
  return (
    <section className="space-y-4 p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbPage>{t("nav.items")}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
      <h1 className="text-2xl font-semibold">{t("nav.items")}</h1>
      <Suspense fallback={<Skeleton className="h-40 w-full" />}>
        <ItemsListClient />
      </Suspense>
    </section>
  )
}
