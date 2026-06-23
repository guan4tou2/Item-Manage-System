import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  addWebPushSubscription,
  getChannelStatus,
  getVapidPublicKey,
  listWebPushSubscriptions,
  removeWebPushSubscription,
  setLineLink,
  setTelegramLink,
  testChannel,
  unlinkLine,
  unlinkTelegram,
} from './channels'

const originalFetch = global.fetch

function mockJson(body: unknown, status = 200) {
  global.fetch = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'content-type': 'application/json' },
    }),
  )
}

describe('channels api client', () => {
  afterEach(() => {
    global.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it('loads channel status', async () => {
    mockJson({
      email_configured: false,
      line_configured: false,
      telegram_configured: false,
      web_push_configured: false,
      user_line_linked: false,
      user_telegram_linked: false,
      user_web_push_count: 0,
    })

    const status = await getChannelStatus('jwt')

    expect(status.user_web_push_count).toBe(0)
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/channels/status',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('links and unlinks LINE and Telegram accounts', async () => {
    global.fetch = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))

    await setLineLink('U123', 'jwt')
    expect(global.fetch).toHaveBeenLastCalledWith(
      '/api/channels/line',
      expect.objectContaining({
        method: 'PUT',
        body: JSON.stringify({ line_user_id: 'U123' }),
      }),
    )

    await unlinkLine('jwt')
    expect(global.fetch).toHaveBeenLastCalledWith(
      '/api/channels/line',
      expect.objectContaining({ method: 'DELETE' }),
    )

    await setTelegramLink('12345', 'jwt')
    expect(global.fetch).toHaveBeenLastCalledWith(
      '/api/channels/telegram',
      expect.objectContaining({
        method: 'PUT',
        body: JSON.stringify({ chat_id: '12345' }),
      }),
    )

    await unlinkTelegram('jwt')
    expect(global.fetch).toHaveBeenLastCalledWith(
      '/api/channels/telegram',
      expect.objectContaining({ method: 'DELETE' }),
    )
  })

  it('manages web push subscriptions', async () => {
    mockJson({ public_key: 'BKEY' })
    expect(await getVapidPublicKey()).toEqual({ public_key: 'BKEY' })
    expect(global.fetch).toHaveBeenLastCalledWith(
      '/api/channels/vapid-public-key',
      expect.objectContaining({ credentials: 'include' }),
    )

    mockJson([{ id: 'sub_1', endpoint: 'https://push.example/x' }])
    await listWebPushSubscriptions('jwt')
    expect(global.fetch).toHaveBeenLastCalledWith(
      '/api/channels/web-push/subscriptions',
      expect.objectContaining({ credentials: 'include' }),
    )

    mockJson({ id: 'sub_1', endpoint: 'https://push.example/x' }, 201)
    await addWebPushSubscription(
      { endpoint: 'https://push.example/x', p256dh: 'AAA', auth: 'BBB' },
      'jwt',
    )
    expect(global.fetch).toHaveBeenLastCalledWith(
      '/api/channels/web-push/subscriptions',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          endpoint: 'https://push.example/x',
          p256dh: 'AAA',
          auth: 'BBB',
        }),
      }),
    )

    global.fetch = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    await removeWebPushSubscription('sub_1', 'jwt')
    expect(global.fetch).toHaveBeenLastCalledWith(
      '/api/channels/web-push/subscriptions/sub_1',
      expect.objectContaining({ method: 'DELETE' }),
    )
  })

  it('sends channel test notifications', async () => {
    mockJson({ delivered: true })

    const result = await testChannel('telegram', 'jwt')

    expect(result.delivered).toBe(true)
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/channels/test/telegram',
      expect.objectContaining({ method: 'POST' }),
    )
  })
})
