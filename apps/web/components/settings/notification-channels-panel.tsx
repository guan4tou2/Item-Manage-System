'use client'

import { useState } from 'react'
import type { ComponentType, ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  BellRing,
  CheckCircle2,
  Link2,
  Mail,
  MessageCircle,
  Send,
  SendHorizontal,
  Smartphone,
  Trash2,
  Unlink,
  XCircle,
} from 'lucide-react'
import { useTranslations } from 'next-intl'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  addWebPushSubscription,
  getChannelStatus,
  getVapidPublicKey,
  listWebPushSubscriptions,
  removeWebPushSubscription,
  setLineLink,
  setTelegramLink,
  subscribeBrowserWebPush,
  testChannel,
  unlinkLine,
  unlinkTelegram,
  type NotificationChannel,
} from '@/lib/api/channels'
import { useAccessToken } from '@/lib/auth/use-auth'
import { cn } from '@/lib/utils'

type ChannelCardProps = {
  actions: ReactNode
  children?: ReactNode
  configured: boolean
  description: string
  icon: ComponentType<{ className?: string }>
  linked?: boolean
  title: string
}

function StatusBadge({ ok, labels }: { ok: boolean; labels: { ok: string; no: string } }) {
  const Icon = ok ? CheckCircle2 : XCircle
  return (
    <Badge variant={ok ? 'secondary' : 'outline'} className="gap-1.5">
      <Icon className={cn('h-3.5 w-3.5', ok ? 'text-emerald-600' : 'text-muted-foreground')} />
      {ok ? labels.ok : labels.no}
    </Badge>
  )
}

function ChannelCard({
  actions,
  children,
  configured,
  description,
  icon: Icon,
  linked,
  title,
}: ChannelCardProps) {
  const t = useTranslations()

  return (
    <section className="bg-card rounded-lg border p-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <div className="bg-primary/10 text-primary grid h-10 w-10 shrink-0 place-items-center rounded-md">
            <Icon className="h-5 w-5" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <h2 className="text-base font-semibold">{title}</h2>
            <p className="text-muted-foreground mt-1 text-sm">{description}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <StatusBadge
                ok={configured}
                labels={{
                  ok: t('settings.channels.serverReady'),
                  no: t('settings.channels.serverMissing'),
                }}
              />
              {typeof linked === 'boolean' ? (
                <StatusBadge
                  ok={linked}
                  labels={{
                    ok: t('settings.channels.linked'),
                    no: t('settings.channels.notLinked'),
                  }}
                />
              ) : null}
            </div>
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>
      </div>
      {children ? <div className="mt-4">{children}</div> : null}
    </section>
  )
}

function formatEndpoint(endpoint: string) {
  return endpoint.replace(/^https?:\/\//, '')
}

export function NotificationChannelsPanel() {
  const t = useTranslations()
  const token = useAccessToken()
  const queryClient = useQueryClient()
  const [lineUserId, setLineUserId] = useState('')
  const [telegramChatId, setTelegramChatId] = useState('')

  const status = useQuery({
    queryKey: ['channels', 'status'],
    queryFn: () => getChannelStatus(token),
    enabled: token !== null,
  })

  const subscriptions = useQuery({
    queryKey: ['channels', 'web-push', 'subscriptions'],
    queryFn: () => listWebPushSubscriptions(token),
    enabled: token !== null,
  })

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['channels'] })
  }

  const lineLink = useMutation({
    mutationFn: () => setLineLink(lineUserId.trim(), token),
    onSuccess: () => {
      setLineUserId('')
      toast.success(t('settings.channels.toast.saved'))
      refresh()
    },
    onError: () => toast.error(t('settings.channels.toast.saveFailed')),
  })

  const lineUnlink = useMutation({
    mutationFn: () => unlinkLine(token),
    onSuccess: () => {
      toast.success(t('settings.channels.toast.unlinked'))
      refresh()
    },
    onError: () => toast.error(t('settings.channels.toast.unlinkFailed')),
  })

  const telegramLink = useMutation({
    mutationFn: () => setTelegramLink(telegramChatId.trim(), token),
    onSuccess: () => {
      setTelegramChatId('')
      toast.success(t('settings.channels.toast.saved'))
      refresh()
    },
    onError: () => toast.error(t('settings.channels.toast.saveFailed')),
  })

  const telegramUnlink = useMutation({
    mutationFn: () => unlinkTelegram(token),
    onSuccess: () => {
      toast.success(t('settings.channels.toast.unlinked'))
      refresh()
    },
    onError: () => toast.error(t('settings.channels.toast.unlinkFailed')),
  })

  const sendTest = useMutation({
    mutationFn: (channel: NotificationChannel) => testChannel(channel, token),
    onSuccess: (result) => {
      if (result.delivered) toast.success(t('settings.channels.toast.testDelivered'))
      else toast.error(t('settings.channels.toast.testFailed'))
    },
    onError: () => toast.error(t('settings.channels.toast.testFailed')),
  })

  const subscribePush = useMutation({
    mutationFn: async () => {
      const key = await getVapidPublicKey()
      const body = await subscribeBrowserWebPush(key.public_key)
      return addWebPushSubscription(body, token)
    },
    onSuccess: () => {
      toast.success(t('settings.channels.toast.subscribed'))
      refresh()
    },
    onError: () => toast.error(t('settings.channels.toast.subscribeFailed')),
  })

  const removePush = useMutation({
    mutationFn: (id: string) => removeWebPushSubscription(id, token),
    onSuccess: () => {
      toast.success(t('settings.channels.toast.unlinked'))
      refresh()
    },
    onError: () => toast.error(t('settings.channels.toast.unlinkFailed')),
  })

  const data = status.data
  const webPushCount = data?.user_web_push_count ?? 0

  return (
    <div className="max-w-6xl space-y-6">
      {status.isLoading ? (
        <p className="text-muted-foreground text-sm">{t('settings.channels.loading')}</p>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-2">
        <ChannelCard
          title={t('settings.channels.email.title')}
          description={t('settings.channels.email.description')}
          icon={Mail}
          configured={data?.email_configured ?? false}
          actions={
            <Button
              variant="outline"
              size="sm"
              onClick={() => sendTest.mutate('email')}
              disabled={sendTest.isPending}
            >
              <SendHorizontal className="h-4 w-4" aria-hidden="true" />
              {t('settings.channels.email.test')}
            </Button>
          }
        />

        <ChannelCard
          title={t('settings.channels.line.title')}
          description={t('settings.channels.line.description')}
          icon={MessageCircle}
          configured={data?.line_configured ?? false}
          linked={data?.user_line_linked ?? false}
          actions={
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => sendTest.mutate('line')}
                disabled={sendTest.isPending || !data?.user_line_linked}
              >
                <Send className="h-4 w-4" aria-hidden="true" />
                {t('settings.channels.test')}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => lineUnlink.mutate()}
                disabled={lineUnlink.isPending || !data?.user_line_linked}
              >
                <Unlink className="h-4 w-4" aria-hidden="true" />
                {t('settings.channels.unlink')}
              </Button>
            </>
          }
        >
          <div className="grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
            <div className="grid gap-2">
              <Label htmlFor="line-user-id">{t('settings.channels.line.userIdLabel')}</Label>
              <Input
                id="line-user-id"
                value={lineUserId}
                onChange={(event) => setLineUserId(event.target.value)}
                placeholder={t('settings.channels.line.userIdPlaceholder')}
              />
            </div>
            <Button
              onClick={() => lineLink.mutate()}
              disabled={!lineUserId.trim() || lineLink.isPending}
            >
              <Link2 className="h-4 w-4" aria-hidden="true" />
              {t('settings.channels.line.save')}
            </Button>
          </div>
        </ChannelCard>

        <ChannelCard
          title={t('settings.channels.telegram.title')}
          description={t('settings.channels.telegram.description')}
          icon={Send}
          configured={data?.telegram_configured ?? false}
          linked={data?.user_telegram_linked ?? false}
          actions={
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => sendTest.mutate('telegram')}
                disabled={sendTest.isPending || !data?.user_telegram_linked}
              >
                <Send className="h-4 w-4" aria-hidden="true" />
                {t('settings.channels.test')}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => telegramUnlink.mutate()}
                disabled={telegramUnlink.isPending || !data?.user_telegram_linked}
              >
                <Unlink className="h-4 w-4" aria-hidden="true" />
                {t('settings.channels.unlink')}
              </Button>
            </>
          }
        >
          <div className="grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
            <div className="grid gap-2">
              <Label htmlFor="telegram-chat-id">
                {t('settings.channels.telegram.chatIdLabel')}
              </Label>
              <Input
                id="telegram-chat-id"
                value={telegramChatId}
                onChange={(event) => setTelegramChatId(event.target.value)}
                placeholder={t('settings.channels.telegram.chatIdPlaceholder')}
              />
            </div>
            <Button
              onClick={() => telegramLink.mutate()}
              disabled={!telegramChatId.trim() || telegramLink.isPending}
            >
              <Link2 className="h-4 w-4" aria-hidden="true" />
              {t('settings.channels.telegram.save')}
            </Button>
          </div>
        </ChannelCard>
      </div>

      <ChannelCard
        title={t('settings.channels.webPush.title')}
        description={t('settings.channels.webPush.description', { count: webPushCount })}
        icon={BellRing}
        configured={data?.web_push_configured ?? false}
        linked={webPushCount > 0}
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={() => sendTest.mutate('web_push')}
              disabled={sendTest.isPending || webPushCount === 0}
            >
              <Send className="h-4 w-4" aria-hidden="true" />
              {t('settings.channels.test')}
            </Button>
            <Button
              size="sm"
              onClick={() => subscribePush.mutate()}
              disabled={subscribePush.isPending || !data?.web_push_configured}
            >
              <Smartphone className="h-4 w-4" aria-hidden="true" />
              {subscribePush.isPending
                ? t('settings.channels.webPush.subscribing')
                : t('settings.channels.webPush.subscribe')}
            </Button>
          </>
        }
      />

      <section className="bg-card rounded-lg border p-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-base font-semibold">
            {t('settings.channels.webPush.subscriptions')}
          </h2>
          <Badge variant="outline">
            {t('settings.channels.webPush.linkedCount', { count: webPushCount })}
          </Badge>
        </div>
        <div className="mt-4 space-y-2">
          {subscriptions.isLoading ? (
            <p className="text-muted-foreground text-sm">
              {t('settings.channels.webPush.loadingSubscriptions')}
            </p>
          ) : (subscriptions.data ?? []).length === 0 ? (
            <div className="text-muted-foreground rounded-md border border-dashed p-4 text-sm">
              {t('settings.channels.webPush.noSubscriptions')}
            </div>
          ) : (
            subscriptions.data?.map((subscription) => (
              <div
                key={subscription.id}
                className="flex flex-col gap-3 rounded-md border p-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">
                    {formatEndpoint(subscription.endpoint)}
                  </p>
                  <p className="text-muted-foreground mt-1 text-xs">
                    {t('settings.channels.webPush.createdAt', {
                      date: new Date(subscription.created_at).toLocaleString(),
                    })}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => removePush.mutate(subscription.id)}
                  disabled={removePush.isPending}
                >
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                  {t('settings.channels.webPush.remove')}
                </Button>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  )
}
