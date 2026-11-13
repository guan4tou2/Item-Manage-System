import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { describe, expect, it, vi, beforeEach } from 'vitest'

import enMessages from '@/messages/en.json'
import * as api from '@/lib/api/webhooks'
import { ApiError } from '@/lib/api/client'
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

  it('shows the dedicated message when the URL is rejected by SSRF protection', async () => {
    vi.mocked(api.listWebhooks).mockResolvedValue([])
    vi.mocked(api.createWebhook).mockRejectedValue(
      new ApiError(422, { detail: [{ msg: 'Value error, webhook_url_not_allowed', type: 'value_error' }] }),
    )

    renderPanel()

    fireEvent.change(screen.getByLabelText('Webhook name'), { target: { value: 'Bad' } })
    fireEvent.change(screen.getByLabelText('Endpoint URL'), { target: { value: 'http://127.0.0.1/hook' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create webhook' }))

    expect(await screen.findByText(enMessages.settings.webhooks.urlNotAllowed)).toBeInTheDocument()
  })

  it('keeps the generic hint for other create errors', async () => {
    vi.mocked(api.listWebhooks).mockResolvedValue([])
    vi.mocked(api.createWebhook).mockRejectedValue(new ApiError(500, { detail: 'boom' }))

    renderPanel()

    fireEvent.change(screen.getByLabelText('Webhook name'), { target: { value: 'Bad' } })
    fireEvent.change(screen.getByLabelText('Endpoint URL'), { target: { value: 'https://example.com/hook' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create webhook' }))

    expect(await screen.findByText(enMessages.settings.webhooks.tryAgain)).toBeInTheDocument()
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

  it('filters deliveries by status', async () => {
    renderPanel()

    await screen.findByTestId('deliveries-table')
    fireEvent.click(screen.getByRole('button', { name: 'Failed' }))

    await waitFor(() => {
      expect(api.listWebhookDeliveries).toHaveBeenLastCalledWith(
        'wh_1',
        { limit: 20, offset: 0, status: 'failed' },
        'jwt',
      )
    })
  })

  it('shows the filter empty state and clears the filter', async () => {
    renderPanel()

    await screen.findByTestId('deliveries-table')
    vi.mocked(api.listWebhookDeliveries).mockResolvedValue([])
    fireEvent.click(screen.getByRole('button', { name: 'Succeeded' }))

    expect(await screen.findByText('No matching deliveries')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Clear filter' }))

    await waitFor(() => {
      expect(api.listWebhookDeliveries).toHaveBeenLastCalledWith(
        'wh_1',
        { limit: 20, offset: 0 },
        'jwt',
      )
    })
    expect(await screen.findByText('No deliveries yet')).toBeInTheDocument()
  })

  it('loads the next page of deliveries on demand', async () => {
    const firstPage = Array.from({ length: 20 }, (_, index) => ({
      ...failedDelivery,
      id: `del_${index}`,
    }))
    const secondPage = [{ ...failedDelivery, id: 'del_extra' }]
    vi.mocked(api.listWebhookDeliveries)
      .mockResolvedValueOnce(firstPage)
      .mockResolvedValueOnce(secondPage)

    renderPanel()

    await screen.findByTestId('deliveries-table')
    fireEvent.click(screen.getByRole('button', { name: 'Load more' }))

    await waitFor(() => {
      expect(api.listWebhookDeliveries).toHaveBeenLastCalledWith(
        'wh_1',
        { limit: 20, offset: 20 },
        'jwt',
      )
    })
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: 'Load more' })).not.toBeInTheDocument()
    })
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

  it('shows delivery success rate and last success in the overview', async () => {
    vi.mocked(api.getWebhookDeliveryStats).mockResolvedValue({
      total: 2,
      succeeded: 1,
      failed: 1,
      pending: 0,
      last_success_at: '2026-06-19T03:09:00Z',
    })

    renderPanel()

    const stats = await screen.findByTestId('deliveries-stats')
    expect(stats).toHaveTextContent('Success rate 50% (1 of 2)')
    expect(stats).toHaveTextContent('Last success:')
  })

  it('hides the overview when there are no deliveries', async () => {
    renderPanel()

    await screen.findByTestId('deliveries-table')
    expect(screen.queryByTestId('deliveries-stats')).not.toBeInTheDocument()
  })

  it('keeps delivery history when the overview fails to load', async () => {
    vi.mocked(api.getWebhookDeliveryStats).mockRejectedValue(new Error('boom'))

    renderPanel()

    expect(await screen.findByTestId('deliveries-table')).toBeInTheDocument()
    expect(screen.queryByTestId('deliveries-stats')).not.toBeInTheDocument()
  })

  it('shows a small skeleton while the overview loads', async () => {
    vi.mocked(api.getWebhookDeliveryStats).mockReturnValue(new Promise(() => {}))

    renderPanel()

    await screen.findByTestId('deliveries-table')
    expect(screen.getByTestId('deliveries-stats-loading')).toBeInTheDocument()
    expect(screen.queryByTestId('deliveries-stats')).not.toBeInTheDocument()
  })

  it('shows an error with retry when the webhook list fails', async () => {
    vi.mocked(api.listWebhooks).mockRejectedValue(new Error('boom'))

    renderPanel()

    expect(await screen.findByText('Could not load webhooks.')).toBeInTheDocument()

    vi.mocked(api.listWebhooks).mockResolvedValue([webhook])
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))

    await waitFor(() => {
      expect(api.listWebhooks).toHaveBeenCalledTimes(2)
    })
    expect(await screen.findByText('Inventory sync')).toBeInTheDocument()
  })

  it('processes due retries and reports aggregate results', async () => {
    renderPanel()

    fireEvent.click(await screen.findByRole('button', { name: 'Process due retries' }))

    expect(
      await screen.findByText('Processed 3 retries, 2 succeeded, 1 remaining.'),
    ).toBeInTheDocument()
  })
})
