import { apiFetch } from "./client"

export interface AiSuggestResponse {
  name: string
  description: string | null
  category_suggestion: string | null
  tag_suggestions: string[]
}

export async function suggestFromImage(
  imageId: string,
  accessToken: string | null,
  hint?: string,
): Promise<AiSuggestResponse> {
  const res = await apiFetch("/ai/suggest-from-image", {
    method: "POST",
    accessToken,
    body: JSON.stringify({ image_id: imageId, hint: hint ?? undefined }),
  })
  return res.json()
}
