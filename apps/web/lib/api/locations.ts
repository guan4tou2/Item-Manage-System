import type { paths } from "@ims/api-types"
import { apiFetch } from "./client"

export type LocationRead =
  paths["/api/locations"]["get"]["responses"]["200"]["content"]["application/json"][number]
export type LocationTreeNode =
  paths["/api/locations/tree"]["get"]["responses"]["200"]["content"]["application/json"][number]
export type LocationCreate =
  paths["/api/locations"]["post"]["requestBody"]["content"]["application/json"]
export type LocationUpdate =
  paths["/api/locations/{location_id}"]["patch"]["requestBody"]["content"]["application/json"]
export type LocationPath =
  paths["/api/locations/{location_id}/path"]["get"]["responses"]["200"]["content"]["application/json"]
export type LocationReorder =
  paths["/api/locations/reorder"]["post"]["requestBody"]["content"]["application/json"]

export async function listLocations(accessToken: string | null): Promise<LocationRead[]> {
  const res = await apiFetch("/locations", { accessToken })
  return (await res.json()) as LocationRead[]
}

/** 巢狀樹（節點附直接物品數；`item_count`、`children`）。 */
export async function getLocationTree(
  accessToken: string | null,
): Promise<LocationTreeNode[]> {
  const res = await apiFetch("/locations/tree", { accessToken })
  return (await res.json()) as LocationTreeNode[]
}

/** 節點至 root 的麵包屑（`path`＋`nodes`）。 */
export async function getLocationPath(
  id: number,
  accessToken: string | null,
): Promise<LocationPath> {
  const res = await apiFetch(`/locations/${id}/path`, { accessToken })
  return (await res.json()) as LocationPath
}

export async function createLocation(
  body: LocationCreate,
  accessToken: string | null,
): Promise<LocationRead> {
  const res = await apiFetch("/locations", {
    method: "POST",
    body: JSON.stringify(body),
    accessToken,
  })
  return (await res.json()) as LocationRead
}

export async function updateLocation(
  id: number,
  body: LocationUpdate,
  accessToken: string | null,
): Promise<LocationRead> {
  const res = await apiFetch(`/locations/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
    accessToken,
  })
  return (await res.json()) as LocationRead
}

/** 搬移節點（含子樹）；`parentId = null` → 移到最上層。 */
export async function moveLocation(
  id: number,
  parentId: number | null,
  accessToken: string | null,
): Promise<LocationRead> {
  return updateLocation(id, { parent_id: parentId }, accessToken)
}

export async function reorderLocations(
  body: LocationReorder,
  accessToken: string | null,
): Promise<LocationRead[]> {
  const res = await apiFetch("/locations/reorder", {
    method: "POST",
    body: JSON.stringify(body),
    accessToken,
  })
  return (await res.json()) as LocationRead[]
}

export async function deleteLocation(id: number, accessToken: string | null): Promise<void> {
  await apiFetch(`/locations/${id}`, { method: "DELETE", accessToken })
}
