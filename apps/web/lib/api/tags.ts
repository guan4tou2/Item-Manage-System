import type { paths } from "@ims/api-types"
import { apiFetch } from "./client"

type TagRead = paths["/api/tags"]["get"]["responses"]["200"]["content"]["application/json"][number]
type TagReadWithCount = paths["/api/tags/with-counts"]["get"]["responses"]["200"]["content"]["application/json"][number]
type TagMergeResult = paths["/api/tags/{tag_id}/merge"]["post"]["responses"]["200"]["content"]["application/json"]
type PruneOrphansResult = paths["/api/tags/prune-orphans"]["post"]["responses"]["200"]["content"]["application/json"]

export type { TagRead, TagReadWithCount, TagMergeResult, PruneOrphansResult }

export async function listTags(
  q: string | undefined,
  accessToken: string | null,
): Promise<TagRead[]> {
  const qs = q ? `?q=${encodeURIComponent(q)}` : ""
  const res = await apiFetch(`/tags${qs}`, { accessToken })
  return (await res.json()) as TagRead[]
}

export async function listTagsWithCounts(
  accessToken: string | null,
): Promise<TagReadWithCount[]> {
  const res = await apiFetch("/tags/with-counts", { accessToken })
  return (await res.json()) as TagReadWithCount[]
}

export async function renameTag(
  tagId: number,
  name: string,
  accessToken: string | null,
): Promise<TagRead> {
  const res = await apiFetch(`/tags/${tagId}`, {
    accessToken,
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  })
  return (await res.json()) as TagRead
}

export async function mergeTag(
  sourceId: number,
  targetId: number,
  accessToken: string | null,
): Promise<TagMergeResult> {
  const res = await apiFetch(`/tags/${sourceId}/merge`, {
    accessToken,
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target_id: targetId }),
  })
  return (await res.json()) as TagMergeResult
}

export async function deleteTag(
  tagId: number,
  force: boolean,
  accessToken: string | null,
): Promise<void> {
  const qs = force ? "?force=true" : ""
  await apiFetch(`/tags/${tagId}${qs}`, { accessToken, method: "DELETE" })
}

export async function pruneOrphanTags(
  accessToken: string | null,
): Promise<PruneOrphansResult> {
  const res = await apiFetch("/tags/prune-orphans", {
    accessToken,
    method: "POST",
  })
  return (await res.json()) as PruneOrphansResult
}
