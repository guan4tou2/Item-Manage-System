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

// 顯示既有圖片請用 `components/common/auth-image.tsx`（`GET /api/images/{id}` 需 Bearer，
// `<img src>` 帶不了 token，故以 apiFetch 取 blob 後轉 object URL）。
