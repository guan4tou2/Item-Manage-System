"use client"

import type { ReactNode } from "react"

import { useReadOnly } from "@/lib/auth/use-readonly"

/**
 * Phase 30（§5.5 viewer 旅程）：唯讀 viewer 時**不渲染**編輯入口（非禁用）。
 * 後端 403 僅為最後防線。
 */
export function EditableOnly({ children }: { children: ReactNode }) {
  const readOnly = useReadOnly()
  if (readOnly) return null
  return <>{children}</>
}
