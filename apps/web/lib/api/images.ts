import { apiFetch } from "./client"

export interface ImageMeta {
  id: string
  owner_id: string
  filename: string
  mime_type: string
  size_bytes: number
  created_at: string
}

export async function uploadImage(file: File, accessToken: string | null): Promise<ImageMeta> {
  const fd = new FormData()
  fd.append("file", file)
  const res = await apiFetch("/images", {
    method: "POST",
    accessToken,
    body: fd,
  })
  return res.json()
}

export function imageUrl(imageId: string): string {
  return `/api/images/${imageId}`
}
