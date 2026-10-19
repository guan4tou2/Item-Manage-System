import { Suspense } from "react"
import Link from "next/link"
import { useTranslations } from "next-intl"

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Skeleton } from "@/components/ui/skeleton"

import { DraftsClient } from "./drafts-client"

export default function DraftsPage() {
  const t = useTranslations()
  return (
    <section className="space-y-6 p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <Link href="/items">{t("nav.items")}</Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>{t("ai.drafts.title")}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold">{t("ai.drafts.title")}</h1>
          <p className="max-w-2xl text-sm text-muted-foreground">{t("ai.drafts.subtitle")}</p>
        </div>
        <Link
          href="/items/new"
          className="text-sm font-medium text-primary underline-offset-4 hover:underline"
        >
          {t("ai.drafts.backToNew")}
        </Link>
      </div>

      <Suspense fallback={<Skeleton className="h-40 w-full" />}>
        <DraftsClient />
      </Suspense>
    </section>
  )
}
