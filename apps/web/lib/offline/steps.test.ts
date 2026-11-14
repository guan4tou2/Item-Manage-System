import { afterEach, expect, it, vi } from "vitest"
import { submitItem } from "./submission"
import { buildSteps, updateBody, mergePending } from "./steps"
import type { PendingItem } from "./storage"
import { saveItemCustomValues } from "@/lib/api/customization"
import { updateItem } from "@/lib/api/items"

const draft: PendingItem = {
  client_id: "key", owner_user_id: "owner", status: "pending", error_code: null, attempts: 0, created_at: "first",
  values: { name: "電池", description: "", barcode: "", cost: "15.50", quantity: 2, category_id: null, location_id: 3, image_id: null, tag_names: ["備品"], custom_values: { "1": false, "2": "", "3": 0, "4": "值" } },
  customFields: [1, 2, 3, 4].map((id) => ({ id } as never)), trackBatches: true,
}
afterEach(() => vi.unstubAllGlobals())
function capture() {
  const calls: unknown[] = []
  const fetch = vi.fn(async (url: string, init: RequestInit) => {
    const headers = new Headers(init.headers)
    calls.push({ path: url.replace(/^\/api/, ""), method: init.method, body: init.body ? JSON.parse(String(init.body)) : undefined,
      headers: Object.fromEntries(["Idempotency-Key", "If-Match"].filter((key) => headers.has(key)).map((key) => [key, headers.get(key)])) })
    return new Response(JSON.stringify({ id: "created" }), { status: 200 })
  })
  vi.stubGlobal("fetch", fetch)
  return calls
}
function serializedSteps(row: PendingItem) {
  return buildSteps(row).map((step) => ({ method: step.method, path: step.path.replaceAll("{item_id}", "created"),
    body: step.body === undefined ? undefined : JSON.parse(JSON.stringify(step.body)), headers: step.headers ?? {} }))
}
it("create requests match the real online submission in payload, order and idempotency key", async () => {
  const calls = capture()
  await submitItem(draft, draft.client_id, "token")
  expect(serializedSteps(draft)).toEqual(calls)
  expect(calls).toHaveLength(6)
})
it.each([false, true])("update requests match online including tracked quantity (%s) and custom clear/write", async (tracking) => {
  const calls = capture()
  const row = { ...draft, kind: "update" as const, item_id: "created", base_updated_at: "original", trackBatches: tracking }
  await updateItem("created", updateBody(row.values, tracking), "token", "original")
  await saveItemCustomValues("created", row.customFields, row.values.custom_values, "token")
  expect(serializedSteps(row)).toEqual(calls)
  expect("quantity" in (buildSteps(row)[0]!.body as object)).toBe(!tracking)
  expect(buildSteps(row)[2]).toMatchObject({ method: "DELETE", tolerate404: true })
})
it("D7 replaces updates and update→delete with earliest base and identity, isolates owners upstream", () => {
  const old = { ...draft, kind: "update" as const, item_id: "item", base_updated_at: "earliest" }
  for (const kind of ["update", "delete"] as const) {
    const incoming = { ...old, kind, client_id: "new", base_updated_at: "later", created_at: "later", values: { ...old.values, name: "latest" } }
    expect(mergePending(incoming, [old])).toMatchObject({ kind, client_id: "key", base_updated_at: "earliest", created_at: "first", values: { name: "latest" } })
  }
  const deletion = { ...old, kind: "delete" as const }
  expect(mergePending({ ...old, values: { ...old.values, name: "cannot resurrect" } }, [deletion])).toBe(deletion)
  expect(mergePending(draft, [draft])).toBe(draft)
})
