import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  getNotificationPreferences,
  resetNotificationPreferences,
  updateNotificationPreferences,
} from './notification-preferences'

const originalFetch = global.fetch

function mockJson(body: unknown, status = 200) {
  global.fetch = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'content-type': 'application/json' },
    }),
  )
}

describe('notification preferences api client', () => {
  afterEach(() => {
    global.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it('loads the preference snapshot', async () => {
    mockJson({ has_custom: false, matrix: { low_stock: { email: true } } })

    const prefs = await getNotificationPreferences('jwt')

    expect(prefs.has_custom).toBe(false)
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/notifications/preferences',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('sends updates as a PUT body', async () => {
    mockJson({ has_custom: true })

    await updateNotificationPreferences(
      [{ type: 'low_stock', channel: 'email', enabled: false }],
      'jwt',
    )

    expect(global.fetch).toHaveBeenLastCalledWith(
      '/api/notifications/preferences',
      expect.objectContaining({
        method: 'PUT',
        body: JSON.stringify({
          updates: [{ type: 'low_stock', channel: 'email', enabled: false }],
        }),
      }),
    )
  })

  it('resets with DELETE and returns the fresh snapshot', async () => {
    mockJson({ has_custom: false })

    const prefs = await resetNotificationPreferences('jwt')

    expect(prefs.has_custom).toBe(false)
    expect(global.fetch).toHaveBeenLastCalledWith(
      '/api/notifications/preferences',
      expect.objectContaining({ method: 'DELETE' }),
    )
  })
})
