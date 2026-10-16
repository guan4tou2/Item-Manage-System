"use client"

import { Search } from "lucide-react"
import { useTranslations } from "next-intl"
import { useEffect, useMemo, useState } from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import type { LocationRead } from "@/lib/api/locations"
import { useLocations } from "@/lib/hooks/use-locations"
import { useIsMobile } from "@/lib/hooks/use-is-mobile"
import {
  ancestorChain,
  childrenOf,
  flattenList,
  searchNodes,
  type TreeFlatNode,
} from "@/lib/locations/tree"

const NONE = "none"

interface Props {
  value: number | null
  onChange: (id: number | null) => void
  nodes?: LocationRead[]
  allowNone?: boolean
  /** 顯示用標籤（桌面 Select 的 aria-label 前綴）。 */
  label?: string
  testId?: string
}

/**
 * 樹狀位置選擇器（§5.7）：
 * 桌機＝cascading 逐層下拉（可停在任一層）；行動＝bottom sheet＋扁平搜尋（顯示完整路徑）。
 */
export function LocationSelect({
  value,
  onChange,
  nodes,
  allowNone = true,
  label,
  testId,
}: Props) {
  const t = useTranslations()
  const queried = useLocations()
  const flat = useMemo(
    () => flattenList(nodes ?? queried.data ?? []),
    [nodes, queried.data],
  )
  const isMobile = useIsMobile()
  const [sheetOpen, setSheetOpen] = useState(false)
  const [query, setQuery] = useState("")
  const [levels, setLevels] = useState<number[]>([])

  // 外部 value 變動 → 還原 cascading 層級（含選取節點本身；內容相同時不改狀態，避免重繪迴圈）
  useEffect(() => {
    const next =
      value === null ? [] : [...ancestorChain(flat, value), value]
    setLevels((prev) =>
      prev.length === next.length && prev.every((id, index) => id === next[index])
        ? prev
        : next,
    )
  }, [value, flat])

  const noneLabel = t("items.form.noneOption")
  const selectedPath =
    value !== null ? (flat.find((node) => node.id === value)?.path ?? null) : null

  if (isMobile) {
    const results = searchNodes(flat, query)
    return (
      <div data-testid={testId}>
        <Button
          type="button"
          variant="outline"
          className="w-full justify-start font-normal"
          aria-label={label}
          onClick={() => setSheetOpen(true)}
        >
          {selectedPath ?? noneLabel}
        </Button>
        <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
          <SheetContent side="bottom" className="max-h-[80vh] overflow-y-auto">
            <SheetHeader>
              <SheetTitle>{label ?? t("items.form.location")}</SheetTitle>
            </SheetHeader>
            <div className="space-y-3 py-3">
              <div className="relative">
                <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder={t("locations.select.searchPlaceholder")}
                  aria-label={t("locations.select.searchPlaceholder")}
                  className="pl-8"
                />
              </div>
              <ul className="space-y-1">
                {allowNone ? (
                  <li>
                    <Button
                      type="button"
                      variant={value === null ? "secondary" : "ghost"}
                      className="w-full justify-start"
                      onClick={() => {
                        onChange(null)
                        setSheetOpen(false)
                      }}
                    >
                      {noneLabel}
                    </Button>
                  </li>
                ) : null}
                {results.map((node) => (
                  <li key={node.id}>
                    <Button
                      type="button"
                      variant={value === node.id ? "secondary" : "ghost"}
                      className="w-full justify-start"
                      onClick={() => {
                        onChange(node.id)
                        setSheetOpen(false)
                      }}
                    >
                      <span className="truncate">{node.path}</span>
                    </Button>
                  </li>
                ))}
                {results.length === 0 ? (
                  <li className="px-2 py-3 text-sm text-muted-foreground">
                    {t("locations.select.empty")}
                  </li>
                ) : null}
              </ul>
            </div>
          </SheetContent>
        </Sheet>
      </div>
    )
  }

  const maxLevel = levels.length
  const columns: Array<{ level: number; options: TreeFlatNode[] }> = []
  for (let level = 0; level <= maxLevel; level += 1) {
    const parentId = level === 0 ? null : (levels[level - 1] ?? null)
    const options = childrenOf(flat, parentId)
    if (options.length === 0) break
    columns.push({ level, options })
  }
  const choose = (level: number, rawValue: string) => {
    if (rawValue === NONE) {
      onChange(level === 0 ? null : (levels[level - 1] ?? null))
      setLevels(levels.slice(0, level))
      return
    }
    const id = Number(rawValue)
    const next = [...levels.slice(0, level), id]
    setLevels(next)
    onChange(id)
  }

  return (
    <div data-testid={testId} className="space-y-2">
      {columns.map(({ level, options }) => (
        <Select
          key={level}
          value={
            level === 0
              ? levels[0] !== undefined
                ? String(levels[0])
                : NONE
              : levels[level] !== undefined
                ? String(levels[level])
                : undefined
          }
          onValueChange={(next) => choose(level, next)}
        >
          <SelectTrigger aria-label={`${label ?? t("items.form.location")} ${level + 1}`}>
            <SelectValue
              placeholder={
                level === 0 ? undefined : t("locations.select.drillDeeper")
              }
            />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={NONE}>
              {level === 0 ? noneLabel : t("locations.select.stopHere")}
            </SelectItem>
            {options.map((option) => (
              <SelectItem key={option.id} value={String(option.id)}>
                {option.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      ))}
      {columns.length === 0 ? (
        <div className="space-y-1">
          <Label className="text-muted-foreground">
            {t("locations.select.noNodes")}
          </Label>
        </div>
      ) : null}
      {selectedPath ? (
        <p className="text-xs text-muted-foreground" data-testid="location-select-path">
          {selectedPath}
        </p>
      ) : null}
    </div>
  )
}
