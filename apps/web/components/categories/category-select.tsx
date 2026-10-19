"use client"

import { useMemo } from "react"
import { useTranslations } from "next-intl"

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { CategoryTreeNode } from "@/lib/api/categories"

export interface FlatCategory {
  id: number
  label: string
}

/** 深度優先攤平分類樹；子層以「— 」前綴表示層級（Select 無縮排能力）。 */
export function flattenCategories(
  nodes: CategoryTreeNode[],
  depth = 0,
): FlatCategory[] {
  const out: FlatCategory[] = []
  for (const node of nodes) {
    out.push({ id: node.id, label: `${"— ".repeat(depth)}${node.name}` })
    if (node.children && node.children.length > 0) {
      out.push(...flattenCategories(node.children, depth + 1))
    }
  }
  return out
}

/** 以完整名稱精確匹配分類（含子層）；找不到回 `null`。 */
export function findCategoryByName(
  nodes: CategoryTreeNode[],
  name: string,
): number | null {
  const target = name.trim()
  for (const node of nodes) {
    if (node.name === target) return node.id
    const child = findCategoryByName(node.children ?? [], target)
    if (child !== null) return child
  }
  return null
}

interface Props {
  value: number | null
  onChange: (id: number | null) => void
  categories: CategoryTreeNode[]
  /** 顯示用標籤（Select 觸發器的 aria-label）。 */
  label?: string
  testId?: string
}

/** 分類選擇器（攤平樹＋「未分類」選項）；物品表單與草稿卡共用。 */
export function CategorySelect({ value, onChange, categories, label, testId }: Props) {
  const t = useTranslations()
  const flat = useMemo(() => flattenCategories(categories), [categories])
  const ariaLabel = label ?? t("items.form.category")

  return (
    <Select
      value={value !== null ? String(value) : "none"}
      onValueChange={(next) => onChange(next === "none" ? null : Number(next))}
    >
      <SelectTrigger aria-label={ariaLabel} data-testid={testId}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="none">{t("items.form.noneOption")}</SelectItem>
        {flat.map((category) => (
          <SelectItem key={category.id} value={String(category.id)}>
            {category.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
