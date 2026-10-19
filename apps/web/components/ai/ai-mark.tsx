"use client"

import { Sparkles } from "lucide-react"
import { useTranslations } from "next-intl"

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"

/**
 * AI 產出標記（roadmap §5.6）：lucide `sparkles` ＋ 說明「由 AI 產生，可編輯」。
 *
 * - 僅加記號，不改變容器既有樣式（無漸層／發光／裝飾動畫）
 * - hover 與鍵盤 focus 皆可說明；`aria-label` 供螢幕閱讀器，tap target 可聚焦
 */
export function AiMark({ className }: { className?: string }) {
  const t = useTranslations("ai.mark")
  const label = t("tooltip")

  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span
            aria-label={label}
            className={cn("text-muted-foreground inline-flex", className)}
            role="img"
            tabIndex={0}
          >
            <Sparkles aria-hidden="true" className="size-3.5" />
          </span>
        </TooltipTrigger>
        <TooltipContent>{label}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
