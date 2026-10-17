"use client"

import { useState } from "react"
import { useTranslations } from "next-intl"
import { toast } from "sonner"

import { downloadBackup } from "@/lib/api/backup"
import { useAccessToken } from "@/lib/auth/use-auth"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export function BackupPanel() {
  const t = useTranslations()
  const token = useAccessToken()
  const [exporting, setExporting] = useState(false)

  async function handleExport() {
    setExporting(true)
    try {
      await downloadBackup(token)
      toast.success(t("settings.backup.export.toast.done"))
    } catch {
      toast.error(t("settings.backup.export.toast.failed"))
    } finally {
      setExporting(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("settings.backup.export.title")}</CardTitle>
        <CardDescription>{t("settings.backup.export.description")}</CardDescription>
      </CardHeader>
      <CardContent>
        <Button
          onClick={handleExport}
          disabled={exporting}
          className="max-sm:min-h-11"
        >
          {exporting
            ? t("settings.backup.export.preparing")
            : t("settings.backup.export.download")}
        </Button>
      </CardContent>
    </Card>
  )
}
