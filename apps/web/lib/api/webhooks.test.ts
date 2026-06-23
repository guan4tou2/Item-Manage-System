import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  createWebhook,
  deleteWebhook,
  listWebhookDeliveries,
  listWebhooks,
  processDueWebhookRetries,
  retryWebhookDelivery,
  updateWebhook,
} from './webhooks'

const originalFetch = global.fetch

function mockJson(body: unknown, status = 200) {
  global.fetch = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'content-type': 'application/json' },
    }),
  )
}

describe('webhooks api client', () => {
  afterEach(() => {
    global.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it('lists webhooks', async () => {
    mockJson([{ id: 'wh_1', name: 'Inventory sync' }])

    const rows = await listWebhooks('jwt')

    expect(rows).toHaveLength(1)
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/webhooks',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('creates webhooks with selected events and optional secret', async () => {
    mockJson({ id: 'wh_1', name: 'Inventory sync' }, 201)

    await createWebhook(
      {
        name: 'Inventory sync',
        url: 'https://example.com/hook',
        secret: 'signed',
        events: ['item.created', 'item.deleted'],
      },
      'jwt',
    )

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/webhooks',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          name: 'Inventory sync',
          url: 'https://example.com/hook',
          secret: 'signed',
          events: ['item.created', 'item.deleted'],
        }),
      }),
    )
  })

  it('updates and deletes webhooks', async () => {
    mockJson({ id: 'wh_1', is_active: false })
    await updateWebhook('wh_1', { is_active: false }, 'jwt')
    expect(global.fetch).toHaveBeenLastCalledWith(
      '/api/webhooks/wh_1',
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify({ is_active: false }),
      }),
    )

    global.fetch = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    await deleteWebhook('wh_1', 'jwt')
    expect(global.fetch).toHaveBeenLastCalledWith(
      '/api/webhooks/wh_1',
      expect.objectContaining({ method: 'DELETE' }),
    )
  })

  it('lists deliveries with a bounded limit', async () => {
    mockJson([{ id: 'del_1', attempt: 1 }])

    await listWebhookDeliveries('wh_1', { limit: 25 }, 'jwt')

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/webhooks/wh_1/deliveries?limit=25',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('retries a specific delivery and processes due retries', async () => {
    mockJson({ id: 'del_2', attempt: 2 })
    await retryWebhookDelivery('wh_1', 'del_1', 'jwt')
    expect(global.fetch).toHaveBeenLastCalledWith(
      '/api/webhooks/wh_1/deliveries/del_1/retry',
      expect.objectContaining({ method: 'POST' }),
    )

    mockJson({ processed: 3, succeeded: 2, remaining: 1 })
    const result = await processDueWebhookRetries('jwt')
    expect(result.remaining).toBe(1)
    expect(global.fetch).toHaveBeenLastCalledWith(
      '/api/webhooks/process-retries',
      expect.objectContaining({ method: 'POST' }),
    )
  })
})
