import type { components } from "@ims/api-types"

export type PublicList = components["schemas"]["PublicList"]

export class PublicListError extends Error {
  constructor(public status: number) {
    super("public list request failed")
  }
}

/** 公開讀取不經過登入 client，不送 cookie，也不觸發 refresh 或變更登入狀態。 */
export async function getPublicList(token: string, signal?: AbortSignal): Promise<PublicList> {
  const base = process.env.NEXT_PUBLIC_API_BASE ?? "/api"
  const response = await fetch(`${base}/public/list`, {
    headers: { "X-Share-Token": token },
    credentials: "omit",
    cache: "no-store",
    referrerPolicy: "no-referrer",
    signal,
  })
  if (!response.ok) throw new PublicListError(response.status)
  return response.json()
}

export function isPublicHttpLink(value: string): boolean {
  return /^https?:\/\//i.test(value)
}
