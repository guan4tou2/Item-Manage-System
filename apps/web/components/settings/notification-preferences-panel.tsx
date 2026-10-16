"use client"

import Link from "next/link"
import { useTranslations } from "next-intl"
import { Lock, RotateCcw } from "lucide-react"

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import type { NotificationPreferencesResponse } from "@/lib/api/notification-preferences"
import {
  useNotificationPreferences,
  useResetNotificationPreferences,
  useUpdateNotificationPreferences,
} from "@/lib/hooks/use-notification-preferences"

type PreferenceType = NotificationPreferencesResponse["types"][number]

const GROUP_ORDER = ["items", "collab", "system"] as const

/** 類型標籤＋鎖定 icon（鎖定＝後端強制開啟，附 tooltip）。 */
function TypeLabel({ type }: { type: PreferenceType }) {
  const t = useTranslations("settings.notificationPreferences")
  return (
    <span className="flex items-center gap-1.5">
      <span className="text-sm font-medium">{t(`typeLabels.${type.key}`)}</span>
      {type.locked ? (
        <Tooltip>
          <TooltipTrigger asChild>
            <span
              aria-label={t("lockedTooltip")}
              className="text-muted-foreground inline-flex"
              role="img"
              tabIndex={0}
            >
              <Lock aria-hidden="true" className="size-3.5" />
            </span>
          </TooltipTrigger>
          <TooltipContent>{t("lockedTooltip")}</TooltipContent>
        </Tooltip>
      ) : null}
    </span>
  )
}

export function NotificationPreferencesPanel() {
  const t = useTranslations("settings.notificationPreferences")
  const { data, isError, isLoading, refetch } = useNotificationPreferences()
  const update = useUpdateNotificationPreferences()
  const reset = useResetNotificationPreferences()

  if (isLoading) {
    return (
      <div aria-busy="true" aria-label={t("loading")} className="space-y-4">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-40 animate-pulse rounded-lg border bg-muted/40" />
        ))}
      </div>
    )
  }

  if (isError || !data) {
    return (
      <Card className="border-dashed">
        <CardContent className="space-y-3 pt-6">
          <p className="text-muted-foreground text-sm">{t("loadError")}</p>
          <Button size="sm" variant="outline" onClick={() => refetch()}>
            {t("retry")}
          </Button>
        </CardContent>
      </Card>
    )
  }

  const onToggle = (type: string, channel: string, enabled: boolean) => {
    update.mutate([{ type, channel, enabled }])
  }

  const switchLabels = (type: PreferenceType, channel: string) =>
    t("toggleAria", {
      type: t(`typeLabels.${type.key}`),
      channel: t(`channelLabels.${channel}`),
    })

  const groups = GROUP_ORDER.map((id) => ({
    id,
    types: data.types.filter((type) => type.group === id),
  })).filter((group) => group.types.length > 0)

  return (
    <TooltipProvider delayDuration={200}>
      <div className="space-y-6">
        {!data.has_custom ? (
          <div
            className="rounded-lg border border-dashed bg-muted/40 p-4"
            data-testid="preferences-defaults-banner"
          >
            <p className="text-sm font-medium">{t("defaultsSummary")}</p>
            <p className="text-muted-foreground mt-1 text-xs">{t("defaultsDetail")}</p>
          </div>
        ) : (
          <div className="flex justify-end">
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button size="sm" variant="outline" disabled={reset.isPending}>
                  <RotateCcw aria-hidden="true" className="mr-1.5 size-4" />
                  {t("reset")}
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>{t("resetTitle")}</AlertDialogTitle>
                  <AlertDialogDescription>{t("resetBody")}</AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>{t("cancel")}</AlertDialogCancel>
                  <AlertDialogAction onClick={() => reset.mutate()}>
                    {t("resetConfirm")}
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        )}

        {groups.map((group) => (
          <Card key={group.id}>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">{t(`groups.${group.id}`)}</CardTitle>
            </CardHeader>
            <CardContent>
              {/* 桌面：矩陣表（列＝類型、欄＝管道） */}
              <div className="hidden md:block" data-testid={`preferences-matrix-${group.id}`}>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-44">{t("typeColumn")}</TableHead>
                      {data.channels.map((channel) => (
                        <TableHead className="text-center" key={channel}>
                          <span className="flex flex-col items-center gap-0.5">
                            {t(`channelLabels.${channel}`)}
                            {!data.channel_availability[channel] ? (
                              <Link
                                className="text-primary text-xs font-normal underline"
                                href="/settings/channels"
                              >
                                {t("goLink")}
                              </Link>
                            ) : null}
                          </span>
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {group.types.map((type) => (
                      <TableRow key={type.key}>
                        <TableCell>
                          <TypeLabel type={type} />
                        </TableCell>
                        {data.channels.map((channel) => (
                          <TableCell className="text-center" key={channel}>
                            <Switch
                              aria-label={switchLabels(type, channel)}
                              checked={data.matrix[type.key]?.[channel] ?? false}
                              disabled={type.locked || !data.channel_availability[channel]}
                              onCheckedChange={(checked) =>
                                onToggle(type.key, channel, checked)
                              }
                            />
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* 行動（<md）：每類型卡片；寬表格卡片化（§5.7） */}
              <div className="space-y-3 md:hidden" data-testid={`preferences-cards-${group.id}`}>
                {group.types.map((type) => (
                  <div className="rounded-lg border p-3" key={type.key}>
                    <TypeLabel type={type} />
                    <div className="mt-3 space-y-3">
                      {data.channels.map((channel) => (
                        <div
                          className="flex items-center justify-between gap-3"
                          key={channel}
                        >
                          <span className="text-sm">{t(`channelLabels.${channel}`)}</span>
                          <span className="flex items-center gap-3">
                            {!data.channel_availability[channel] ? (
                              <Link
                                className="text-primary text-xs underline"
                                href="/settings/channels"
                              >
                                {t("goLink")}
                              </Link>
                            ) : null}
                            <Switch
                              aria-label={switchLabels(type, channel)}
                              checked={data.matrix[type.key]?.[channel] ?? false}
                              disabled={type.locked || !data.channel_availability[channel]}
                              onCheckedChange={(checked) =>
                                onToggle(type.key, channel, checked)
                              }
                            />
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </TooltipProvider>
  )
}
