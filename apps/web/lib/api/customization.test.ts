import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  createCustomField,
  createItemTemplate,
  createItemType,
  deleteCustomField,
  deleteItemTemplate,
  deleteItemType,
  deleteItemCustomValue,
  listItemCustomValues,
  listCustomFields,
  listItemTemplates,
  listItemTypes,
  saveItemCustomValues,
  setItemCustomValue,
  updateItemTemplate,
} from './customization'

const originalFetch = global.fetch

function mockJson(body: unknown, status = 200) {
  global.fetch = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'content-type': 'application/json' },
    }),
  )
}

describe('customization api client', () => {
  afterEach(() => {
    global.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it('lists item types, custom fields, and templates', async () => {
    mockJson([{ id: 1, name: 'Appliance', icon: 'plug' }])
    expect(await listItemTypes('jwt')).toHaveLength(1)
    expect(global.fetch).toHaveBeenLastCalledWith(
      '/api/item-types',
      expect.objectContaining({ credentials: 'include' }),
    )

    mockJson([{ id: 2, name: 'Warranty', field_type: 'date' }])
    expect(await listCustomFields('jwt')).toHaveLength(1)
    expect(global.fetch).toHaveBeenLastCalledWith(
      '/api/custom-fields',
      expect.objectContaining({ credentials: 'include' }),
    )

    mockJson([{ id: 3, name: 'Office supply', payload: { quantity: 10 } }])
    expect(await listItemTemplates('jwt')).toHaveLength(1)
    expect(global.fetch).toHaveBeenLastCalledWith(
      '/api/item-templates',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('creates customization records with the expected payloads', async () => {
    mockJson({ id: 1, name: 'Appliance', icon: 'plug' }, 201)
    await createItemType({ name: 'Appliance', icon: 'plug' }, 'jwt')
    expect(global.fetch).toHaveBeenLastCalledWith(
      '/api/item-types',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ name: 'Appliance', icon: 'plug' }),
      }),
    )

    mockJson({ id: 2, name: 'Warranty', field_type: 'date' }, 201)
    await createCustomField({ name: 'Warranty', field_type: 'date' }, 'jwt')
    expect(global.fetch).toHaveBeenLastCalledWith(
      '/api/custom-fields',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ name: 'Warranty', field_type: 'date' }),
      }),
    )

    mockJson({ id: 3, name: 'Restock pack', payload: { name: 'Battery', quantity: 12 } }, 201)
    await createItemTemplate({ name: 'Restock pack', payload: { name: 'Battery', quantity: 12 } }, 'jwt')
    expect(global.fetch).toHaveBeenLastCalledWith(
      '/api/item-templates',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ name: 'Restock pack', payload: { name: 'Battery', quantity: 12 } }),
      }),
    )
  })

  it('deletes customization records', async () => {
    global.fetch = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))

    await deleteItemType(1, 'jwt')
    expect(global.fetch).toHaveBeenLastCalledWith(
      '/api/item-types/1',
      expect.objectContaining({ method: 'DELETE' }),
    )

    await deleteCustomField(2, 'jwt')
    expect(global.fetch).toHaveBeenLastCalledWith(
      '/api/custom-fields/2',
      expect.objectContaining({ method: 'DELETE' }),
    )

    await deleteItemTemplate(3, 'jwt')
    expect(global.fetch).toHaveBeenLastCalledWith(
      '/api/item-templates/3',
      expect.objectContaining({ method: 'DELETE' }),
    )
  })

  it('updates an item template', async () => {
    mockJson({ id: 3, name: 'Restock pack v2', payload: { name: 'Battery', quantity: 24 } })

    await updateItemTemplate(
      3,
      { name: 'Restock pack v2', payload: { name: 'Battery', quantity: 24 } },
      'jwt',
    )

    expect(global.fetch).toHaveBeenLastCalledWith(
      '/api/item-templates/3',
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify({
          name: 'Restock pack v2',
          payload: { name: 'Battery', quantity: 24 },
        }),
      }),
    )
  })

  it('manages custom values on an item', async () => {
    mockJson([{ custom_field_id: 2, value: 'SN-123' }])

    const values = await listItemCustomValues('item_1', 'jwt')

    expect(values[0]?.value).toBe('SN-123')
    expect(global.fetch).toHaveBeenLastCalledWith(
      '/api/items/item_1/custom-values',
      expect.objectContaining({ credentials: 'include' }),
    )

    mockJson({ custom_field_id: 2, value: 'SN-456' })
    await setItemCustomValue('item_1', { custom_field_id: 2, value: 'SN-456' }, 'jwt')
    expect(global.fetch).toHaveBeenLastCalledWith(
      '/api/items/item_1/custom-values',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ custom_field_id: 2, value: 'SN-456' }),
      }),
    )

    global.fetch = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    await deleteItemCustomValue('item_1', 2, 'jwt')
    expect(global.fetch).toHaveBeenLastCalledWith(
      '/api/items/item_1/custom-values/2',
      expect.objectContaining({ method: 'DELETE' }),
    )
  })

  it('saves item custom values by setting filled fields and clearing empty fields', async () => {
    global.fetch = vi.fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ custom_field_id: 1, value: 'SN-123' }), {
          status: 200,
          headers: { 'content-type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: 'value not set' }), { status: 404 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ custom_field_id: 3, value: false }), {
          status: 200,
          headers: { 'content-type': 'application/json' },
        }),
      )

    await saveItemCustomValues(
      'item_1',
      [
        { id: 1, name: 'Serial', field_type: 'text', created_at: '2026-06-19T00:00:00Z' },
        { id: 2, name: 'Capacity', field_type: 'number', created_at: '2026-06-19T00:00:00Z' },
        { id: 3, name: 'Fragile', field_type: 'bool', created_at: '2026-06-19T00:00:00Z' },
      ],
      { '1': 'SN-123', '2': null, '3': false },
      'jwt',
    )

    expect(global.fetch).toHaveBeenNthCalledWith(
      1,
      '/api/items/item_1/custom-values',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ custom_field_id: 1, value: 'SN-123' }),
      }),
    )
    expect(global.fetch).toHaveBeenNthCalledWith(
      2,
      '/api/items/item_1/custom-values/2',
      expect.objectContaining({ method: 'DELETE' }),
    )
    expect(global.fetch).toHaveBeenNthCalledWith(
      3,
      '/api/items/item_1/custom-values',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ custom_field_id: 3, value: false }),
      }),
    )
  })
})
