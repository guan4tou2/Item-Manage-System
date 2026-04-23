"use client"
import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import * as api from "@/lib/api/api-tokens"
import { useAccessToken } from "@/lib/auth/use-auth"

export function ApiTokensPanel() {
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
          <p className="font-medium">Token 建立成功，請立即複製（只會顯示這一次）：</p>
          <code className="mt-1 block break-all rounded bg-background p-2 font-mono text-xs">
            {newToken}
          </code>
          <Button size="sm" variant="outline" className="mt-2" onClick={() => setNewToken(null)}>
            我已複製
          </Button>
        </div>
      ) : null}

      <div className="flex gap-2">
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Token 名稱（例如：CI、手機 App）"
        />
        <Button onClick={onCreate} disabled={!name.trim() || create.isPending}>
          建立 Token
        </Button>
      </div>

      <ul className="divide-y rounded border">
        {(list.data ?? []).length === 0 ? (
          <li className="p-3 text-sm text-muted-foreground">尚無 Token</li>
        ) : (
          list.data?.map((t) => (
            <li key={t.id} className="flex items-center justify-between p-3 text-sm">
              <div>
                <p className="font-medium">{t.name}</p>
                <p className="text-xs text-muted-foreground">
                  建立於 {new Date(t.created_at).toLocaleString()}
                  {t.last_used_at ? ` · 上次使用 ${new Date(t.last_used_at).toLocaleString()}` : " · 從未使用"}
                </p>
              </div>
              <Button size="sm" variant="ghost" onClick={() => del.mutate(t.id)}>
                刪除
              </Button>
            </li>
          ))
        )}
      </ul>
    </div>
  )
}
