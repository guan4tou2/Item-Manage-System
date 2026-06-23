import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as itemsApi from '@/lib/api/items'
import * as stocktakeApi from '@/lib/api/stocktakes'
import enMessages from '@/messages/en.json'

import { StocktakesClient } from './stocktakes-client'

vi.mock('@/lib/auth/use-auth', () => ({
  useAccessToken: () => 'jwt',
}))

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

vi.mock('@/lib/api/items', () => ({
  listItems: vi.fn(),
}))

vi.mock('@/lib/api/stocktakes', () => ({
  cancelStocktake: vi.fn(),
  completeStocktake: vi.fn(),
  createStocktake: vi.fn(),
  getStocktake: vi.fn(),
  listStocktakes: vi.fn(),
  scanStocktakeItem: vi.fn(),
}))

function renderClient() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <StocktakesClient />
      </NextIntlClientProvider>
    </QueryClientProvider>,
  )
}

const openStocktake = {
  id: 'st_1',
  name: 'June stocktake',
  status: 'open' as const,
  started_at: '2026-06-19T03:00:00Z',
  completed_at: null,
  item_count: 1,
  discrepancy_count: 1,
}

const detail = {
  ...openStocktake,
  items: [
    {
      id: 1,
      item_id: 'item_1',
      expected_quantity: 10,
      actual_quantity: 8,
      note: 'Shelf count',
      scanned_at: '2026-06-19T03:10:00Z',
    },
  ],
}

const item = {
  id: 'item_1',
  name: 'Batteries',
  description: null,
  quantity: 10,
  min_quantity: null,
  notes: null,
  is_favorite: false,
  image_id: null,
  warehouse_id: null,
  owner_id: 'user_1',
  owner_username: 'owner',
  created_at: '2026-06-19T03:00:00Z',
  updated_at: '2026-06-19T03:00:00Z',
  category: null,
  location: null,
  tags: [],
}

const matchedItem = { ...item, id: 'item_2', name: 'Labels', quantity: 5 }
const overItem = { ...item, id: 'item_3', name: 'Markers', quantity: 1 }

describe('StocktakesClient', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(stocktakeApi.listStocktakes).mockResolvedValue([openStocktake])
    vi.mocked(stocktakeApi.getStocktake).mockResolvedValue(detail)
    vi.mocked(stocktakeApi.createStocktake).mockResolvedValue({
      ...openStocktake,
      id: 'st_2',
      name: 'July stocktake',
      item_count: 0,
      discrepancy_count: 0,
    })
    vi.mocked(stocktakeApi.scanStocktakeItem).mockResolvedValue({
      id: 2,
      item_id: 'item_1',
      expected_quantity: 10,
      actual_quantity: 9,
      note: null,
      scanned_at: '2026-06-19T03:12:00Z',
    })
    vi.mocked(stocktakeApi.completeStocktake).mockResolvedValue({
      ...detail,
      status: 'completed',
      completed_at: '2026-06-19T03:20:00Z',
    })
    vi.mocked(stocktakeApi.cancelStocktake).mockResolvedValue({
      ...openStocktake,
      status: 'cancelled',
      completed_at: '2026-06-19T03:20:00Z',
    })
    vi.mocked(itemsApi.listItems).mockResolvedValue({
      items: [item, matchedItem, overItem],
      total: 3,
      page: 1,
      per_page: 100,
    })
  })

  it('renders stocktake status and discrepancy detail', async () => {
    renderClient()

    expect(await screen.findByText('June stocktake')).toBeInTheDocument()
    expect(await screen.findByText('Batteries')).toBeInTheDocument()
    expect(await screen.findByText('-2')).toBeInTheDocument()
  })

  it('creates a new stocktake session', async () => {
    renderClient()

    fireEvent.change(await screen.findByLabelText('Session name'), {
      target: { value: 'July stocktake' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Start stocktake' }))

    await waitFor(() => {
      expect(stocktakeApi.createStocktake).toHaveBeenCalledWith(
        { name: 'July stocktake' },
        'jwt',
      )
    })
  })

  it('scans an item with actual quantity', async () => {
    renderClient()

    fireEvent.change(await screen.findByLabelText('Item'), {
      target: { value: 'item_1' },
    })
    fireEvent.change(screen.getByLabelText('Actual quantity'), {
      target: { value: '9' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Record count' }))

    await waitFor(() => {
      expect(stocktakeApi.scanStocktakeItem).toHaveBeenCalledWith(
        'st_1',
        { item_id: 'item_1', actual_quantity: 9, note: null },
        'jwt',
      )
    })
  })

  it('clears scan inputs, focuses the next item, and announces readiness', async () => {
    renderClient()

    const itemSelect = await screen.findByLabelText('Item')
    fireEvent.change(itemSelect, {
      target: { value: 'item_1' },
    })
    fireEvent.change(screen.getByLabelText('Actual quantity'), {
      target: { value: '9' },
    })
    fireEvent.change(screen.getByLabelText('Note'), {
      target: { value: 'Shelf A' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Record count' }))

    await waitFor(() => {
      expect(stocktakeApi.scanStocktakeItem).toHaveBeenCalled()
    })

    expect(screen.getByText('Recorded, ready for next item')).toBeInTheDocument()
    expect(screen.getByLabelText('Actual quantity')).toHaveValue(null)
    expect(screen.getByLabelText('Note')).toHaveValue('')
    expect(itemSelect).toHaveFocus()
  })

  it('groups scanned rows by discrepancy status', async () => {
    vi.mocked(stocktakeApi.getStocktake).mockResolvedValue({
      ...openStocktake,
      item_count: 3,
      discrepancy_count: 2,
      items: [
        {
          id: 1,
          item_id: 'item_2',
          expected_quantity: 5,
          actual_quantity: 5,
          note: null,
          scanned_at: '2026-06-19T03:10:00Z',
        },
        {
          id: 2,
          item_id: 'item_1',
          expected_quantity: 10,
          actual_quantity: 8,
          note: null,
          scanned_at: '2026-06-19T03:12:00Z',
        },
        {
          id: 3,
          item_id: 'item_3',
          expected_quantity: 1,
          actual_quantity: 4,
          note: null,
          scanned_at: '2026-06-19T03:14:00Z',
        },
      ],
    })

    renderClient()

    const matched = await screen.findByRole('region', { name: 'Matched (1)' })
    const missing = screen.getByRole('region', { name: 'Missing (1)' })
    const over = screen.getByRole('region', { name: 'Over-counted (1)' })

    expect(within(matched).getByText('Labels')).toBeInTheDocument()
    expect(within(missing).getByText('Batteries')).toBeInTheDocument()
    expect(within(over).getByText('Markers')).toBeInTheDocument()
  })

  it('completes an open stocktake immediately when there are no discrepancies', async () => {
    vi.mocked(stocktakeApi.listStocktakes).mockResolvedValue([
      { ...openStocktake, discrepancy_count: 0 },
    ])
    vi.mocked(stocktakeApi.getStocktake).mockResolvedValue({
      ...detail,
      discrepancy_count: 0,
      items: [
        {
          id: 1,
          item_id: 'item_1',
          expected_quantity: 10,
          actual_quantity: 10,
          note: null,
          scanned_at: '2026-06-19T03:10:00Z',
        },
      ],
    })

    renderClient()

    fireEvent.click(await screen.findByRole('button', { name: 'Complete stocktake' }))

    await waitFor(() => {
      expect(stocktakeApi.completeStocktake).toHaveBeenCalledWith('st_1', 'jwt')
    })
  })

  it('confirms completion when discrepancies exist', async () => {
    renderClient()

    fireEvent.click(await screen.findByRole('button', { name: 'Complete stocktake' }))

    expect(screen.getByText('Complete with discrepancies?')).toBeInTheDocument()
    expect(screen.getByText('Matched 0 · Missing 1 · Over-counted 0 · Total delta -2')).toBeInTheDocument()
    expect(stocktakeApi.completeStocktake).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'Complete anyway' }))

    await waitFor(() => {
      expect(stocktakeApi.completeStocktake).toHaveBeenCalledWith('st_1', 'jwt')
    })
  })
})
