"use client"

import { useLocale, useTranslations } from "next-intl"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { isApiError } from "@/lib/api/client"
import { useCreateListShare, useListShares, useRevokeListShare } from "@/lib/hooks/use-list-shares"

function ShareDialogBody({ listId }: { listId: string }) {
  const t = useTranslations("listShare")
  const locale = useLocale()
  const list = useListShares(listId)
  const create = useCreateListShare(listId)
  const revoke = useRevokeListShare(listId)
  const [days, setDays] = useState("7")
  const [showPrices, setShowPrices] = useState(false)
  const [url, setUrl] = useState("")
  const [createdId, setCreatedId] = useState("")
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">("idle")
  const [error, setError] = useState("")
  const date = (value: string | null) => value ? new Date(value).toLocaleString(locale) : t("never")
  const limit = (list.data?.length ?? 0) >= 5

  async function onCreate() {
    setError("")
    setUrl("")
    setCopyState("idle")
    try {
      const result = await create.mutateAsync({
        expires_in_days: days === "forever" ? null : Number(days) as 1 | 7 | 30,
        show_prices: showPrices,
      })
      setUrl(`${window.location.origin}/share#${result.token}`)
      setCreatedId(result.id)
      create.reset()
    } catch (err) {
      setError(isApiError(err) && err.status === 409 ? t("limit") : t("createError"))
      create.reset()
    }
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(url)
      setCopyState("copied")
    } catch {
      setCopyState("failed")
    }
  }

  return <>
    <DialogHeader>
      <DialogTitle>{t("title")}</DialogTitle>
      <DialogDescription>{t("description")}</DialogDescription>
    </DialogHeader>
    <div className="min-w-0 space-y-4 text-sm" aria-live="polite">
      <div className="space-y-2">
        <Label htmlFor="share-expiry">{t("expiry")}</Label>
        <Select value={days} onValueChange={setDays} disabled={create.isPending}>
          <SelectTrigger id="share-expiry" className="min-h-11"><SelectValue /></SelectTrigger>
          <SelectContent>
            {["1", "7", "30", "forever"].map(value => <SelectItem className="min-h-11" key={value} value={value}>
              {value === "forever" ? t("forever") : t("days", { count: Number(value) })}
            </SelectItem>)}
          </SelectContent>
        </Select>
      </div>
      <div className="flex min-h-11 items-center justify-between gap-4">
        <Label htmlFor="share-prices">{t("showPrices")}</Label>
        <Switch id="share-prices" className="before:absolute before:inset-x-0 before:-inset-y-3 relative" checked={showPrices} onCheckedChange={setShowPrices} disabled={create.isPending} />
      </div>
      <Button className="min-h-11 w-full" onClick={onCreate} disabled={create.isPending || list.isLoading || list.isError || limit}>
        {create.isPending ? t("creating") : t("create")}
      </Button>
      {limit && <p role="status">{t("limit")}</p>}
      {error && <p role="alert" className="text-destructive">{error}</p>}
      {url && <div className="min-w-0 space-y-2 rounded-md border p-3">
        <p className="font-medium">{t("once")}</p>
        <Label htmlFor="share-url">{t("url")}</Label>
        <Input id="share-url" className="min-h-11 min-w-0 font-mono text-xs" value={url} readOnly onFocus={e => e.target.select()} />
        <Button className="min-h-11" variant="outline" onClick={copy}>{t("copy")}</Button>
        <p aria-live="polite">{copyState === "copied" ? t("copied") : copyState === "failed" ? t("copyFallback") : ""}</p>
      </div>}
      <h2 className="font-semibold">{t("existing")}</h2>
      {list.isLoading ? <div role="status" aria-label={t("loading")}><Skeleton className="h-24 w-full" /></div>
        : list.isError ? <div role="alert"><p>{t("loadError")}</p><Button className="min-h-11" variant="outline" onClick={() => list.refetch()}>{t("retry")}</Button></div>
        : !list.data?.length ? <p className="text-muted-foreground">{t("empty")}</p>
        : <ul className="divide-y">{list.data.map(share => <li key={share.id} className="min-w-0 space-y-2 py-3">
          <p className="font-mono">{share.token_prefix}…</p>
          <dl className="grid min-w-0 grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 tabular-nums">
            <dt>{t("createdAt")}</dt><dd className="break-words">{date(share.created_at)}</dd>
            <dt>{t("expiresAt")}</dt><dd className="break-words">{share.expires_at ? date(share.expires_at) : t("forever")}</dd>
            <dt>{t("showPrices")}</dt><dd>{share.show_prices ? t("yes") : t("no")}</dd>
            <dt>{t("lastAccessed")}</dt><dd className="break-words">{date(share.last_accessed_at)}</dd>
            <dt>{t("accessCount")}</dt><dd>{share.access_count}</dd>
          </dl>
          <AlertDialog>
            <AlertDialogTrigger asChild><Button className="min-h-11" variant="outline" disabled={revoke.isPending}>{t("revoke")}</Button></AlertDialogTrigger>
            <AlertDialogContent className="w-[calc(100%_-_2rem)] max-w-lg">
              <AlertDialogHeader><AlertDialogTitle>{t("confirmRevoke")}</AlertDialogTitle><AlertDialogDescription>{t("revokeDescription")}</AlertDialogDescription></AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel className="min-h-11">{t("cancel")}</AlertDialogCancel>
                <AlertDialogAction className="min-h-11" onClick={async () => {
                  setError("")
                  try {
                    await revoke.mutateAsync(share.id)
                    if (createdId === share.id) setUrl("")
                  } catch { setError(t("revokeError")) }
                }}>{t("revoke")}</AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </li>)}</ul>}
    </div>
  </>
}

export function ShareDialog({ listId }: { listId: string }) {
  const t = useTranslations("listShare")
  const [open, setOpen] = useState(false)
  return <Dialog open={open} onOpenChange={setOpen}>
    <DialogTrigger asChild><Button variant="outline" className="min-h-11">{t("title")}</Button></DialogTrigger>
    <DialogContent className="max-h-[85dvh] w-[calc(100%_-_2rem)] max-w-lg overflow-y-auto [&>button]:min-h-11 [&>button]:min-w-11 [&>button]:flex [&>button]:items-center [&>button]:justify-center">
      {open && <ShareDialogBody listId={listId} />}
    </DialogContent>
  </Dialog>
}
