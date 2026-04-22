import type { paths } from "@ims/api-types"
import { apiFetch } from "./client"

type CategoryTreeNode = paths["/api/categories"]["get"]["responses"]["200"]["content"]["application/json"][number]
type CategoryRead = paths["/api/categories"]["post"]["responses"]["201"]["content"]["application/json"]
type CategoryCreate = paths["/api/categories"]["post"]["requestBody"]["content"]["application/json"]
type CategoryUpdate = paths["/api/categories/{category_id}"]["patch"]["requestBody"]["content"]["application/json"]

export type { CategoryTreeNode, CategoryRead, CategoryCreate, CategoryUpdate }

export async function listCategories(accessToken: string | null): Promise<CategoryTreeNode[]> {
  const res = await apiFetch("/categories", { accessToken })
  return (await res.json()) as CategoryTreeNode[]
}

export async function createCategory(body: CategoryCreate, accessToken: string | null): Promise<CategoryRead> {
  const res = await apiFetch("/categories", {
    method: "POST", body: JSON.stringify(body), accessToken,
  })
  return (await res.json()) as CategoryRead
}

export async function updateCategory(id: number, body: CategoryUpdate, accessToken: string | null): Promise<CategoryRead> {
  const res = await apiFetch(`/categories/${id}`, {
    method: "PATCH", body: JSON.stringify(body), accessToken,
  })
  return (await res.json()) as CategoryRead
}

export async function deleteCategory(id: number, accessToken: string | null): Promise<void> {
  await apiFetch(`/categories/${id}`, { method: "DELETE", accessToken })
}
