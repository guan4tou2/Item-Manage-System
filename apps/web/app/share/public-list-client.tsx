"use client"

import { useEffect, useState } from "react"
import { useLocale, useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { KindBadge } from "@/components/lists/kind-badge"
import { getPublicList, isPublicHttpLink, PublicListError, type PublicList } from "@/lib/api/public-list"
import { formatCurrency } from "@/lib/format/currency"

type State = { kind: "loading" | "missing" | "invalid" | "error" } | { kind: "success"; list: PublicList }

export function PublicListClient() {
  const t = useTranslations("publicList")
  const locale = useLocale()
  const [state, setState] = useState<State>({ kind: "loading" })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let controller: AbortController | undefined
    let current = 0
    const load = async () => {
      controller?.abort()
      controller = new AbortController()
      const signal = controller.signal
      const request = ++current
      const token = window.location.hash.slice(1)
      if (!token) { setState({ kind: "missing" }); return }
      setState({ kind: "loading" })
      try {
        const list = await getPublicList(token, signal)
        if (!signal.aborted && request === current) setState({ kind: "success", list })
      } catch (error) {
        if (!signal.aborted && request === current) setState({ kind: error instanceof PublicListError && error.status === 404 ? "invalid" : "error" })
      }
    }
    void load()
    window.addEventListener("hashchange", load)
    return () => { controller?.abort(); window.removeEventListener("hashchange", load) }
  }, [attempt])

  const date = (value: string) => new Intl.DateTimeFormat(locale, { dateStyle: "short" }).format(new Date(`${value}T00:00:00`))

  return <main className="mx-auto min-h-screen w-full max-w-2xl space-y-6 px-4 py-8 text-sm sm:px-6 sm:py-12">
    <p className="text-muted-foreground">{t("heading")}</p>
    <div aria-live="polite" aria-busy={state.kind === "loading"}>
      {state.kind === "loading" ? <div role="status" aria-label={t("loading")} className="space-y-4"><Skeleton className="h-8 w-2/3" /><Skeleton className="h-32 w-full" /></div>
        : state.kind === "success" ? <div className="min-w-0 space-y-6 break-words [overflow-wrap:anywhere]">
          <header className="space-y-3">
            <KindBadge kind={state.list.kind} />
            <h1 className="text-2xl font-semibold">{state.list.title}</h1>
            {state.list.description && <p className="whitespace-pre-wrap">{state.list.description}</p>}
            {(state.list.start_date || state.list.end_date) && <p className="tabular-nums text-muted-foreground">{[state.list.start_date, state.list.end_date].filter((value): value is string => Boolean(value)).map(date).join(" – ")}</p>}
            {state.list.currency && "budget" in state.list && <p className="tabular-nums">{t("budget")}: {formatCurrency(state.list.budget, state.list.currency, locale)}</p>}
          </header>
          {!state.list.entries.length ? <p className="text-muted-foreground">{t("empty")}</p> : <ul className="divide-y border-y">
            {state.list.entries.map((entry, index) => <li key={index} className="min-w-0 space-y-2 py-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 className={`min-w-0 font-medium ${entry.is_done ? "line-through text-muted-foreground" : ""}`}>{entry.name}</h2>
                <span className="text-xs text-muted-foreground">{entry.is_done ? t("done") : t("pending")}</span>
              </div>
              {entry.quantity != null && <p className="tabular-nums">{t("quantity")}: {entry.quantity}</p>}
              {entry.note && <p className="whitespace-pre-wrap text-muted-foreground">{entry.note}</p>}
              {entry.link && (isPublicHttpLink(entry.link) ? <a className="inline-block min-h-11 py-2 text-primary underline" href={entry.link} target="_blank" rel="noopener noreferrer nofollow">{entry.link}</a> : <p>{entry.link}</p>)}
              {state.list.currency && "price" in entry && <p className="tabular-nums">{t("price")}: {formatCurrency(entry.price, state.list.currency, locale)}</p>}
            </li>)}
          </ul>}
        </div> : <div className="space-y-4">
          <h1 className="text-2xl font-semibold">{t(state.kind)}</h1>
          <p className="text-muted-foreground">{t(state.kind === "error" ? "errorHelp" : "invalidHelp")}</p>
          {state.kind === "error" && <Button className="min-h-11" variant="outline" onClick={() => setAttempt(value => value + 1)}>{t("retry")}</Button>}
        </div>}
    </div>
    <footer className="border-t pt-4 text-xs text-muted-foreground">{t("readonly")}</footer>
  </main>
}
