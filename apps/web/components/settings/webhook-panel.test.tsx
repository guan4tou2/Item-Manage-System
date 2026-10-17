import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { describe, expect, it, vi, beforeEach } from 'vitest'

import enMessages from '@/messages/en.json'
import * as api from '@/lib/api/webhooks'
import { WebhookPanel } from './webhook-panel'

vi.mock('@/lib/auth/use-auth', () => ({
  useAccessToken: () => 'jwt',
}))

vi.mock('@/lib/api/webhooks', () => ({
  WEBHOOK_EVENTS: ['item.created', 'item.updated', 'item.deleted'],
  createWebhook: vi.fn(),
  deleteWebhook: vi.fn(),
  getWebhookDeliveryStats: vi.fn(),
  listWebhookDeliveries: vi.fn(),
  listWebhooks: vi.fn(),
  processDueWebhookRetries: vi.fn(),
  retryWebhookDelivery: vi.fn(),
  updateWebhook: vi.fn(),
}))

function renderPanel() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <WebhookPanel />
      </NextIntlClientProvider>
    </QueryClientProvider>,
  )
}

const webhook = {
  id: 'wh_1',
  name: 'Inventory sync',
  url: 'https://example.com/hook',
  events: ['item.created', 'item.deleted'],
  is_active: true,
  created_at: '2026-06-19T03:00:00Z',
  last_fired_at: '2026-06-19T03:10:00Z',
  last_status: 503,
}

const failedDelivery = {
  id: 'del_1',
  webhook_id: 'wh_1',
  event: 'item.created',
  payload: { item_id: 'item_1' },
  status_code: 503,
  response_excerpt: 'Service unavailable',
  attempt: 1,
  next_retry_at: '2026-06-19T03:12:00Z',
  created_at: '2026-06-19T03:10:00Z',
}

describe('WebhookPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.createWebhook).mockResolvedValue(webhook)
    vi.mocked(api.deleteWebhook).mockResolvedValue(undefined)
    vi.mocked(api.updateWebhook).mockResolvedValue(webhook)
    vi.mocked(api.retryWebhookDelivery).mockResolvedValue({
      ...failedDelivery,
      id: 'del_2',
      attempt: 2,
    })
    vi.mocked(api.processDueWebhookRetries).mockResolvedValue({
      processed: 3,
      succeeded: 2,
      remaining: 1,
    })
    vi.mocked(api.listWebhooks).mockResolvedValue([webhook])
    vi.mocked(api.listWebhookDeliveries).mockResolvedValue([failedDelivery])
    vi.mocked(api.getWebhookDeliveryStats).mockResolvedValue({
      total: 0,
      succeeded: 0,
      failed: 0,
      pending: 0,
      last_success_at: null,
    })
  })

  it('shows a useful empty state', async () => {
    vi.mocked(api.listWebhooks).mockResolvedValue([])

    renderPanel()

    expect(await screen.findByText('No webhooks yet')).toBeInTheDocument()
    expect(
      screen.getByText('Create an endpoint to receive item lifecycle events.'),
    ).toBeInTheDocument()
  })

  it('creates a webhook with selected events', async () => {
    vi.mocked(api.listWebhooks).mockResolvedValue([])

    renderPanel()

    fireEvent.change(screen.getByLabelText('Webhook name'), {
      target: { value: 'Inventory sync' },
    })
    fireEvent.change(screen.getByLabelText('Endpoint URL'), {
      target: { value: 'https://example.com/hook' },
    })
    fireEvent.click(screen.getByLabelText('Item deleted'))
    fireEvent.click(screen.getByRole('button', { name: 'Create webhook' }))

    await waitFor(() => {
      expect(api.createWebhook).toHaveBeenCalledWith(
        {
          name: 'Inventory sync',
          url: 'https://example.com/hook',
          secret: null,
          events: ['item.created', 'item.updated', 'item.deleted'],
        },
        'jwt',
      )
    })
  })

  it('renders deliveries as a desktop table and mobile cards', async () => {
    renderPanel()

    const table = await screen.findByTestId('deliveries-table')
    expect(api.listWebhookDeliveries).toHaveBeenCalledWith(
      'wh_1',
      { limit: 20, offset: 0 },
      'jwt',
    )
    for (const header of ['Time', 'Event', 'Status', 'Attempt', 'Next retry', 'Actions']) {
      expect(within(table).getByText(header)).toBeInTheDocument()
    }
    expect(within(table).getByText('Item created')).toBeInTheDocument()
    expect(within(table).getByText('HTTP 503')).toBeInTheDocument()
    expect(within(table).getByText('Attempt 1')).toBeInTheDocument()

    const cards = screen.getByTestId('deliveries-cards')
    expect(within(cards).getByText('HTTP 503')).toBeInTheDocument()
    expect(within(cards).getByText('Retry scheduled')).toBeInTheDocument()
  })

  it('expands the response excerpt on demand', async () => {
    renderPanel()

    const table = await screen.findByTestId('deliveries-table')
    expect(within(table).queryByTestId('delivery-excerpt')).not.toBeInTheDocument()

    fireEvent.click(within(table).getByRole('button', { name: 'Show response' }))
    expect(within(table).getByTestId('delivery-excerpt')).toHaveTextContent(
      'Service unavailable',
    )

    fireEvent.click(within(table).getByRole('button', { name: 'Hide response' }))
    expect(within(table).queryByTestId('delivery-excerpt')).not.toBeInTheDocument()
  })

  it('retries failed deliveries from the table', async () => {
    renderPanel()

    const table = await screen.findByTestId('deliveries-table')
    fireEvent.click(within(table).getByRole('button', { name: 'Retry now' }))

    await waitFor(() => {
      expect(api.retryWebhookDelivery).toHaveBeenCalledWith('wh_1', 'del_1', 'jwt')
    })
  })

  it('shows a retry affordance when deliveries fail to load', async () => {
    vi.mocked(api.listWebhookDeliveries).mockRejectedValue(new Error('boom'))

    renderPanel()

    expect(await screen.findByText('Could not load delivery history.')).toBeInTheDocument()

    vi.mocked(api.listWebhookDeliveries).mockResolvedValue([failedDelivery])
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))

    await waitFor(() => {
      expect(screen.getByTestId('deliveries-table')).toBeInTheDocument()
    })
    expect(api.listWebhookDeliveries).toHaveBeenCalledTimes(2)
  })

  it('processes due retries and reports aggregate results', async () => {
    renderPanel()

    fireEvent.click(await screen.findByRole('button', { name: 'Process due retries' }))

    expect(
      await screen.findByText('Processed 3 retries, 2 succeeded, 1 remaining.'),
    ).toBeInTheDocument()
  })
})
