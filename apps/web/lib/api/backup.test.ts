import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { downloadBackup, importBackup } from "./backup"

const originalFetch = global.fetch

function jsonResponse(payload: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "content-type": "application/json" },
    ...init,
  })
}

const importResult = {
  format_version: 4,
  mode: "create_only",
  dry_run: true,
  status: "ok",
  deleted_total: 0,
  entities: [],
  errors: [],
  errors_total: 0,
  warnings: [],
  reconciliation: [],
}

describe("backup api client", () => {
  const createObjectURL = vi.fn(() => "blob:backup")

  beforeEach(() => {
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: createObjectURL,
    })
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    })
  })

  afterEach(() => {
    global.fetch = originalFetch
    vi.restoreAllMocks()
    createObjectURL.mockClear()
  })

  it("downloads the backup with the server-provided filename", async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        jsonResponse({ format_version: 4 }, {
          headers: {
            "content-type": "application/json",
            "content-disposition": 'attachment; filename="ims-backup-alice-2026-10-17.json"',
          },
        }),
    )
    global.fetch = fetchMock as unknown as typeof global.fetch
    let clickedName: string | null = null
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(function (this: HTMLAnchorElement) {
        clickedName = this.download
      })

    await downloadBackup("jwt")

    expect(String(fetchMock.mock.calls[0]?.[0])).toBe("/api/backup/export")
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect(new Headers(init.headers).get("authorization")).toBe("Bearer jwt")
    expect(createObjectURL).toHaveBeenCalledTimes(1)
    expect(clickedName).toBe("ims-backup-alice-2026-10-17.json")
    expect(click).toHaveBeenCalledTimes(1)
  })

  it("falls back to ims-backup.json without a Content-Disposition filename", async () => {
    global.fetch = vi.fn(async () =>
      jsonResponse({ format_version: 4 }),
    ) as unknown as typeof global.fetch
    let clickedName: string | null = null
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(
      function (this: HTMLAnchorElement) {
        clickedName = this.download
      },
    )

    await downloadBackup(null)

    expect(clickedName).toBe("ims-backup.json")
  })

  it("uploads a dry-run create_only import without confirm", async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) => jsonResponse(importResult),
    )
    global.fetch = fetchMock as unknown as typeof global.fetch

    const file = new File(["{}"], "backup.json", { type: "application/json" })
    const result = await importBackup(file, { mode: "create_only", dryRun: true }, "jwt")

    expect(result.format_version).toBe(4)
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit
    const form = init.body as FormData
    expect(init.method).toBe("POST")
    expect(String(fetchMock.mock.calls[0]?.[0])).toBe("/api/backup/import")
    expect(form.get("file")).toBe(file)
    expect(form.get("mode")).toBe("create_only")
    expect(form.get("dry_run")).toBe("true")
    expect(form.get("confirm")).toBeNull()
  })

  it("sends confirm only for non-dry-run replace", async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        jsonResponse({ ...importResult, mode: "replace", dry_run: false }),
    )
    global.fetch = fetchMock as unknown as typeof global.fetch

    const file = new File(["{}"], "backup.json", { type: "application/json" })
    await importBackup(
      file,
      { mode: "replace", dryRun: false, confirm: "REPLACE" },
      "jwt",
    )
    const form = fetchMock.mock.calls[0]?.[1]?.body as FormData
    expect(form.get("mode")).toBe("replace")
    expect(form.get("dry_run")).toBe("false")
    expect(form.get("confirm")).toBe("REPLACE")

    fetchMock.mockClear()
    await importBackup(file, { mode: "replace", dryRun: true, confirm: "REPLACE" }, "jwt")
    const dryForm = fetchMock.mock.calls[0]?.[1]?.body as FormData
    expect(dryForm.get("dry_run")).toBe("true")
    expect(dryForm.get("confirm")).toBeNull()
  })
})
