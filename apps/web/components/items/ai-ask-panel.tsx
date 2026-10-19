"use client"

import Link from "next/link"
import { useTranslations } from "next-intl"
import { useState } from "react"

import { AiMark } from "@/components/ai/ai-mark"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import type { AskResponse } from "@/lib/api/ai-search"
import { getApiErrorDetail } from "@/lib/api/client"
import { useAiAsk } from "@/lib/hooks/use-ai-search"

interface Props {
  /** 目前檢索結果的物品（作為問答上下文）。 */
  itemIds: string[]
}

const ERROR_CODES = ["ai_disabled", "quota_exhausted", "upstream_error", "ai_opt_in_required"] as const
type AskErrorCode = (typeof ERROR_CODES)[number]

function askErrorCode(error: unknown): AskErrorCode | null {
  const detail = getApiErrorDetail(error)
  return ERROR_CODES.find((code) => code === detail) ?? null
}

/**
 * 物品問答面板（Phase 34）。
 *
 * - 以目前結果為上下文（`itemIds`）；回答附引用連結與「以系統資料為限」聲明
 * - `grounded=false` → 資料不足文案（不顯示引用）
 * - 錯誤以代碼文案呈現；未開啟資料分享 → 引導至設定
 */
export function AiAskPanel({ itemIds }: Props) {
  const t = useTranslations()
  const ask = useAiAsk()
  const [question, setQuestion] = useState("")
  const [answer, setAnswer] = useState<AskResponse | null>(null)
  const [errorCode, setErrorCode] = useState<AskErrorCode | null>(null)

  const submit = async () => {
    const text = question.trim()
    if (!text) return
    setErrorCode(null)
    try {
      const result = await ask.mutateAsync({ question: text, itemIds })
      setAnswer(result)
    } catch (error) {
      setAnswer(null)
      setErrorCode(askErrorCode(error))
    }
  }

  return (
    <Card data-testid="ai-ask-panel">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{t("ai.ask.title")}</CardTitle>
        <p className="text-xs text-muted-foreground">{t("ai.ask.description")}</p>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap gap-2">
          <Input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") void submit()
            }}
            placeholder={t("ai.ask.placeholder")}
            aria-label={t("ai.ask.aria")}
            className="min-w-0 flex-1"
          />
          <Button
            type="button"
            onClick={() => void submit()}
            disabled={ask.isPending}
          >
            {ask.isPending ? t("ai.ask.thinking") : t("ai.ask.submit")}
          </Button>
        </div>

        {errorCode !== null ? (
          <div className="flex flex-wrap items-center gap-2">
            <p role="alert" className="text-sm text-destructive">
              {t(`ai.ask.errors.${errorCode}`)}
            </p>
            {errorCode === "ai_opt_in_required" ? (
              <Link
                href="/settings/preferences"
                className="text-sm font-medium text-primary underline-offset-2 hover:underline"
              >
                {t("ai.search.openSettings")}
              </Link>
            ) : null}
          </div>
        ) : null}

        {answer !== null ? (
          <div className="space-y-2" aria-live="polite">
            <div className="flex items-start gap-2">
              <AiMark className="mt-1 shrink-0" />
              <p className="text-sm whitespace-pre-wrap">
                {answer.grounded ? answer.answer : t("ai.ask.insufficient")}
              </p>
            </div>
            {answer.grounded && answer.citations.length > 0 ? (
              <div className="space-y-1">
                <p className="text-xs font-medium text-muted-foreground">
                  {t("ai.ask.citations")}
                </p>
                <ul className="space-y-1">
                  {answer.citations.map((citation) => (
                    <li key={citation.item_id} className="text-sm">
                      <Link
                        href={`/items/${citation.item_id}`}
                        className="font-medium underline-offset-2 hover:underline"
                      >
                        {citation.name}
                      </Link>
                      {citation.path ? (
                        <span className="ml-2 text-xs text-muted-foreground">
                          {citation.path}
                        </span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            <p className="text-xs text-muted-foreground">{t("ai.ask.disclaimer")}</p>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
