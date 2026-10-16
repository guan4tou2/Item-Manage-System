import type { paths } from '@ims/api-types'

import { apiFetch } from './client'

export type NotificationPreferencesResponse =
  paths['/api/notifications/preferences']['get']['responses']['200']['content']['application/json']

type UpdateRequest =
  paths['/api/notifications/preferences']['put']['requestBody']['content']['application/json']

export type NotificationPreferenceUpdate = NonNullable<UpdateRequest['updates']>[number]

export async function getNotificationPreferences(
  token: string | null,
): Promise<NotificationPreferencesResponse> {
  return (await apiFetch('/notifications/preferences', { accessToken: token })).json()
}

export async function updateNotificationPreferences(
  updates: NotificationPreferenceUpdate[],
  token: string | null,
): Promise<NotificationPreferencesResponse> {
  return (
    await apiFetch('/notifications/preferences', {
      method: 'PUT',
      accessToken: token,
      body: JSON.stringify({ updates }),
    })
  ).json()
}

export async function resetNotificationPreferences(
  token: string | null,
): Promise<NotificationPreferencesResponse> {
  return (
    await apiFetch('/notifications/preferences', {
      method: 'DELETE',
      accessToken: token,
    })
  ).json()
}
