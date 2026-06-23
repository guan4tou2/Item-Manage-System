import type { paths } from '@ims/api-types'

import { apiFetch } from './client'

export type StocktakeRead =
  paths['/api/stocktakes']['get']['responses']['200']['content']['application/json'][number]

export type StocktakeCreate =
  paths['/api/stocktakes']['post']['requestBody']['content']['application/json']

export type StocktakeDetail =
  paths['/api/stocktakes/{stocktake_id}']['get']['responses']['200']['content']['application/json']

export type StocktakeItemScan =
  paths['/api/stocktakes/{stocktake_id}/scan']['post']['requestBody']['content']['application/json']

export type StocktakeItemRead =
  paths['/api/stocktakes/{stocktake_id}/scan']['post']['responses']['200']['content']['application/json']

export async function listStocktakes(token: string | null): Promise<StocktakeRead[]> {
  return (await apiFetch('/stocktakes', { accessToken: token })).json()
}

export async function createStocktake(
  body: StocktakeCreate,
  token: string | null,
): Promise<StocktakeRead> {
  return (
    await apiFetch('/stocktakes', {
      method: 'POST',
      accessToken: token,
      body: JSON.stringify(body),
    })
  ).json()
}

export async function getStocktake(
  id: string,
  token: string | null,
): Promise<StocktakeDetail> {
  return (await apiFetch(`/stocktakes/${id}`, { accessToken: token })).json()
}

export async function scanStocktakeItem(
  id: string,
  body: StocktakeItemScan,
  token: string | null,
): Promise<StocktakeItemRead> {
  return (
    await apiFetch(`/stocktakes/${id}/scan`, {
      method: 'POST',
      accessToken: token,
      body: JSON.stringify(body),
    })
  ).json()
}

export async function completeStocktake(
  id: string,
  token: string | null,
): Promise<StocktakeDetail> {
  return (
    await apiFetch(`/stocktakes/${id}/complete`, {
      method: 'POST',
      accessToken: token,
    })
  ).json()
}

export async function cancelStocktake(
  id: string,
  token: string | null,
): Promise<StocktakeRead> {
  return (
    await apiFetch(`/stocktakes/${id}/cancel`, {
      method: 'POST',
      accessToken: token,
    })
  ).json()
}
