import type { paths } from "@ims/api-types"
import { apiFetch } from "./client"

type TagRead = paths["/api/tags"]["get"]["responses"]["200"]["content"]["application/json"][number]

export type { TagRead }

export async function listTags(q: string | undefined, accessToken: string | null): Promise<TagRead[]> {
  const qs = q ? `?q=${encodeURIComponent(q)}` : ""
  const res = await apiFetch(`/tags${qs}`, { accessToken })
  return (await res.json()) as TagRead[]
}
