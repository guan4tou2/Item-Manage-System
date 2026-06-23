import type { paths } from '@ims/api-types'

import { apiFetch } from './client'

export type NotificationChannel = 'email' | 'line' | 'telegram' | 'web_push'

export type ChannelStatus =
  paths['/api/channels/status']['get']['responses']['200']['content']['application/json']

export type VapidPublicKey =
  paths['/api/channels/vapid-public-key']['get']['responses']['200']['content']['application/json']

export type WebPushSubscriptionRead =
  paths['/api/channels/web-push/subscriptions']['get']['responses']['200']['content']['application/json'][number]

export type WebPushSubscriptionCreate =
  paths['/api/channels/web-push/subscriptions']['post']['requestBody']['content']['application/json']

export type TestChannelResult = { delivered: boolean }

export async function getChannelStatus(token: string | null): Promise<ChannelStatus> {
  return (await apiFetch('/channels/status', { accessToken: token })).json()
}

export async function setLineLink(lineUserId: string, token: string | null): Promise<void> {
  await apiFetch('/channels/line', {
    method: 'PUT',
    accessToken: token,
    body: JSON.stringify({ line_user_id: lineUserId }),
  })
}

export async function unlinkLine(token: string | null): Promise<void> {
  await apiFetch('/channels/line', { method: 'DELETE', accessToken: token })
}

export async function setTelegramLink(chatId: string, token: string | null): Promise<void> {
  await apiFetch('/channels/telegram', {
    method: 'PUT',
    accessToken: token,
    body: JSON.stringify({ chat_id: chatId }),
  })
}

export async function unlinkTelegram(token: string | null): Promise<void> {
  await apiFetch('/channels/telegram', { method: 'DELETE', accessToken: token })
}

export async function getVapidPublicKey(): Promise<VapidPublicKey> {
  return (await apiFetch('/channels/vapid-public-key')).json()
}

export async function listWebPushSubscriptions(
  token: string | null,
): Promise<WebPushSubscriptionRead[]> {
  return (await apiFetch('/channels/web-push/subscriptions', { accessToken: token })).json()
}

export async function addWebPushSubscription(
  body: WebPushSubscriptionCreate,
  token: string | null,
): Promise<WebPushSubscriptionRead> {
  return (
    await apiFetch('/channels/web-push/subscriptions', {
      method: 'POST',
      accessToken: token,
      body: JSON.stringify(body),
    })
  ).json()
}

export async function removeWebPushSubscription(
  id: string,
  token: string | null,
): Promise<void> {
  await apiFetch(`/channels/web-push/subscriptions/${id}`, {
    method: 'DELETE',
    accessToken: token,
  })
}

export async function testChannel(
  channel: NotificationChannel,
  token: string | null,
): Promise<TestChannelResult> {
  return (
    await apiFetch(`/channels/test/${channel}`, {
      method: 'POST',
      accessToken: token,
    })
  ).json()
}

function vapidPublicKeyToUint8Array(publicKey: string): Uint8Array {
  const padding = '='.repeat((4 - (publicKey.length % 4)) % 4)
  const base64 = `${publicKey}${padding}`.replace(/-/g, '+').replace(/_/g, '/')
  const raw = window.atob(base64)
  const output = new Uint8Array(raw.length)
  for (let i = 0; i < raw.length; i += 1) output[i] = raw.charCodeAt(i)
  return output
}

export async function subscribeBrowserWebPush(
  publicKey: string,
): Promise<WebPushSubscriptionCreate> {
  if (
    typeof window === 'undefined' ||
    typeof navigator === 'undefined' ||
    !('serviceWorker' in navigator) ||
    !('PushManager' in window) ||
    !('Notification' in window)
  ) {
    throw new Error('web push unsupported')
  }

  const permission = await Notification.requestPermission()
  if (permission !== 'granted') throw new Error('notification permission denied')

  const registration = await navigator.serviceWorker.ready
  const existing = await registration.pushManager.getSubscription()
  const subscription =
    existing ??
    (await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: vapidPublicKeyToUint8Array(publicKey),
    }))

  const json = subscription.toJSON()
  const endpoint = json.endpoint
  const keys = json.keys
  if (!endpoint || !keys?.p256dh || !keys?.auth) throw new Error('invalid subscription')

  return {
    endpoint,
    p256dh: keys.p256dh,
    auth: keys.auth,
  }
}
