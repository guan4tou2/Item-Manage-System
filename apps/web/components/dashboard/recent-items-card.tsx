"use client"

import Link from "next/link"
import { useTranslations } from "next-intl"

import type { RecentItem } from "@/lib/api/stats"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface Props {
  items: RecentItem[]
}

export function RecentItemsCard({ items }: Props) {
  const t = useTranslations()
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>{t("dashboard.recent.title")}</CardTitle>
        <Button asChild variant="link" size="sm">
          <Link href="/items">{t("dashboard.recent.viewAll")}</Link>
        </Button>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("dashboard.recent.empty")}</p>
        ) : (
          <ul className="divide-y">
            {items.map((item) => (
              <li key={item.id} className="py-2">
                <Link
                  href={`/items/${item.id}` as never}
                  className="block hover:underline"
                >
                  {item.name}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
