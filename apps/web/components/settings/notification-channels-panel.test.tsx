import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as api from '@/lib/api/channels'
import enMessages from '@/messages/en.json'

import { NotificationChannelsPanel } from './notification-channels-panel'

vi.mock('@/lib/auth/use-auth', () => ({
  useAccessToken: () => 'jwt',
}))

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

vi.mock('@/lib/api/channels', () => ({
  getChannelStatus: vi.fn(),
  getVapidPublicKey: vi.fn(),
  listWebPushSubscriptions: vi.fn(),
  setLineLink: vi.fn(),
  setTelegramLink: vi.fn(),
  subscribeBrowserWebPush: vi.fn(),
  addWebPushSubscription: vi.fn(),
  removeWebPushSubscription: vi.fn(),
  testChannel: vi.fn(),
  unlinkLine: vi.fn(),
  unlinkTelegram: vi.fn(),
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
        <NotificationChannelsPanel />
      </NextIntlClientProvider>
    </QueryClientProvider>,
  )
}

const status = {
  email_configured: true,
  line_configured: true,
  telegram_configured: false,
  web_push_configured: true,
  user_line_linked: false,
  user_telegram_linked: true,
  user_web_push_count: 1,
}

describe('NotificationChannelsPanel', () => {
  beforeEach(() => {
    vi.mocked(api.getChannelStatus).mockResolvedValue(status)
    vi.mocked(api.listWebPushSubscriptions).mockResolvedValue([
      {
        id: 'sub_1',
        endpoint: 'https://push.example/subscription-with-a-long-id',
        created_at: '2026-06-19T03:00:00Z',
      },
    ])
    vi.mocked(api.getVapidPublicKey).mockResolvedValue({ public_key: 'BKEY' })
    vi.mocked(api.setLineLink).mockResolvedValue(undefined)
    vi.mocked(api.setTelegramLink).mockResolvedValue(undefined)
    vi.mocked(api.unlinkLine).mockResolvedValue(undefined)
    vi.mocked(api.unlinkTelegram).mockResolvedValue(undefined)
    vi.mocked(api.testChannel).mockResolvedValue({ delivered: true })
    vi.mocked(api.subscribeBrowserWebPush).mockResolvedValue({
      endpoint: 'https://push.example/new',
      p256dh: 'AAA',
      auth: 'BBB',
    })
    vi.mocked(api.addWebPushSubscription).mockResolvedValue({
      id: 'sub_2',
      endpoint: 'https://push.example/new',
      created_at: '2026-06-19T03:05:00Z',
    })
    vi.mocked(api.removeWebPushSubscription).mockResolvedValue(undefined)
  })

  it('shows status for each notification channel', async () => {
    renderPanel()

    expect(await screen.findByText('Email')).toBeInTheDocument()
    expect(screen.getByText('LINE')).toBeInTheDocument()
    expect(screen.getByText('Telegram')).toBeInTheDocument()
    expect(screen.getByText('Web Push')).toBeInTheDocument()
    expect(screen.getAllByText('Server ready')).toHaveLength(3)
    expect(screen.getByText('Server missing')).toBeInTheDocument()
    expect(screen.getByText('1 browser linked.')).toBeInTheDocument()
  })

  it('links LINE and Telegram identifiers', async () => {
    renderPanel()

    fireEvent.change(await screen.findByLabelText('LINE user ID'), {
      target: { value: 'U1234567' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save LINE' }))

    await waitFor(() => {
      expect(api.setLineLink).toHaveBeenCalledWith('U1234567', 'jwt')
    })

    fireEvent.change(screen.getByLabelText('Telegram chat ID'), {
      target: { value: '98765' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save Telegram' }))

    await waitFor(() => {
      expect(api.setTelegramLink).toHaveBeenCalledWith('98765', 'jwt')
    })
  })

  it('sends test notifications and removes web push subscriptions', async () => {
    renderPanel()

    fireEvent.click(await screen.findByRole('button', { name: 'Send test email' }))
    await waitFor(() => {
      expect(api.testChannel).toHaveBeenCalledWith('email', 'jwt')
    })

    fireEvent.click(screen.getByRole('button', { name: 'Remove subscription' }))
    await waitFor(() => {
      expect(api.removeWebPushSubscription).toHaveBeenCalledWith('sub_1', 'jwt')
    })
  })

  it('registers the current browser for web push', async () => {
    renderPanel()

    fireEvent.click(await screen.findByRole('button', { name: 'Subscribe this browser' }))

    await waitFor(() => {
      expect(api.subscribeBrowserWebPush).toHaveBeenCalledWith('BKEY')
      expect(api.addWebPushSubscription).toHaveBeenCalledWith(
        {
          endpoint: 'https://push.example/new',
          p256dh: 'AAA',
          auth: 'BBB',
        },
        'jwt',
      )
    })
  })
})
