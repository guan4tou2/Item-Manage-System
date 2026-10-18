"use client"

import { useTranslations } from "next-intl"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { useReadOnly } from "@/lib/auth/use-readonly"
import {
  usePreferences,
  useUpdatePreferences,
} from "@/lib/preferences/use-preferences"

/**
 * Phase 30（§5.5 viewer 家人旅程）：首次登入一次性說明 banner。
 *
 * - 可關閉、**不重複**（狀態存 `users.preferences.viewer_notice_dismissed`）
 * - 偏好載入中不渲染（避免對非 viewer 或已關閉者閃爍）
 * - 關閉失敗：留在畫面＋錯誤 toast
 */
export function ViewerBanner() {
  const t = useTranslations()
  const readOnly = useReadOnly()
  const prefs = usePreferences()
  const update = useUpdatePreferences()

  const dismissed = prefs.data?.viewer_notice_dismissed ?? false
  if (!readOnly || prefs.isLoading || !prefs.data || dismissed) return null

  return (
    <div
      data-testid="viewer-banner"
      className="flex flex-wrap items-center justify-between gap-2 border-b bg-muted px-4 py-2"
    >
      <div className="min-w-0">
        <p className="text-sm font-medium">{t("viewer.banner.title")}</p>
        <p className="text-sm text-muted-foreground">{t("viewer.banner.body")}</p>
      </div>
      <Button
        variant="outline"
        size="sm"
        disabled={update.isPending}
        onClick={() =>
          update.mutate(
            { viewer_notice_dismissed: true },
            {
              onError: () => toast.error(t("viewer.banner.dismissFailed")),
            },
          )
        }
      >
        {t("viewer.banner.dismiss")}
      </Button>
    </div>
  )
}
