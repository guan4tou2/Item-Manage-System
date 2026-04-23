"use client"
import Link from "next/link"
import { useTranslations } from "next-intl"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import type { GroupSummary } from "@/lib/api/groups"

export function GroupCard({ row }: { row: GroupSummary }) {
  const t = useTranslations()
  return (
    <Link href={`/collaboration/groups/${row.id}` as never} className="block no-underline">
      <Card className="transition-shadow hover:shadow-md">
        <CardHeader className="flex flex-row items-start justify-between gap-2 pb-2">
          <CardTitle className="text-base">{row.name}</CardTitle>
          {row.is_owner ? <Badge variant="secondary">{t("collab.groups.youAreOwner")}</Badge> : null}
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          {t("collab.groups.memberCount", { count: row.member_count })} · {row.owner_username}
        </CardContent>
      </Card>
    </Link>
  )
}
