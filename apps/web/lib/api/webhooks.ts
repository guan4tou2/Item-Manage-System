import { apiFetch } from './client'

export const WEBHOOK_EVENTS = ['item.created', 'item.updated', 'item.deleted'] as const

export type WebhookEvent = (typeof WEBHOOK_EVENTS)[number]

export interface WebhookRead {
  id: string
  name: string
  url: string
  events: string[]
  is_active: boolean
  created_at: string
  last_fired_at: string | null
  last_status: number | null
}

export interface WebhookCreate {
  name: string
  url: string
  secret: string | null
  events: WebhookEvent[]
}

export interface WebhookUpdate {
  name?: string
  url?: string
  secret?: string | null
  events?: WebhookEvent[]
  is_active?: boolean
}

export interface WebhookDeliveryRead {
  id: string
  webhook_id: string
  event: string
  payload: Record<string, unknown>
  status_code: number | null
  response_excerpt: string | null
  attempt: number
  next_retry_at: string | null
  created_at: string
}

export interface ProcessRetriesResult {
  processed: number
  succeeded: number
  remaining: number
}

export type WebhookDeliveryStatus = 'success' | 'failed' | 'pending'

export interface WebhookDeliveryParams {
  limit?: number
  offset?: number
  status?: WebhookDeliveryStatus
  event?: string
}

export interface WebhookDeliveryStats {
  total: number
  succeeded: number
  failed: number
  pending: number
  last_success_at: string | null
}

export async function listWebhooks(token: string | null): Promise<WebhookRead[]> {
  return (await apiFetch('/webhooks', { accessToken: token })).json()
}

export async function createWebhook(
  body: WebhookCreate,
  token: string | null,
): Promise<WebhookRead> {
  return (
    await apiFetch('/webhooks', {
      method: 'POST',
      accessToken: token,
      body: JSON.stringify(body),
    })
  ).json()
}

export async function updateWebhook(
  id: string,
  body: WebhookUpdate,
  token: string | null,
): Promise<WebhookRead> {
  return (
    await apiFetch(`/webhooks/${id}`, {
      method: 'PATCH',
      accessToken: token,
      body: JSON.stringify(body),
    })
  ).json()
}

export async function deleteWebhook(id: string, token: string | null): Promise<void> {
  await apiFetch(`/webhooks/${id}`, { method: 'DELETE', accessToken: token })
}

export async function listWebhookDeliveries(
  webhookId: string,
  params: WebhookDeliveryParams,
  token: string | null,
): Promise<WebhookDeliveryRead[]> {
  const q = new URLSearchParams()
  if (params.limit !== undefined) q.set('limit', String(params.limit))
  if (params.offset !== undefined) q.set('offset', String(params.offset))
  if (params.status !== undefined) q.set('status', params.status)
  if (params.event !== undefined) q.set('event', params.event)
  const suffix = q.size ? `?${q}` : ''
  return (
    await apiFetch(`/webhooks/${webhookId}/deliveries${suffix}`, { accessToken: token })
  ).json()
}

export async function getWebhookDeliveryStats(
  webhookId: string,
  token: string | null,
): Promise<WebhookDeliveryStats> {
  return (
    await apiFetch(`/webhooks/${webhookId}/deliveries/stats`, { accessToken: token })
  ).json()
}

export async function retryWebhookDelivery(
  webhookId: string,
  deliveryId: string,
  token: string | null,
): Promise<WebhookDeliveryRead> {
  return (
    await apiFetch(`/webhooks/${webhookId}/deliveries/${deliveryId}/retry`, {
      method: 'POST',
      accessToken: token,
    })
  ).json()
}

export async function processDueWebhookRetries(
  token: string | null,
): Promise<ProcessRetriesResult> {
  return (
    await apiFetch('/webhooks/process-retries', {
      method: 'POST',
      accessToken: token,
    })
  ).json()
}
