import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as api from '@/lib/api/customization'
import enMessages from '@/messages/en.json'

import { CustomizationPanel } from './customization-panel'

vi.mock('@/lib/auth/use-auth', () => ({
  useAccessToken: () => 'jwt',
}))

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

vi.mock('@/lib/api/customization', () => ({
  createCustomField: vi.fn(),
  createItemTemplate: vi.fn(),
  createItemType: vi.fn(),
  deleteCustomField: vi.fn(),
  deleteItemTemplate: vi.fn(),
  deleteItemType: vi.fn(),
  listCustomFields: vi.fn(),
  listItemTemplates: vi.fn(),
  listItemTypes: vi.fn(),
  updateItemTemplate: vi.fn(),
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
        <CustomizationPanel />
      </NextIntlClientProvider>
    </QueryClientProvider>,
  )
}

const itemType = {
  id: 1,
  name: 'Appliance',
  icon: 'plug',
  created_at: '2026-06-19T03:00:00Z',
}

const customField = {
  id: 2,
  name: 'Warranty date',
  field_type: 'date',
  created_at: '2026-06-19T03:01:00Z',
}

const template = {
  id: 3,
  name: 'Battery pack',
  payload: { name: 'AA Battery', quantity: 12, notes: 'Keep in drawer' },
  created_at: '2026-06-19T03:02:00Z',
}

describe('CustomizationPanel', () => {
  beforeEach(() => {
    vi.mocked(api.listItemTypes).mockResolvedValue([itemType])
    vi.mocked(api.listCustomFields).mockResolvedValue([customField])
    vi.mocked(api.listItemTemplates).mockResolvedValue([template])
    vi.mocked(api.createItemType).mockResolvedValue(itemType)
    vi.mocked(api.createCustomField).mockResolvedValue(customField)
    vi.mocked(api.createItemTemplate).mockResolvedValue(template)
    vi.mocked(api.deleteItemType).mockResolvedValue(undefined)
    vi.mocked(api.deleteCustomField).mockResolvedValue(undefined)
    vi.mocked(api.deleteItemTemplate).mockResolvedValue(undefined)
    vi.mocked(api.updateItemTemplate).mockResolvedValue(template)
  })

  it('renders item types, custom fields, and templates', async () => {
    renderPanel()

    expect(await screen.findByText('Appliance')).toBeInTheDocument()
    expect(screen.getAllByText('Warranty date').length).toBeGreaterThan(0)
    expect(screen.getByText('Date')).toBeInTheDocument()
    expect(screen.getByText('Battery pack')).toBeInTheDocument()
    expect(screen.getByText('AA Battery · qty 12')).toBeInTheDocument()
  })

  it('creates a custom field with the selected type', async () => {
    vi.mocked(api.listCustomFields).mockResolvedValue([])

    renderPanel()

    fireEvent.change(await screen.findByLabelText('Field name'), {
      target: { value: 'Serial number' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Create field' }))

    await waitFor(() => {
      expect(api.createCustomField).toHaveBeenCalledWith(
        { name: 'Serial number', field_type: 'text' },
        'jwt',
      )
    })
  })

  it('creates an item template from common item defaults', async () => {
    renderPanel()

    fireEvent.change(await screen.findByLabelText('Template name'), {
      target: { value: 'Restock pack' },
    })
    fireEvent.change(screen.getByLabelText('Default item name'), {
      target: { value: 'AA Battery' },
    })
    fireEvent.change(screen.getByLabelText('Default quantity'), {
      target: { value: '12' },
    })
    fireEvent.change(screen.getByLabelText('Default notes'), {
      target: { value: 'Keep in drawer' },
    })
    fireEvent.input(screen.getByLabelText('Warranty date'), {
      target: { value: '2026-07-01' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Create template' }))

    await waitFor(() => {
      expect(api.createItemTemplate).toHaveBeenCalledWith(
        {
          name: 'Restock pack',
          payload: {
            name: 'AA Battery',
            quantity: 12,
            notes: 'Keep in drawer',
            custom_values: {
              '2': '2026-07-01',
            },
          },
        },
        'jwt',
      )
    })
  })

  it('deletes item types from the list', async () => {
    renderPanel()

    fireEvent.click(await screen.findByRole('button', { name: 'Delete item type Appliance' }))

    await waitFor(() => {
      expect(api.deleteItemType).toHaveBeenCalledWith(1, 'jwt')
    })
  })

  it('duplicates an item template from the list', async () => {
    renderPanel()

    fireEvent.click(await screen.findByRole('button', { name: 'Duplicate template Battery pack' }))

    await waitFor(() => {
      expect(api.createItemTemplate).toHaveBeenCalledWith(
        {
          name: 'Battery pack copy',
          payload: template.payload,
        },
        'jwt',
      )
    })
  })

  it('updates an item template from the list form', async () => {
    renderPanel()

    fireEvent.click(await screen.findByRole('button', { name: 'Edit template Battery pack' }))
    fireEvent.change(screen.getByLabelText('Template name'), {
      target: { value: 'Battery pack v2' },
    })
    fireEvent.change(screen.getByLabelText('Default quantity'), {
      target: { value: '24' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Update template' }))

    await waitFor(() => {
      expect(api.updateItemTemplate).toHaveBeenCalledWith(
        3,
        {
          name: 'Battery pack v2',
          payload: {
            name: 'AA Battery',
            quantity: 24,
            notes: 'Keep in drawer',
          },
        },
        'jwt',
      )
    })
  })
})
