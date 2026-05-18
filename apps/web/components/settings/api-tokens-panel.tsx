"use client"
import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import * as api from "@/lib/api/api-tokens"
import { useAccessToken } from "@/lib/auth/use-auth"

export function ApiTokensPanel() {
  const t = useTranslations()
  const token = useAccessToken()
  const qc = useQueryClient()
  const list = useQuery({
    queryKey: ["api-tokens"],
    queryFn: () => api.listTokens(token),
    enabled: token !== null,
  })
  const create = useMutation({
    mutationFn: (name: string) => api.createToken(name, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["api-tokens"] }),
  })
  const del = useMutation({
    mutationFn: (id: string) => api.deleteToken(id, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["api-tokens"] }),
  })
  const [name, setName] = useState("")
  const [newToken, setNewToken] = useState<string | null>(null)

  const onCreate = async () => {
    if (!name.trim()) return
    const res = await create.mutateAsync(name.trim())
    setNewToken(res.token)
    setName("")
  }

  return (
    <div className="max-w-2xl space-y-4">
      {newToken ? (
        <div className="rounded border border-amber-500 bg-amber-50 p-3 text-sm dark:bg-amber-950">
          <p className="font-medium">{t("settings.tokens.created")}</p>
          <code className="mt-1 block break-all rounded bg-background p-2 font-mono text-xs">
            {newToken}
          </code>
          <Button size="sm" variant="outline" className="mt-2" onClick={() => setNewToken(null)}>
            {t("settings.tokens.copied")}
          </Button>
        </div>
      ) : null}

      <div className="flex gap-2">
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={t("settings.tokens.namePlaceholder")}
        />
        <Button onClick={onCreate} disabled={!name.trim() || create.isPending}>
          {t("settings.tokens.create")}
        </Button>
      </div>

      <ul className="divide-y rounded border">
        {(list.data ?? []).length === 0 ? (
          <li className="p-3 text-sm text-muted-foreground">{t("settings.tokens.empty")}</li>
        ) : (
          list.data?.map((tk) => (
            <li key={tk.id} className="flex items-center justify-between p-3 text-sm">
              <div>
                <p className="font-medium">{tk.name}</p>
                <p className="text-xs text-muted-foreground">
                  {t("settings.tokens.createdAt", { date: new Date(tk.created_at).toLocaleString() })}
                  {tk.last_used_at ? ` · ${t("settings.tokens.lastUsed", { date: new Date(tk.last_used_at).toLocaleString() })}` : ` · ${t("settings.tokens.neverUsed")}`}
                </p>
              </div>
              <Button size="sm" variant="ghost" onClick={() => del.mutate(tk.id)}>
                {t("settings.tokens.delete")}
              </Button>
            </li>
          ))
        )}
      </ul>
    </div>
  )
}
