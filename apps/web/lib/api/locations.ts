import type { paths } from "@ims/api-types"
import { apiFetch } from "./client"

type LocationRead = paths["/api/locations"]["post"]["responses"]["201"]["content"]["application/json"]
type LocationCreate = paths["/api/locations"]["post"]["requestBody"]["content"]["application/json"]
type LocationUpdate = paths["/api/locations/{location_id}"]["patch"]["requestBody"]["content"]["application/json"]

export type { LocationRead, LocationCreate, LocationUpdate }

export async function listLocations(accessToken: string | null): Promise<LocationRead[]> {
  const res = await apiFetch("/locations", { accessToken })
  return (await res.json()) as LocationRead[]
}

export async function createLocation(body: LocationCreate, accessToken: string | null): Promise<LocationRead> {
  const res = await apiFetch("/locations", {
    method: "POST", body: JSON.stringify(body), accessToken,
  })
  return (await res.json()) as LocationRead
}

export async function updateLocation(id: number, body: LocationUpdate, accessToken: string | null): Promise<LocationRead> {
  const res = await apiFetch(`/locations/${id}`, {
    method: "PATCH", body: JSON.stringify(body), accessToken,
  })
  return (await res.json()) as LocationRead
}

export async function deleteLocation(id: number, accessToken: string | null): Promise<void> {
  await apiFetch(`/locations/${id}`, { method: "DELETE", accessToken })
}
