"use client"

import Link from "next/link"
import { useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"

const LINKS = [
  { href: "/items", key: "items" as const },
  { href: "/statistics", key: "stats" as const },
  { href: "/settings/taxonomy", key: "taxonomy" as const },
]

export function QuickLinks() {
  const t = useTranslations()
  return (
    <div className="flex flex-wrap gap-2">
      {LINKS.map(({ href, key }) => (
        <Button key={key} asChild variant="outline">
          <Link href={href as never}>{t(`dashboard.quickLinks.${key}`)}</Link>
        </Button>
      ))}
    </div>
  )
}
