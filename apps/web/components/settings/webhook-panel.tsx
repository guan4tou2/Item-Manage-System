'use client'

import { useEffect, useMemo, useState } from 'react'
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Activity, CheckCircle2, Clock3, PlugZap, RefreshCcw, Trash2, XCircle } from 'lucide-react'
import { useTranslations } from 'next-intl'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  WEBHOOK_EVENTS,
  createWebhook,
  deleteWebhook,
  getWebhookDeliveryStats,
  listWebhookDeliveries,
  listWebhooks,
  processDueWebhookRetries,
  retryWebhookDelivery,
  updateWebhook,
  type ProcessRetriesResult,
  type WebhookDeliveryRead,
  type WebhookDeliveryStatus,
  type WebhookEvent,
  type WebhookRead,
} from '@/lib/api/webhooks'
import { getApiErrorMessages } from '@/lib/api/client'
import { useAccessToken } from '@/lib/auth/use-auth'
import { cn } from '@/lib/utils'

const DEFAULT_EVENTS: WebhookEvent[] = ['item.created', 'item.updated']

const DELIVERY_PAGE_SIZE = 20

type DeliveryFilter = 'all' | WebhookDeliveryStatus

const DELIVERY_FILTERS: { value: DeliveryFilter; labelKey: string }[] = [
  { value: 'all', labelKey: 'settings.webhooks.filter.all' },
  { value: 'success', labelKey: 'settings.webhooks.filter.success' },
  { value: 'failed', labelKey: 'settings.webhooks.filter.failed' },
  { value: 'pending', labelKey: 'settings.webhooks.filter.pending' },
]

function isSuccess(status: number | null) {
  return status !== null && status >= 200 && status < 300
}

function isRetryable(delivery: WebhookDeliveryRead) {
  return !isSuccess(delivery.status_code)
}

function statusTone(status: number | null) {
  if (isSuccess(status)) return 'text-emerald-600 dark:text-emerald-400'
  if (status === null) return 'text-amber-600 dark:text-amber-400'
  return 'text-destructive'
}

function formatDate(value: string | null) {
  if (!value) return '—'
  return new Date(value).toLocaleString()
}

function statusLabel(t: ReturnType<typeof useTranslations>, status: number | null) {
  if (status === null) return t('settings.webhooks.status.network')
  if (isSuccess(status)) return t('settings.webhooks.status.success', { status })
  return t('settings.webhooks.status.failed', { status })
}

function eventLabel(t: ReturnType<typeof useTranslations>, event: string) {
  if (event === 'item.created' || event === 'item.updated' || event === 'item.deleted') {
    return t(`settings.webhooks.events.${event}`)
  }
  return event
}

function WebhookStatusBadge({ webhook }: { webhook: WebhookRead }) {
  const t = useTranslations()
  if (!webhook.is_active) {
    return <Badge variant="secondary">{t('settings.webhooks.inactive')}</Badge>
  }
  if (isSuccess(webhook.last_status)) {
    return (
      <Badge className="bg-emerald-600 text-white hover:bg-emerald-600">
        {t('settings.webhooks.healthy')}
      </Badge>
    )
  }
  if (webhook.last_status !== null) {
    return <Badge variant="destructive">{t('settings.webhooks.needsAttention')}</Badge>
  }
  return <Badge variant="outline">{t('settings.webhooks.waiting')}</Badge>
}

function DeliveryStatus({ delivery }: { delivery: WebhookDeliveryRead }) {
  const t = useTranslations()
  const Icon = isSuccess(delivery.status_code)
    ? CheckCircle2
    : delivery.status_code === null
      ? Clock3
      : XCircle

  return (
    <div
      className={cn(
        'flex items-center gap-2 text-sm font-medium',
        statusTone(delivery.status_code),
      )}
    >
      <Icon className="h-4 w-4" aria-hidden="true" />
      <span>{statusLabel(t, delivery.status_code)}</span>
    </div>
  )
}

function RetryButton({
  retryPending,
  onClick,
}: {
  retryPending: boolean
  onClick: () => void
}) {
  const t = useTranslations()
  return (
    <Button variant="outline" size="sm" onClick={onClick} disabled={retryPending}>
      <RefreshCcw className="h-4 w-4" aria-hidden="true" />
      {retryPending ? t('settings.webhooks.retrying') : t('settings.webhooks.retryNow')}
    </Button>
  )
}

function ExcerptButton({ open, onToggle }: { open: boolean; onToggle: () => void }) {
  const t = useTranslations()
  return (
    <Button variant="ghost" size="sm" aria-expanded={open} onClick={onToggle}>
      {open ? t('settings.webhooks.excerptHide') : t('settings.webhooks.excerptShow')}
    </Button>
  )
}

function DeliveryTableRow({
  delivery,
  retryPending,
  onRetry,
}: {
  delivery: WebhookDeliveryRead
  retryPending: boolean
  onRetry: () => void
}) {
  const t = useTranslations()
  const [showExcerpt, setShowExcerpt] = useState(false)

  return (
    <>
      <TableRow>
        <TableCell className="text-muted-foreground whitespace-nowrap text-sm">
          {formatDate(delivery.created_at)}
        </TableCell>
        <TableCell className="text-sm font-medium">{eventLabel(t, delivery.event)}</TableCell>
        <TableCell>
          <DeliveryStatus delivery={delivery} />
        </TableCell>
        <TableCell>
          <Badge variant="outline">
            {t('settings.webhooks.attempt', { attempt: delivery.attempt })}
          </Badge>
        </TableCell>
        <TableCell className="text-muted-foreground whitespace-nowrap text-sm">
          {delivery.next_retry_at ? formatDate(delivery.next_retry_at) : '—'}
        </TableCell>
        <TableCell>
          <div className="flex justify-end gap-2">
            {delivery.response_excerpt ? (
              <ExcerptButton
                open={showExcerpt}
                onToggle={() => setShowExcerpt((open) => !open)}
              />
            ) : null}
            {isRetryable(delivery) ? (
              <RetryButton retryPending={retryPending} onClick={onRetry} />
            ) : null}
          </div>
        </TableCell>
      </TableRow>
      {showExcerpt && delivery.response_excerpt ? (
        <TableRow className="hover:bg-transparent">
          <TableCell colSpan={6} className="pt-0">
            <pre
              data-testid="delivery-excerpt"
              className="bg-muted text-muted-foreground max-h-24 overflow-auto whitespace-pre-wrap rounded-md p-3 text-xs"
            >
              {delivery.response_excerpt}
            </pre>
          </TableCell>
        </TableRow>
      ) : null}
    </>
  )
}

function DeliveryCard({
  delivery,
  retryPending,
  onRetry,
}: {
  delivery: WebhookDeliveryRead
  retryPending: boolean
  onRetry: () => void
}) {
  const t = useTranslations()
  const [showExcerpt, setShowExcerpt] = useState(false)

  return (
    <div className="rounded-lg border p-4">
      <div className="flex flex-wrap items-center gap-2">
        <DeliveryStatus delivery={delivery} />
        <Badge variant="outline">
          {t('settings.webhooks.attempt', { attempt: delivery.attempt })}
        </Badge>
        {delivery.next_retry_at ? (
          <Badge variant="secondary">{t('settings.webhooks.retryScheduled')}</Badge>
        ) : null}
      </div>
      <p className="mt-2 text-sm font-medium">{eventLabel(t, delivery.event)}</p>
      <p className="text-muted-foreground mt-1 text-xs">
        {t('settings.webhooks.createdAt', { date: formatDate(delivery.created_at) })}
        {delivery.next_retry_at
          ? ` · ${t('settings.webhooks.nextRetryAt', { date: formatDate(delivery.next_retry_at) })}`
          : ''}
      </p>
      {showExcerpt && delivery.response_excerpt ? (
        <pre
          data-testid="delivery-excerpt"
          className="bg-muted text-muted-foreground mt-3 max-h-24 overflow-auto whitespace-pre-wrap rounded-md p-3 text-xs"
        >
          {delivery.response_excerpt}
        </pre>
      ) : null}
      <div className="mt-3 flex flex-wrap gap-2">
        {delivery.response_excerpt ? (
          <ExcerptButton open={showExcerpt} onToggle={() => setShowExcerpt((open) => !open)} />
        ) : null}
        {isRetryable(delivery) ? (
          <RetryButton retryPending={retryPending} onClick={onRetry} />
        ) : null}
      </div>
    </div>
  )
}

export function WebhookPanel() {
  const t = useTranslations()
  const token = useAccessToken()
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [secret, setSecret] = useState('')
  const [events, setEvents] = useState<WebhookEvent[]>(DEFAULT_EVENTS)
  const [processResult, setProcessResult] = useState<ProcessRetriesResult | null>(null)
  const [deliveryFilter, setDeliveryFilter] = useState<DeliveryFilter>('all')

  const webhooksQuery = useQuery({
    queryKey: ['webhooks'],
    queryFn: () => listWebhooks(token),
    enabled: token !== null,
  })

  const webhooks = useMemo(() => webhooksQuery.data ?? [], [webhooksQuery.data])
  const selectedWebhook = webhooks.find((webhook) => webhook.id === selectedId) ?? null

  useEffect(() => {
    if (webhooks.length === 0) {
      setSelectedId(null)
      return
    }
    if (!selectedId || !webhooks.some((webhook) => webhook.id === selectedId)) {
      setSelectedId(webhooks[0]?.id ?? null)
    }
  }, [selectedId, webhooks])

  useEffect(() => {
    setDeliveryFilter('all')
  }, [selectedId])

  const deliveriesQuery = useInfiniteQuery({
    queryKey: ['webhooks', selectedId, 'deliveries', deliveryFilter],
    queryFn: ({ pageParam }) =>
      listWebhookDeliveries(
        selectedId!,
        {
          limit: DELIVERY_PAGE_SIZE,
          offset: pageParam,
          ...(deliveryFilter !== 'all' ? { status: deliveryFilter } : {}),
        },
        token,
      ),
    initialPageParam: 0,
    getNextPageParam: (lastPage, pages) =>
      lastPage.length === DELIVERY_PAGE_SIZE
        ? pages.length * DELIVERY_PAGE_SIZE
        : undefined,
    enabled: token !== null && selectedId !== null,
  })

  const deliveries = useMemo(
    () => deliveriesQuery.data?.pages.flat() ?? [],
    [deliveriesQuery.data],
  )

  const statsQuery = useQuery({
    queryKey: ['webhooks', selectedId, 'deliveries', 'stats'],
    queryFn: () => getWebhookDeliveryStats(selectedId!, token),
    enabled: token !== null && selectedId !== null,
  })

  const deliveryStats = statsQuery.data

  const create = useMutation({
    mutationFn: () =>
      createWebhook(
        {
          name: name.trim(),
          url: url.trim(),
          secret: secret.trim() ? secret.trim() : null,
          events,
        },
        token,
      ),
    onSuccess: (webhook) => {
      setName('')
      setUrl('')
      setSecret('')
      setEvents(DEFAULT_EVENTS)
      setSelectedId(webhook.id)
      queryClient.invalidateQueries({ queryKey: ['webhooks'] })
    },
  })

  const toggleActive = useMutation({
    mutationFn: (webhook: WebhookRead) =>
      updateWebhook(webhook.id, { is_active: !webhook.is_active }, token),
    onSuccess: (webhook) => {
      setSelectedId(webhook.id)
      queryClient.invalidateQueries({ queryKey: ['webhooks'] })
    },
  })

  const remove = useMutation({
    mutationFn: (webhookId: string) => deleteWebhook(webhookId, token),
    onSuccess: (_, webhookId) => {
      if (selectedId === webhookId) setSelectedId(null)
      queryClient.invalidateQueries({ queryKey: ['webhooks'] })
    },
  })

  const retry = useMutation({
    mutationFn: (delivery: WebhookDeliveryRead) =>
      retryWebhookDelivery(delivery.webhook_id, delivery.id, token),
    onSuccess: (delivery) => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] })
      queryClient.invalidateQueries({ queryKey: ['webhooks', delivery.webhook_id, 'deliveries'] })
    },
  })

  const processRetries = useMutation({
    mutationFn: () => processDueWebhookRetries(token),
    onSuccess: (result) => {
      setProcessResult(result)
      queryClient.invalidateQueries({ queryKey: ['webhooks'] })
      if (selectedId)
        queryClient.invalidateQueries({ queryKey: ['webhooks', selectedId, 'deliveries'] })
    },
  })

  const canCreate = name.trim().length > 0 && url.trim().length > 0 && events.length > 0

  const onEventChange = (event: WebhookEvent, checked: boolean | 'indeterminate') => {
    setEvents((current) => {
      if (checked === true) return current.includes(event) ? current : [...current, event]
      return current.filter((item) => item !== event)
    })
  }

  return (
    <div className="max-w-6xl space-y-6">
      <div className="grid gap-6 xl:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
        <section className="bg-card rounded-lg border p-4">
          <div className="flex items-start gap-3">
            <div className="bg-primary/10 text-primary grid h-10 w-10 shrink-0 place-items-center rounded-md">
              <PlugZap className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <h2 className="text-base font-semibold">{t('settings.webhooks.createTitle')}</h2>
              <p className="text-muted-foreground mt-1 text-sm">
                {t('settings.webhooks.createDescription')}
              </p>
            </div>
          </div>

          <div className="mt-5 space-y-4">
            <div className="grid gap-2">
              <Label htmlFor="webhook-name">{t('settings.webhooks.nameLabel')}</Label>
              <Input
                id="webhook-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder={t('settings.webhooks.namePlaceholder')}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="webhook-url">{t('settings.webhooks.urlLabel')}</Label>
              <Input
                id="webhook-url"
                type="url"
                value={url}
                onChange={(event) => setUrl(event.target.value)}
                placeholder="https://example.com/webhook"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="webhook-secret">{t('settings.webhooks.secretLabel')}</Label>
              <Input
                id="webhook-secret"
                value={secret}
                onChange={(event) => setSecret(event.target.value)}
                placeholder={t('settings.webhooks.secretPlaceholder')}
              />
              <p className="text-muted-foreground text-xs">{t('settings.webhooks.secretHelp')}</p>
            </div>
            <fieldset className="space-y-3">
              <legend className="text-sm font-medium">{t('settings.webhooks.eventsTitle')}</legend>
              <div className="grid gap-2 sm:grid-cols-3">
                {WEBHOOK_EVENTS.map((event) => (
                  <div
                    key={event}
                    className="flex min-h-11 items-center gap-2 rounded-md border px-3"
                  >
                    <Checkbox
                      id={`webhook-event-${event}`}
                      checked={events.includes(event)}
                      onCheckedChange={(checked) => onEventChange(event, checked)}
                    />
                    <Label htmlFor={`webhook-event-${event}`} className="cursor-pointer leading-5">
                      {eventLabel(t, event)}
                    </Label>
                  </div>
                ))}
              </div>
            </fieldset>
            {create.isError ? (
              <Alert variant="destructive">
                <AlertTitle>{t('settings.webhooks.createFailed')}</AlertTitle>
                <AlertDescription>
                  {getApiErrorMessages(create.error).some((m) => m.includes('webhook_url_not_allowed'))
                    ? t('settings.webhooks.urlNotAllowed')
                    : t('settings.webhooks.tryAgain')}
                </AlertDescription>
              </Alert>
            ) : null}
            <Button
              className="w-full sm:w-auto"
              onClick={() => create.mutate()}
              disabled={!canCreate || create.isPending}
            >
              {create.isPending ? t('settings.webhooks.creating') : t('settings.webhooks.create')}
            </Button>
          </div>
        </section>

        <section className="bg-card rounded-lg border p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h2 className="text-base font-semibold">{t('settings.webhooks.endpointsTitle')}</h2>
              <p className="text-muted-foreground mt-1 text-sm">
                {t('settings.webhooks.endpointsDescription')}
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => processRetries.mutate()}
              disabled={processRetries.isPending}
            >
              <RefreshCcw className="h-4 w-4" aria-hidden="true" />
              {processRetries.isPending
                ? t('settings.webhooks.processing')
                : t('settings.webhooks.processRetries')}
            </Button>
          </div>

          {processResult ? (
            <Alert className="mt-4">
              <Activity className="h-4 w-4" aria-hidden="true" />
              <AlertTitle>{t('settings.webhooks.processedTitle')}</AlertTitle>
              <AlertDescription>
                {t('settings.webhooks.processedSummary', {
                  processed: processResult.processed,
                  succeeded: processResult.succeeded,
                  remaining: processResult.remaining,
                })}
              </AlertDescription>
            </Alert>
          ) : null}

          <div className="mt-4 space-y-3">
            {webhooksQuery.isLoading ? (
              <p className="text-muted-foreground text-sm">{t('settings.webhooks.loading')}</p>
            ) : webhooksQuery.isError ? (
              <Alert variant="destructive">
                <AlertTitle>{t('settings.webhooks.listLoadFailed')}</AlertTitle>
                <AlertDescription>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-2"
                    onClick={() => webhooksQuery.refetch()}
                  >
                    {t('settings.webhooks.retryLoad')}
                  </Button>
                </AlertDescription>
              </Alert>
            ) : webhooks.length === 0 ? (
              <div className="rounded-md border border-dashed p-4">
                <p className="font-medium">{t('settings.webhooks.emptyTitle')}</p>
                <p className="text-muted-foreground mt-1 text-sm">
                  {t('settings.webhooks.emptyBody')}
                </p>
              </div>
            ) : (
              webhooks.map((webhook) => (
                <div
                  key={webhook.id}
                  className={cn(
                    'rounded-lg border p-4 transition-colors',
                    selectedId === webhook.id && 'border-primary bg-primary/5',
                  )}
                >
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <button
                      type="button"
                      onClick={() => setSelectedId(webhook.id)}
                      className="focus-visible:ring-ring min-w-0 flex-1 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-medium">{webhook.name}</p>
                        <WebhookStatusBadge webhook={webhook} />
                      </div>
                      <p className="text-muted-foreground mt-1 break-all text-sm">{webhook.url}</p>
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {webhook.events.length === 0 ? (
                          <Badge variant="outline">{t('settings.webhooks.allEvents')}</Badge>
                        ) : (
                          webhook.events.map((event) => (
                            <Badge key={event} variant="secondary">
                              {eventLabel(t, event)}
                            </Badge>
                          ))
                        )}
                      </div>
                    </button>
                    <div className="flex shrink-0 items-center gap-3">
                      <div className="flex items-center gap-2">
                        <Switch
                          checked={webhook.is_active}
                          onClick={(event) => event.stopPropagation()}
                          onCheckedChange={() => toggleActive.mutate(webhook)}
                          aria-label={t('settings.webhooks.toggleActive', { name: webhook.name })}
                          disabled={toggleActive.isPending}
                        />
                        <span className="text-muted-foreground text-sm">
                          {webhook.is_active
                            ? t('settings.webhooks.active')
                            : t('settings.webhooks.inactive')}
                        </span>
                      </div>
                      <Button
                        type="button"
                        size="icon"
                        variant="ghost"
                        aria-label={t('settings.webhooks.deleteWebhook', { name: webhook.name })}
                        onClick={(event) => {
                          event.stopPropagation()
                          remove.mutate(webhook.id)
                        }}
                        disabled={remove.isPending}
                      >
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </div>

      <section className="bg-card rounded-lg border p-4">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-base font-semibold">{t('settings.webhooks.deliveriesTitle')}</h2>
            <p className="text-muted-foreground mt-1 text-sm">
              {selectedWebhook
                ? t('settings.webhooks.deliveriesFor', { name: selectedWebhook.name })
                : t('settings.webhooks.selectWebhook')}
            </p>
          </div>
          {selectedWebhook ? (
            <p className="text-muted-foreground text-xs">
              {t('settings.webhooks.lastFired', {
                date: formatDate(selectedWebhook.last_fired_at),
              })}
            </p>
          ) : null}
        </div>

        {selectedWebhook && deliveryStats && deliveryStats.total > 0 ? (
          <p className="text-muted-foreground mt-2 text-sm" data-testid="deliveries-stats">
            {t('settings.webhooks.stats.successRate', {
              pct: Math.round((deliveryStats.succeeded / deliveryStats.total) * 100),
              succeeded: deliveryStats.succeeded,
              total: deliveryStats.total,
            })}
            {' · '}
            {t('settings.webhooks.stats.lastSuccess', {
              date: formatDate(deliveryStats.last_success_at),
            })}
          </p>
        ) : selectedWebhook && statsQuery.isLoading ? (
          <Skeleton
            className="mt-2 h-4 w-72"
            data-testid="deliveries-stats-loading"
          />
        ) : null}

        {selectedWebhook ? (
          <div className="mt-4 flex flex-wrap gap-2">
            {DELIVERY_FILTERS.map(({ value, labelKey }) => (
              <Button
                key={value}
                type="button"
                size="sm"
                variant={deliveryFilter === value ? 'default' : 'outline'}
                className="min-h-11"
                aria-pressed={deliveryFilter === value}
                onClick={() => setDeliveryFilter(value)}
              >
                {t(labelKey)}
              </Button>
            ))}
          </div>
        ) : null}

        <div className="mt-4 space-y-3">
          {!selectedWebhook ? (
            <div className="text-muted-foreground rounded-md border border-dashed p-4 text-sm">
              {t('settings.webhooks.noSelection')}
            </div>
          ) : deliveriesQuery.isError ? (
            <Alert variant="destructive">
              <AlertTitle>{t('settings.webhooks.loadFailed')}</AlertTitle>
              <AlertDescription>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2"
                  onClick={() => deliveriesQuery.refetch()}
                >
                  {t('settings.webhooks.retryLoad')}
                </Button>
              </AlertDescription>
            </Alert>
          ) : deliveriesQuery.isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-11 w-full" />
              <Skeleton className="h-11 w-full" />
              <Skeleton className="h-11 w-full" />
            </div>
          ) : deliveries.length === 0 ? (
            deliveryFilter !== 'all' ? (
              <div className="rounded-md border border-dashed p-4">
                <p className="font-medium">{t('settings.webhooks.filterEmptyTitle')}</p>
                <p className="text-muted-foreground mt-1 text-sm">
                  {t('settings.webhooks.filterEmptyBody')}
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  onClick={() => setDeliveryFilter('all')}
                >
                  {t('settings.webhooks.clearFilter')}
                </Button>
              </div>
            ) : (
              <div className="rounded-md border border-dashed p-4">
                <p className="font-medium">{t('settings.webhooks.noDeliveriesTitle')}</p>
                <p className="text-muted-foreground mt-1 text-sm">
                  {t('settings.webhooks.noDeliveriesBody')}
                </p>
              </div>
            )
          ) : (
            <>
              <div data-testid="deliveries-table" className="hidden md:block">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t('settings.webhooks.table.time')}</TableHead>
                      <TableHead>{t('settings.webhooks.table.event')}</TableHead>
                      <TableHead>{t('settings.webhooks.table.status')}</TableHead>
                      <TableHead>{t('settings.webhooks.table.attempt')}</TableHead>
                      <TableHead>{t('settings.webhooks.table.nextRetry')}</TableHead>
                      <TableHead className="text-right">
                        {t('settings.webhooks.table.actions')}
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {deliveries.map((delivery) => (
                      <DeliveryTableRow
                        key={delivery.id}
                        delivery={delivery}
                        retryPending={retry.isPending}
                        onRetry={() => retry.mutate(delivery)}
                      />
                    ))}
                  </TableBody>
                </Table>
              </div>
              <div data-testid="deliveries-cards" className="space-y-3 md:hidden">
                {deliveries.map((delivery) => (
                  <DeliveryCard
                    key={delivery.id}
                    delivery={delivery}
                    retryPending={retry.isPending}
                    onRetry={() => retry.mutate(delivery)}
                  />
                ))}
              </div>
              {deliveriesQuery.hasNextPage ? (
                <div className="mt-3 flex justify-center">
                  <Button
                    variant="outline"
                    onClick={() => deliveriesQuery.fetchNextPage()}
                    disabled={deliveriesQuery.isFetchingNextPage}
                  >
                    {deliveriesQuery.isFetchingNextPage
                      ? t('settings.webhooks.loadingMore')
                      : t('settings.webhooks.loadMore')}
                  </Button>
                </div>
              ) : null}
            </>
          )}
        </div>
      </section>
    </div>
  )
}
