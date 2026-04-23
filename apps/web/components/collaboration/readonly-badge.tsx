"use client"
import { Lock } from "lucide-react"
import { useTranslations } from "next-intl"

export function ReadonlyBadge({ ownerUsername }: { ownerUsername: string }) {
  const t = useTranslations()
  return (
    <div className="flex items-center gap-2 rounded border bg-muted px-3 py-1.5 text-sm text-muted-foreground">
      <Lock className="h-3.5 w-3.5" />
      {t("collab.readonly.sharedBy", { username: ownerUsername })}
    </div>
  )
}
