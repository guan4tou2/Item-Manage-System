"use client"
import { useTranslations } from "next-intl"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { useBootstrapAdmin, useMe } from "@/lib/hooks/use-profile"

export function BootstrapAdminButton() {
  const t = useTranslations()
  const me = useMe()
  const bootstrap = useBootstrapAdmin()
  const onClick = async () => {
    try {
      await bootstrap.mutateAsync()
      toast.success(t("settings.bootstrap.success"))
    } catch (e: unknown) {
      const err = e as { body?: { detail?: string } }
      toast.error(err.body?.detail ?? "error")
    }
  }
  if (me.data?.is_admin) return null
  return (
    <div className="rounded border border-dashed p-4 space-y-2">
      <p className="text-sm text-muted-foreground">{t("settings.bootstrap.prompt")}</p>
      <Button size="sm" onClick={onClick} disabled={bootstrap.isPending}>
        {t("settings.bootstrap.confirm")}
      </Button>
    </div>
  )
}
