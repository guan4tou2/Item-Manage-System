'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, ClipboardCheck, PackageSearch, RotateCcw, XCircle } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { toast } from 'sonner'

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Badge } from '@/components/ui/badge'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
} from '@/components/ui/breadcrumb'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { listItems, type ItemRead } from '@/lib/api/items'
import {
  cancelStocktake,
  completeStocktake,
  createStocktake,
  getStocktake,
  listStocktakes,
  scanStocktakeItem,
  type StocktakeDetail,
  type StocktakeRead,
} from '@/lib/api/stocktakes'
import { useAccessToken } from '@/lib/auth/use-auth'
import { cn } from '@/lib/utils'

function formatDate(value: string | null | undefined) {
  if (!value) return '—'
  return new Date(value).toLocaleString()
}

function statusVariant(status: StocktakeRead['status']) {
  if (status === 'open') return 'default'
  if (status === 'completed') return 'secondary'
  return 'outline'
}

function StatusBadge({ status }: { status: StocktakeRead['status'] }) {
  const t = useTranslations()
  return <Badge variant={statusVariant(status)}>{t(`stocktakes.status.${status}`)}</Badge>
}

function deltaTone(delta: number) {
  if (delta === 0) return 'text-muted-foreground'
  if (delta > 0) return 'text-emerald-600 dark:text-emerald-400'
  return 'text-destructive'
}

function formatDelta(delta: number) {
  return delta > 0 ? `+${delta}` : String(delta)
}

type ScannedRow = StocktakeDetail['items'][number]

function rowDelta(row: ScannedRow) {
  return row.actual_quantity - row.expected_quantity
}

function summarizeRows(rows: ScannedRow[]) {
  return rows.reduce(
    (summary, row) => {
      const delta = rowDelta(row)
      if (delta === 0) summary.matched += 1
      else if (delta < 0) summary.missing += 1
      else summary.over += 1
      summary.totalDelta += delta
      return summary
    },
    { matched: 0, missing: 0, over: 0, totalDelta: 0 },
  )
}

function itemLabel(item: ItemRead) {
  return `${item.name} (${item.quantity})`
}

function SummaryTile({
  label,
  value,
}: {
  label: string
  value: string | number
}) {
  return (
    <div className="rounded-md border bg-background px-3 py-2">
      <p className="text-muted-foreground text-xs">{label}</p>
      <p className="mt-1 text-lg font-semibold tabular-nums">{value}</p>
    </div>
  )
}

function ScannedItemCard({
  row,
  item,
}: {
  row: ScannedRow
  item: ItemRead | undefined
}) {
  const t = useTranslations()
  const delta = rowDelta(row)

  return (
    <div className="grid gap-3 rounded-md border p-3 sm:grid-cols-[minmax(0,1fr)_auto]">
      <div className="min-w-0">
        <Link
          href={`/items/${row.item_id}` as never}
          className="font-medium underline-offset-2 hover:underline"
        >
          {item?.name ?? row.item_id}
        </Link>
        <p className="text-muted-foreground mt-1 text-xs">
          {t('stocktakes.scannedAt', { date: formatDate(row.scanned_at) })}
        </p>
        {row.note ? (
          <p className="text-muted-foreground mt-2 break-words text-sm">{row.note}</p>
        ) : null}
      </div>
      <div className="grid grid-cols-3 gap-2 text-right sm:min-w-56">
        <SummaryTile label={t('stocktakes.expected')} value={row.expected_quantity} />
        <SummaryTile label={t('stocktakes.actual')} value={row.actual_quantity} />
        <div className="rounded-md border bg-background px-3 py-2">
          <p className="text-muted-foreground text-xs">{t('stocktakes.delta')}</p>
          <p className={cn('mt-1 text-lg font-semibold tabular-nums', deltaTone(delta))}>
            {formatDelta(delta)}
          </p>
        </div>
      </div>
    </div>
  )
}

function SessionRow({
  active,
  row,
  onSelect,
}: {
  active: boolean
  row: StocktakeRead
  onSelect: () => void
}) {
  const t = useTranslations()
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        'w-full rounded-lg border p-4 text-left transition-colors hover:bg-accent/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
        active && 'border-primary bg-primary/5',
      )}
    >
      <div className="flex flex-wrap items-center gap-2">
        <p className="font-medium">{row.name}</p>
        <StatusBadge status={row.status} />
      </div>
      <p className="text-muted-foreground mt-1 text-xs">
        {t('stocktakes.startedAt', { date: formatDate(row.started_at) })}
      </p>
      <div className="mt-3 grid grid-cols-2 gap-2">
        <SummaryTile label={t('stocktakes.itemCount')} value={row.item_count} />
        <SummaryTile label={t('stocktakes.discrepancyCount')} value={row.discrepancy_count} />
      </div>
    </button>
  )
}

function ScannedItems({
  detail,
  itemsById,
}: {
  detail: StocktakeDetail | undefined
  itemsById: Map<string, ItemRead>
}) {
  const t = useTranslations()
  const rows = detail?.items ?? []

  if (rows.length === 0) {
    return (
      <div className="text-muted-foreground rounded-md border border-dashed p-4 text-sm">
        {t('stocktakes.noScans')}
      </div>
    )
  }

  const groups = [
    {
      key: 'matched',
      label: t('stocktakes.groups.matched', {
        count: rows.filter((row) => rowDelta(row) === 0).length,
      }),
      rows: rows.filter((row) => rowDelta(row) === 0),
    },
    {
      key: 'missing',
      label: t('stocktakes.groups.missing', {
        count: rows.filter((row) => rowDelta(row) < 0).length,
      }),
      rows: rows.filter((row) => rowDelta(row) < 0),
    },
    {
      key: 'over',
      label: t('stocktakes.groups.over', {
        count: rows.filter((row) => rowDelta(row) > 0).length,
      }),
      rows: rows.filter((row) => rowDelta(row) > 0),
    },
  ]

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {groups.map((group) => (
          <Badge key={group.key} variant="outline">{group.label}</Badge>
        ))}
      </div>
      {groups.filter((group) => group.rows.length > 0).map((group) => (
        <section key={group.key} aria-label={group.label} className="space-y-2">
          <h3 className="text-sm font-semibold">{group.label}</h3>
          {group.rows.map((row) => (
            <ScannedItemCard key={row.id} row={row} item={itemsById.get(row.item_id)} />
          ))}
        </section>
      ))}
    </div>
  )
}

export function StocktakesClient() {
  const t = useTranslations()
  const token = useAccessToken()
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [itemId, setItemId] = useState('')
  const [actualQuantity, setActualQuantity] = useState('')
  const [note, setNote] = useState('')
  const [scanLiveMessage, setScanLiveMessage] = useState('')
  const [completeConfirmOpen, setCompleteConfirmOpen] = useState(false)
  const itemSelectRef = useRef<HTMLSelectElement>(null)

  const stocktakesQuery = useQuery({
    queryKey: ['stocktakes'],
    queryFn: () => listStocktakes(token),
    enabled: token !== null,
  })

  const itemsQuery = useQuery({
    queryKey: ['items', { page: 1, perPage: 100 }],
    queryFn: () => listItems({ page: 1, perPage: 100 }, token),
    enabled: token !== null,
  })

  const stocktakes = useMemo(() => stocktakesQuery.data ?? [], [stocktakesQuery.data])

  useEffect(() => {
    if (stocktakes.length === 0) {
      setSelectedId(null)
      return
    }
    if (!selectedId || !stocktakes.some((row) => row.id === selectedId)) {
      setSelectedId(stocktakes[0]?.id ?? null)
    }
  }, [selectedId, stocktakes])

  const detailQuery = useQuery({
    queryKey: ['stocktakes', selectedId],
    queryFn: () => getStocktake(selectedId!, token),
    enabled: token !== null && selectedId !== null,
  })

  const items = itemsQuery.data?.items ?? []
  const itemsById = useMemo(() => new Map(items.map((item) => [item.id, item])), [items])
  const selectedStocktake =
    stocktakes.find((row) => row.id === selectedId) ?? detailQuery.data ?? null
  const isOpen = selectedStocktake?.status === 'open'
  const actual = Number.parseInt(actualQuantity, 10)
  const canScan = isOpen && itemId.length > 0 && Number.isInteger(actual) && actual >= 0

  const invalidateStocktakes = (id?: string | null) => {
    queryClient.invalidateQueries({ queryKey: ['stocktakes'] })
    if (id) queryClient.invalidateQueries({ queryKey: ['stocktakes', id] })
  }

  const create = useMutation({
    mutationFn: () => createStocktake({ name: name.trim() }, token),
    onSuccess: (row) => {
      setName('')
      setSelectedId(row.id)
      toast.success(t('stocktakes.toast.created'))
      invalidateStocktakes(row.id)
    },
    onError: () => toast.error(t('stocktakes.toast.createFailed')),
  })

  const scan = useMutation({
    mutationFn: () =>
      scanStocktakeItem(
        selectedId!,
        {
          item_id: itemId,
          actual_quantity: actual,
          note: note.trim() ? note.trim() : null,
        },
        token,
      ),
    onSuccess: () => {
      setItemId('')
      setActualQuantity('')
      setNote('')
      setScanLiveMessage(t('stocktakes.readyForNext'))
      itemSelectRef.current?.focus()
      toast.success(t('stocktakes.toast.scanned'))
      invalidateStocktakes(selectedId)
    },
    onError: () => toast.error(t('stocktakes.toast.scanFailed')),
  })

  const complete = useMutation({
    mutationFn: () => completeStocktake(selectedId!, token),
    onSuccess: () => {
      setCompleteConfirmOpen(false)
      toast.success(t('stocktakes.toast.completed'))
      invalidateStocktakes(selectedId)
      queryClient.invalidateQueries({ queryKey: ['items'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
    },
    onError: () => toast.error(t('stocktakes.toast.resolveFailed')),
  })

  const cancel = useMutation({
    mutationFn: () => cancelStocktake(selectedId!, token),
    onSuccess: () => {
      toast.success(t('stocktakes.toast.cancelled'))
      invalidateStocktakes(selectedId)
    },
    onError: () => toast.error(t('stocktakes.toast.resolveFailed')),
  })

  const openCount = stocktakes.filter((row) => row.status === 'open').length
  const discrepancyTotal = stocktakes.reduce((sum, row) => sum + row.discrepancy_count, 0)
  const scannedTotal = stocktakes.reduce((sum, row) => sum + row.item_count, 0)
  const completionSummary = summarizeRows(detailQuery.data?.items ?? [])
  const hasCompletionDiscrepancies =
    completionSummary.missing > 0 ||
    completionSummary.over > 0 ||
    ((detailQuery.data?.items.length ?? 0) === 0 && (selectedStocktake?.discrepancy_count ?? 0) > 0)
  const requestComplete = () => {
    if (!isOpen || complete.isPending || cancel.isPending) return
    if (hasCompletionDiscrepancies) {
      setCompleteConfirmOpen(true)
      return
    }
    complete.mutate()
  }

  return (
    <section className="space-y-6 p-4 sm:p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbPage>{t('stocktakes.title')}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-3xl space-y-1">
          <h1 className="text-2xl font-semibold">{t('stocktakes.title')}</h1>
          <p className="text-muted-foreground text-sm">{t('stocktakes.subtitle')}</p>
        </div>
        <div className="grid gap-2 sm:grid-cols-3 lg:min-w-[28rem]">
          <SummaryTile label={t('stocktakes.openSessions')} value={openCount} />
          <SummaryTile label={t('stocktakes.scannedItems')} value={scannedTotal} />
          <SummaryTile label={t('stocktakes.discrepancies')} value={discrepancyTotal} />
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(18rem,0.8fr)_minmax(0,1.2fr)]">
        <aside className="space-y-4">
          <section className="rounded-lg border bg-card p-4">
            <div className="flex items-start gap-3">
              <div className="grid h-10 w-10 shrink-0 place-items-center rounded-md bg-primary/10 text-primary">
                <ClipboardCheck className="h-5 w-5" aria-hidden="true" />
              </div>
              <div>
                <h2 className="text-base font-semibold">{t('stocktakes.createTitle')}</h2>
                <p className="text-muted-foreground mt-1 text-sm">
                  {t('stocktakes.createDescription')}
                </p>
              </div>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_auto] xl:grid-cols-1">
              <div className="grid gap-2">
                <Label htmlFor="stocktake-name">{t('stocktakes.nameLabel')}</Label>
                <Input
                  id="stocktake-name"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder={t('stocktakes.namePlaceholder')}
                />
              </div>
              <Button onClick={() => create.mutate()} disabled={!name.trim() || create.isPending}>
                {create.isPending ? t('stocktakes.starting') : t('stocktakes.start')}
              </Button>
            </div>
          </section>

          <section className="space-y-3">
            <h2 className="text-base font-semibold">{t('stocktakes.sessionsTitle')}</h2>
            {stocktakesQuery.isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-28 w-full" />
                <Skeleton className="h-28 w-full" />
              </div>
            ) : stocktakes.length === 0 ? (
              <div className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
                {t('stocktakes.emptySessions')}
              </div>
            ) : (
              <div className="space-y-3">
                {stocktakes.map((row) => (
                  <SessionRow
                    key={row.id}
                    row={row}
                    active={row.id === selectedId}
                    onSelect={() => setSelectedId(row.id)}
                  />
                ))}
              </div>
            )}
          </section>
        </aside>

        <main className="space-y-4">
          <section className="rounded-lg border bg-card p-4">
            {selectedStocktake ? (
              <div className="space-y-5">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="text-base font-semibold">{selectedStocktake.name}</h2>
                      <StatusBadge status={selectedStocktake.status} />
                    </div>
                    <p className="text-muted-foreground mt-1 text-xs">
                      {t('stocktakes.startedAt', {
                        date: formatDate(selectedStocktake.started_at),
                      })}
                      {selectedStocktake.completed_at
                        ? ` · ${t('stocktakes.completedAt', {
                            date: formatDate(selectedStocktake.completed_at),
                          })}`
                        : ''}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => cancel.mutate()}
                      disabled={!isOpen || cancel.isPending || complete.isPending}
                    >
                      <XCircle className="h-4 w-4" aria-hidden="true" />
                      {t('stocktakes.cancel')}
                    </Button>
                    <Button
                      size="sm"
                      onClick={requestComplete}
                      disabled={!isOpen || complete.isPending || cancel.isPending}
                    >
                      <RotateCcw className="h-4 w-4" aria-hidden="true" />
                      {complete.isPending ? t('stocktakes.completing') : t('stocktakes.complete')}
                    </Button>
                    <AlertDialog open={completeConfirmOpen} onOpenChange={setCompleteConfirmOpen}>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <div className="flex items-center gap-2">
                            <AlertTriangle className="h-5 w-5 text-destructive" aria-hidden="true" />
                            <AlertDialogTitle>{t('stocktakes.confirmCompleteTitle')}</AlertDialogTitle>
                          </div>
                          <AlertDialogDescription>
                            {t('stocktakes.confirmCompleteBody')}
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <p className="rounded-md border bg-muted/40 px-3 py-2 text-sm">
                          {t('stocktakes.confirmCompleteSummary', {
                            matched: completionSummary.matched,
                            missing: completionSummary.missing,
                            over: completionSummary.over,
                            totalDelta: formatDelta(completionSummary.totalDelta),
                          })}
                        </p>
                        <AlertDialogFooter>
                          <AlertDialogCancel disabled={complete.isPending}>
                            {t('stocktakes.keepCounting')}
                          </AlertDialogCancel>
                          <AlertDialogAction
                            disabled={complete.isPending}
                            onClick={() => complete.mutate()}
                          >
                            {t('stocktakes.completeAnyway')}
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-3">
                  <SummaryTile label={t('stocktakes.itemCount')} value={selectedStocktake.item_count} />
                  <SummaryTile
                    label={t('stocktakes.discrepancyCount')}
                    value={selectedStocktake.discrepancy_count}
                  />
                  <SummaryTile
                    label={t('stocktakes.statusLabel')}
                    value={t(`stocktakes.status.${selectedStocktake.status}`)}
                  />
                </div>
              </div>
            ) : (
              <div className="text-muted-foreground rounded-md border border-dashed p-4 text-sm">
                {t('stocktakes.selectSession')}
              </div>
            )}
          </section>

          <section className="rounded-lg border bg-card p-4">
            <div className="flex items-start gap-3">
              <div className="grid h-10 w-10 shrink-0 place-items-center rounded-md bg-primary/10 text-primary">
                <PackageSearch className="h-5 w-5" aria-hidden="true" />
              </div>
              <div>
                <h2 className="text-base font-semibold">{t('stocktakes.scanTitle')}</h2>
                <p className="text-muted-foreground mt-1 text-sm">
                  {t('stocktakes.scanDescription')}
                </p>
              </div>
            </div>

            <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1.2fr)_9rem_minmax(0,1fr)_auto] lg:items-end">
              <div className="grid gap-2">
                <Label htmlFor="stocktake-item">{t('stocktakes.itemLabel')}</Label>
                <select
                  id="stocktake-item"
                  ref={itemSelectRef}
                  value={itemId}
                  onChange={(event) => setItemId(event.target.value)}
                  className="h-11 rounded-md border border-input bg-background px-3 text-sm"
                  disabled={!isOpen || items.length === 0}
                >
                  <option value="">{t('stocktakes.itemPlaceholder')}</option>
                  {items.map((item) => (
                    <option key={item.id} value={item.id}>
                      {itemLabel(item)}
                    </option>
                  ))}
                </select>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="stocktake-actual">{t('stocktakes.actualQuantity')}</Label>
                <Input
                  id="stocktake-actual"
                  inputMode="numeric"
                  min={0}
                  type="number"
                  value={actualQuantity}
                  onChange={(event) => setActualQuantity(event.target.value)}
                  disabled={!isOpen}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="stocktake-note">{t('stocktakes.noteLabel')}</Label>
                <Input
                  id="stocktake-note"
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  placeholder={t('stocktakes.notePlaceholder')}
                  disabled={!isOpen}
                />
              </div>
              <Button onClick={() => scan.mutate()} disabled={!canScan || scan.isPending}>
                {scan.isPending ? t('stocktakes.recording') : t('stocktakes.recordCount')}
              </Button>
            </div>
            <p aria-live="polite" className="sr-only">{scanLiveMessage}</p>

            {items.length === 0 && !itemsQuery.isLoading ? (
              <p className="text-muted-foreground mt-3 text-sm">{t('stocktakes.noItems')}</p>
            ) : null}
          </section>

          <section className="rounded-lg border bg-card p-4">
            <h2 className="text-base font-semibold">{t('stocktakes.scannedTitle')}</h2>
            <div className="mt-4">
              {detailQuery.isLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-24 w-full" />
                  <Skeleton className="h-24 w-full" />
                </div>
              ) : (
                <ScannedItems detail={detailQuery.data} itemsById={itemsById} />
              )}
            </div>
          </section>
        </main>
      </div>
    </section>
  )
}
