"use client"

import { X } from "lucide-react"
import { useState, type KeyboardEvent } from "react"
import { useTranslations } from "next-intl"

import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"

interface Props {
  value: string[]
  onChange: (next: string[]) => void
  suggestions?: string[]
}

export function TagMultiSelect({ value, onChange, suggestions = [] }: Props) {
  const t = useTranslations()
  const [draft, setDraft] = useState("")

  const commit = () => {
    const cleaned = draft.trim().toLowerCase()
    if (!cleaned) return
    if (value.includes(cleaned)) {
      setDraft("")
      return
    }
    onChange([...value, cleaned])
    setDraft("")
  }

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault()
      commit()
    } else if (e.key === "Backspace" && draft === "" && value.length > 0) {
      onChange(value.slice(0, -1))
    }
  }

  const remove = (name: string) => onChange(value.filter((v) => v !== name))

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1 rounded-md border px-2 py-2">
        {value.map((name) => (
          <Badge key={name} variant="secondary" className="gap-1">
            {name}
            <button type="button" onClick={() => remove(name)} aria-label={`remove ${name}`}>
              <X className="h-3 w-3" />
            </button>
          </Badge>
        ))}
        <Input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          onBlur={commit}
          placeholder={t("items.form.tagsPlaceholder")}
          className="h-7 flex-1 border-0 p-0 focus-visible:ring-0"
          list="tag-suggestions"
        />
      </div>
      {suggestions.length > 0 && (
        <datalist id="tag-suggestions">
          {suggestions.filter((s) => !value.includes(s)).map((s) => (
            <option key={s} value={s} />
          ))}
        </datalist>
      )}
    </div>
  )
}
