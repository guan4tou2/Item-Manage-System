/** Shared with the classic service worker. Keep this file entirely import-free. */
export interface OfflineStep {
  method: "POST" | "PATCH" | "DELETE"
  path: string
  body?: unknown
  headers?: Record<string, string>
  tolerate404?: boolean
}
export interface EngineItem {
  kind?: "create" | "update" | "delete"
  item_id?: string
  steps?: OfflineStep[]
  status: "pending" | "syncing" | "failed" | "conflict"
  attempts: number
  error_code: string | null
  server?: unknown
}
export type RequestStep = (step: OfflineStep) => Promise<{ status: number; body: unknown }>
export type EngineResult =
  | { type: "success"; item_id?: string }
  | { type: "partial"; item_id?: string; network?: boolean }
  | { type: "network" | "unauthorized" }
  | { type: "conflict"; server: unknown }
  | { type: "failed"; code: string }
  | { type: "server" }

export function failureCode(error: { status: number; body: unknown }): string {
  const body = error.body as { detail?: unknown; code?: string } | null
  const detail = body?.detail
  if (typeof detail === "string" && detail.includes("location_id")) return "location"
  if (typeof detail === "string" && detail.includes("category_id")) return "category"
  return (detail as { code?: string } | null)?.code ?? body?.code ?? String(error.status)
}

export async function executeItem(row: EngineItem, request: RequestStep): Promise<EngineResult> {
  let id = row.item_id
  const steps = row.steps ?? []
  if (!steps.length) return { type: "failed", code: "unknown" }
  for (let index = 0; index < steps.length; index++) {
    const step = steps[index]!
    if (step.path.includes("{item_id}") && !id) return index ? { type: "partial", item_id: id } : { type: "failed", code: "unknown" }
    let response
    try {
      response = await request({ ...step, path: step.path.replaceAll("{item_id}", encodeURIComponent(id ?? "")) })
    } catch {
      return index ? { type: "partial", item_id: id, network: true } : { type: "network" }
    }
    const { status, body } = response
    if ((status >= 200 && status < 300) || (status === 404 && step.tolerate404)) {
      if (index === 0 && (row.kind ?? "create") === "create") {
        const created = (body as { id?: unknown } | null)?.id
        if (typeof created === "string") id = created
      }
      continue
    }
    if (index) return { type: "partial", item_id: id }
    if (status === 401) return { type: "unauthorized" }
    if (status === 412) return { type: "conflict", server: (body as { detail?: { current?: unknown } } | null)?.detail?.current }
    if (status === 404 && row.kind === "delete") return { type: "success", item_id: id }
    if (status === 404 && row.kind === "update") return { type: "failed", code: "item_gone" }
    if (status >= 500) return { type: "server" }
    return { type: "failed", code: failureCode(response) }
  }
  return { type: "success", item_id: id }
}

/** null means remove. Never mutate the persisted record. */
export function applyResult<T extends EngineItem>(row: T, result: EngineResult): T | null {
  if (result.type === "success" || result.type === "partial") return null
  const next = { ...row, status: "pending" as EngineItem["status"] }
  if (result.type === "conflict") return { ...next, status: "conflict", error_code: "item_modified", server: result.server }
  if (result.type === "failed") return { ...next, status: "failed", error_code: result.code }
  if (result.type === "server") {
    next.attempts++
    next.error_code = "server"
    if (next.attempts >= 5) next.status = "failed"
  }
  return next
}
