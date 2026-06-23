import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  cancelStocktake,
  completeStocktake,
  createStocktake,
  getStocktake,
  listStocktakes,
  scanStocktakeItem,
} from './stocktakes'

const originalFetch = global.fetch

function mockJson(body: unknown, status = 200) {
  global.fetch = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'content-type': 'application/json' },
    }),
  )
}

describe('stocktakes api client', () => {
  afterEach(() => {
    global.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it('lists and creates stocktakes', async () => {
    mockJson([{ id: 'st_1', name: 'Q1 count', status: 'open' }])

    const rows = await listStocktakes('jwt')

    expect(rows).toHaveLength(1)
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/stocktakes',
      expect.objectContaining({ credentials: 'include' }),
    )

    mockJson({ id: 'st_2', name: 'Q2 count', status: 'open' }, 201)
    await createStocktake({ name: 'Q2 count' }, 'jwt')
    expect(global.fetch).toHaveBeenLastCalledWith(
      '/api/stocktakes',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ name: 'Q2 count' }),
      }),
    )
  })

  it('loads detail and scans an item', async () => {
    mockJson({ id: 'st_1', items: [] })

    await getStocktake('st_1', 'jwt')

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/stocktakes/st_1',
      expect.objectContaining({ credentials: 'include' }),
    )

    mockJson({ id: 1, item_id: 'item_1', actual_quantity: 8 })
    await scanStocktakeItem(
      'st_1',
      { item_id: 'item_1', actual_quantity: 8, note: 'short' },
      'jwt',
    )
    expect(global.fetch).toHaveBeenLastCalledWith(
      '/api/stocktakes/st_1/scan',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ item_id: 'item_1', actual_quantity: 8, note: 'short' }),
      }),
    )
  })

  it('completes and cancels stocktakes', async () => {
    mockJson({ id: 'st_1', status: 'completed' })
    await completeStocktake('st_1', 'jwt')
    expect(global.fetch).toHaveBeenLastCalledWith(
      '/api/stocktakes/st_1/complete',
      expect.objectContaining({ method: 'POST' }),
    )

    mockJson({ id: 'st_2', status: 'cancelled' })
    await cancelStocktake('st_2', 'jwt')
    expect(global.fetch).toHaveBeenLastCalledWith(
      '/api/stocktakes/st_2/cancel',
      expect.objectContaining({ method: 'POST' }),
    )
  })
})
