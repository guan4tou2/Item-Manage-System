"use client"

import Link from "next/link"
import { useTranslations } from "next-intl"
import { AlertTriangle, CheckCircle2, Clock, RotateCcw, XCircle } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { useJobStatus } from "@/lib/hooks/use-job-status"

const JOB_NAME = "expiry-scan"

/** 排程文件（docs/scheduling.md）完整範例連結。 */
const DOCS_URL =
  "https://github.com/guan4tou2/Item-Manage-System/blob/main/docs/scheduling.md"

const CRON_LINE =
  `0 9 * * * curl -fsS -X POST "$IMS_BASE_URL/api/jobs/${JOB_NAME}/run"` +
  ` -H "Authorization: Bearer $IMS_PAT"`

function RunStatus({ status }: { status: string }) {
  const t = useTranslations("settings.reminders")
  if (status === "succeeded") {
    return (
      <span className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
        <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
        {t("lastRunSucceeded")}
      </span>
    )
  }
  if (status === "failed") {
    return (
      <span className="flex items-center gap-1.5 text-destructive">
        <XCircle className="h-4 w-4" aria-hidden="true" />
        {t("lastRunFailed")}
      </span>
    )
  }
  return (
    <span className="text-muted-foreground flex items-center gap-1.5">
      <Clock className="h-4 w-4" aria-hidden="true" />
      {t("lastRunRunning")}
    </span>
  )
}

/** 提醒排程（唯讀）：目前門檻、上次執行、停跑警示與 cron 設定片段。 */
export function RemindersPanel() {
  const t = useTranslations("settings.reminders")
  const { data, isError, isLoading, refetch } = useJobStatus(JOB_NAME)

  if (isLoading) {
    return (
      <div aria-busy="true" aria-label={t("loading")} className="space-y-4">
        <Skeleton className="h-36 w-full" />
        <Skeleton className="h-36 w-full" />
      </div>
    )
  }

  if (isError || !data) {
    return (
      <Card>
        <CardContent className="flex flex-col items-start gap-3 py-6" role="alert">
          <p className="text-muted-foreground text-sm">{t("loadFailed")}</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RotateCcw aria-hidden="true" className="h-4 w-4" />
            {t("retry")}
          </Button>
        </CardContent>
      </Card>
    )
  }

  const last = data.last_run ?? null
  const warning =
    last === null
      ? t("warnNever")
      : data.stale
        ? t("warnStale", { hours: data.thresholds.stale_after_hours })
        : last.status === "failed"
          ? t("warnFailed")
          : null

  return (
    <div className="space-y-4">
      {warning ? (
        <div
          className="border-warning/40 bg-warning/5 flex items-start gap-2 rounded-md border px-3 py-2"
          role="status"
        >
          <AlertTriangle className="text-warning mt-0.5 h-4 w-4" aria-hidden="true" />
          <div className="space-y-2 text-sm">
            <p>{warning}</p>
            <div className="text-muted-foreground space-y-1.5 text-xs">
              <p>{t("setupCronHint")}</p>
              <code className="bg-muted block overflow-x-auto rounded-[0.25rem] px-2 py-1">
                {CRON_LINE}
              </code>
              <p>
                {t("setupPatHint")}{" "}
                <Link className="underline" href="/settings/tokens">
                  {t("setupPatLink")}
                </Link>
                {" · "}
                {t("setupDocsHint")}{" "}
                <a className="underline" href={DOCS_URL} rel="noreferrer" target="_blank">
                  {t("setupDocsLink")}
                </a>
              </p>
            </div>
          </div>
        </div>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("thresholdsTitle")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <ul className="space-y-1 text-sm">
            {(data.thresholds.advance_days ?? []).map((days) => (
              <li key={days}>
                {days === 0 ? t("thresholdDueToday") : t("thresholdAdvance", { days })}
              </li>
            ))}
            {data.thresholds.expired_stop_days != null ? (
              <li>
                {t("thresholdExpiredStop", { days: data.thresholds.expired_stop_days })}
              </li>
            ) : null}
          </ul>
          <p className="text-muted-foreground text-xs">{t("thresholdsNote")}</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("lastRunTitle")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {last === null ? (
            <p className="text-muted-foreground">{t("lastRunNever")}</p>
          ) : (
            <>
              <p className="flex flex-wrap items-center gap-2">
                <RunStatus status={last.status} />
                <span className="text-muted-foreground">
                  {new Date(last.started_at).toLocaleString()}
                </span>
              </p>
              {last.result ? (
                <p className="text-muted-foreground text-xs">
                  {t("lastRunSummary", {
                    processed: Number(last.result.processed ?? 0),
                    emitted: Number(last.result.emitted ?? 0),
                  })}
                </p>
              ) : null}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
