import type { paths } from '@ims/api-types'

import { apiFetch, isApiError } from './client'

export type ItemTypeRead =
  paths['/api/item-types']['get']['responses']['200']['content']['application/json'][number]
export type ItemTypeCreate =
  paths['/api/item-types']['post']['requestBody']['content']['application/json']
export type CustomFieldRead =
  paths['/api/custom-fields']['get']['responses']['200']['content']['application/json'][number]
export type CustomFieldCreate =
  paths['/api/custom-fields']['post']['requestBody']['content']['application/json']
type ApiItemTemplateRead =
  paths['/api/item-templates']['get']['responses']['200']['content']['application/json'][number]
type ApiItemTemplateCreate =
  paths['/api/item-templates']['post']['requestBody']['content']['application/json']
type ApiItemTemplateUpdate =
  paths['/api/item-templates/{template_id}']['patch']['requestBody']['content']['application/json']
export type ItemTemplatePayload = Record<string, unknown>
export type ItemTemplateRead = Omit<ApiItemTemplateRead, 'payload'> & { payload: ItemTemplatePayload }
export type ItemTemplateCreate = Omit<ApiItemTemplateCreate, 'payload'> & { payload: ItemTemplatePayload }
export type ItemTemplateUpdate = Omit<ApiItemTemplateUpdate, 'payload'> & { payload: ItemTemplatePayload }
export type ItemCustomValueRead =
  paths['/api/items/{item_id}/custom-values']['get']['responses']['200']['content']['application/json'][number]
export type ItemCustomValueSet =
  paths['/api/items/{item_id}/custom-values']['post']['requestBody']['content']['application/json']
export type CustomValueMap = Record<string, ItemCustomValueSet['value'] | undefined>

export async function listItemTypes(accessToken: string | null): Promise<ItemTypeRead[]> {
  const res = await apiFetch('/item-types', { accessToken })
  return (await res.json()) as ItemTypeRead[]
}

export async function createItemType(
  body: ItemTypeCreate,
  accessToken: string | null,
): Promise<ItemTypeRead> {
  const res = await apiFetch('/item-types', {
    method: 'POST',
    body: JSON.stringify(body),
    accessToken,
  })
  return (await res.json()) as ItemTypeRead
}

export async function deleteItemType(id: number, accessToken: string | null): Promise<void> {
  await apiFetch(`/item-types/${id}`, { method: 'DELETE', accessToken })
}

export async function listCustomFields(accessToken: string | null): Promise<CustomFieldRead[]> {
  const res = await apiFetch('/custom-fields', { accessToken })
  return (await res.json()) as CustomFieldRead[]
}

export async function createCustomField(
  body: CustomFieldCreate,
  accessToken: string | null,
): Promise<CustomFieldRead> {
  const res = await apiFetch('/custom-fields', {
    method: 'POST',
    body: JSON.stringify(body),
    accessToken,
  })
  return (await res.json()) as CustomFieldRead
}

export async function deleteCustomField(id: number, accessToken: string | null): Promise<void> {
  await apiFetch(`/custom-fields/${id}`, { method: 'DELETE', accessToken })
}

export async function listItemTemplates(accessToken: string | null): Promise<ItemTemplateRead[]> {
  const res = await apiFetch('/item-templates', { accessToken })
  return (await res.json()) as ItemTemplateRead[]
}

export async function createItemTemplate(
  body: ItemTemplateCreate,
  accessToken: string | null,
): Promise<ItemTemplateRead> {
  const res = await apiFetch('/item-templates', {
    method: 'POST',
    body: JSON.stringify(body),
    accessToken,
  })
  return (await res.json()) as ItemTemplateRead
}

export async function updateItemTemplate(
  id: number,
  body: ItemTemplateUpdate,
  accessToken: string | null,
): Promise<ItemTemplateRead> {
  const res = await apiFetch(`/item-templates/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
    accessToken,
  })
  return (await res.json()) as ItemTemplateRead
}

export async function deleteItemTemplate(id: number, accessToken: string | null): Promise<void> {
  await apiFetch(`/item-templates/${id}`, { method: 'DELETE', accessToken })
}

export async function listItemCustomValues(
  itemId: string,
  accessToken: string | null,
): Promise<ItemCustomValueRead[]> {
  const res = await apiFetch(`/items/${itemId}/custom-values`, { accessToken })
  return (await res.json()) as ItemCustomValueRead[]
}

export async function setItemCustomValue(
  itemId: string,
  body: ItemCustomValueSet,
  accessToken: string | null,
): Promise<ItemCustomValueRead> {
  const res = await apiFetch(`/items/${itemId}/custom-values`, {
    method: 'POST',
    body: JSON.stringify(body),
    accessToken,
  })
  return (await res.json()) as ItemCustomValueRead
}

export async function deleteItemCustomValue(
  itemId: string,
  fieldId: number,
  accessToken: string | null,
): Promise<void> {
  await apiFetch(`/items/${itemId}/custom-values/${fieldId}`, {
    method: 'DELETE',
    accessToken,
  })
}

function shouldClearCustomValue(value: unknown) {
  return value === null || value === undefined || value === ''
}

export async function saveItemCustomValues(
  itemId: string,
  customFields: CustomFieldRead[],
  values: CustomValueMap,
  accessToken: string | null,
): Promise<void> {
  for (const field of customFields) {
    const value = values[String(field.id)]
    if (shouldClearCustomValue(value)) {
      try {
        await deleteItemCustomValue(itemId, field.id, accessToken)
      } catch (error) {
        if (!isApiError(error) || error.status !== 404) throw error
      }
      continue
    }

    await setItemCustomValue(
      itemId,
      {
        custom_field_id: field.id,
        value,
      },
      accessToken,
    )
  }
}
