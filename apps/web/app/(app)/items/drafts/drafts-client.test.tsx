import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { NextIntlClientProvider } from "next-intl"
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest"

import * as aiApi from "@/lib/api/ai-drafts"
import type { DraftListResponse, DraftRead } from "@/lib/api/ai-drafts"
import { ApiError } from "@/lib/api/client"
import { uploadImage } from "@/lib/api/images"
import enMessages from "@/messages/en.json"
import { toast } from "sonner"

import { DraftsClient } from "./drafts-client"

const flags = vi.hoisted(() => ({ readOnly: false }))

vi.mock("@/lib/auth/use-readonly", () => ({ useReadOnly: () => flags.readOnly }))
vi.mock("@/lib/auth/use-auth", () => ({ useAccessToken: () => "jwt" }))

vi.mock("@/lib/hooks/use-categories", () => ({
  useCategories: () => ({
    data: [{ id: 3, name: "Kitchen", parent_id: null, children: [] }],
  }),
}))

vi.mock("@/lib/hooks/use-locations", () => ({
  useLocations: () => ({
    data: [
      {
        id: 7,
        parent_id: null,
        name: "Kitchen shelf",
        kind: null,
        sort_order: 0,
        floor_plan_image_id: null,
        path: "Kitchen shelf",
      },
    ],
  }),
}))

vi.mock("@/lib/hooks/use-tags", () => ({
  useTags: () => ({ data: [{ id: 1, name: "coffee" }] }),
}))

vi.mock("@/lib/api/images", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/images")>()),
  uploadImage: vi.fn(),
}))

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() },
}))

function photo(name: string): File {
  return new File(["x"], name, { type: "image/png" })
}

function meta(id: string) {
  return {
    id,
    owner_id: "owner-1",
    filename: `${id}.png`,
    mime_type: "image/png",
    size_bytes: 12,
    created_at: "2026-10-19T02:11:00Z",
  }
}

function draft(overrides: Partial<DraftRead> = {}): DraftRead {
  return {
    id: "draft-1",
    source: "batch_photo",
    status: "pending",
    image_id: "img-1",
    item_id: null,
    error_code: null,
    payload: {
      version: 1,
      ai: null,
      history: { category: null, location: null, tags: [] },
    },
    processed_at: null,
    created_at: "2026-10-19T02:11:03Z",
    ...overrides,
  }
}

function readyDraft(id: string, name = "Coffee dripper"): DraftRead {
  return draft({
    id,
    status: "ready",
    processed_at: "2026-10-19T02:11:09Z",
    payload: {
      version: 1,
      ai: {
        name,
        description: null,
        category_suggestion: "Kitchen",
        tag_suggestions: [],
      },
      history: { category: null, location: null, tags: [] },
    },
  })
}

function listOf(items: DraftRead[]): DraftListResponse {
  const counts = {
    pending: 0,
    processing: 0,
    ready: 0,
    failed: 0,
    accepted: 0,
    discarded: 0,
  }
  for (const item of items) counts[item.status] += 1
  return { items, total: items.length, counts }
}

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (error: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

function renderClient() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <DraftsClient />
      </NextIntlClientProvider>
    </QueryClientProvider>,
  )
}

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn()
  Element.prototype.hasPointerCapture = vi.fn()
  Element.prototype.setPointerCapture = vi.fn()
  Element.prototype.releasePointerCapture = vi.fn()
})

beforeEach(() => {
  vi.clearAllMocks()
  flags.readOnly = false
  vi.spyOn(aiApi, "listDrafts").mockResolvedValue(listOf([]))
  vi.spyOn(aiApi, "createDrafts").mockResolvedValue({ created: [], skipped_image_ids: [] })
  vi.spyOn(aiApi, "processDraft").mockResolvedValue(draft({ status: "ready" }))
  vi.spyOn(aiApi, "acceptDraft").mockResolvedValue({
    draft: draft({ status: "accepted", item_id: "item-1" }),
    item: { id: "item-1", name: "Coffee dripper" } as never,
  })
  vi.spyOn(aiApi, "discardDraft").mockResolvedValue(draft({ status: "discarded" }))
  vi.spyOn(aiApi, "discardDrafts").mockResolvedValue({ discarded: 0, skipped: [] })
})

describe("DraftsClient 上傳區", () => {
  it("uploads the chosen photos and creates drafts, then clears the selection", async () => {
    const user = userEvent.setup()
    vi.mocked(uploadImage)
      .mockResolvedValueOnce(meta("img-1"))
      .mockResolvedValueOnce(meta("img-2"))

    renderClient()
    await waitFor(() => expect(vi.mocked(aiApi.listDrafts)).toHaveBeenCalled())

    await user.upload(screen.getByLabelText("Choose photos to intake"), [
      photo("a.png"),
      photo("b.png"),
    ])

    await waitFor(() =>
      expect(aiApi.createDrafts).toHaveBeenCalledWith(["img-1", "img-2"], "jwt"),
    )
    expect(uploadImage).toHaveBeenCalledTimes(2)
    await waitFor(() => expect(screen.queryByTestId("upload-file-0")).not.toBeInTheDocument())
  })

  it("caps the batch at ten photos and explains the rest", async () => {
    const user = userEvent.setup()
    const gate = deferred<void>()
    vi.mocked(uploadImage).mockImplementation(async () => {
      await gate.promise
      return meta("img-1")
    })

    renderClient()
    await user.upload(
      screen.getByLabelText("Choose photos to intake"),
      Array.from({ length: 12 }, (_, index) => photo(`p${index}.png`)),
    )

    // 僅前 10 張進列，其餘以提示說明
    expect(screen.getByText("Up to 10 photos at a time — 2 ignored")).toBeInTheDocument()
    expect(screen.getByTestId("upload-file-9")).toBeInTheDocument()
    expect(screen.queryByTestId("upload-file-10")).not.toBeInTheDocument()

    gate.resolve()

    await waitFor(() => expect(uploadImage).toHaveBeenCalledTimes(10))
    await waitFor(() =>
      expect(aiApi.createDrafts).toHaveBeenCalledWith(
        Array.from({ length: 10 }, () => "img-1"),
        "jwt",
      ),
    )
  })

  it("keeps a failed row with a retry action", async () => {
    const user = userEvent.setup()
    vi.mocked(uploadImage)
      .mockRejectedValueOnce(new Error("boom"))
      .mockResolvedValueOnce(meta("img-1"))

    renderClient()
    await user.upload(screen.getByLabelText("Choose photos to intake"), [photo("a.png")])

    const row = await screen.findByTestId("upload-file-0")
    expect(within(row).getByText("Upload failed")).toBeInTheDocument()
    // 失敗時不建立草稿
    expect(aiApi.createDrafts).not.toHaveBeenCalled()

    await user.click(within(row).getByRole("button", { name: "Retry" }))

    await waitFor(() => expect(aiApi.createDrafts).toHaveBeenCalledWith(["img-1"], "jwt"))
  })

  it("accepts dropped files", async () => {
    vi.mocked(uploadImage).mockResolvedValue(meta("img-1"))

    renderClient()
    fireEvent.drop(screen.getByTestId("draft-dropzone"), {
      dataTransfer: { files: [photo("dropped.png")] },
    })

    await waitFor(() => expect(aiApi.createDrafts).toHaveBeenCalledWith(["img-1"], "jwt"))
  })

  it("shows a block error with retry when creating drafts fails", async () => {
    const user = userEvent.setup()
    vi.mocked(uploadImage).mockResolvedValue(meta("img-1"))
    vi.mocked(aiApi.createDrafts)
      .mockRejectedValueOnce(new Error("boom"))
      .mockResolvedValueOnce({ created: [draft()], skipped_image_ids: [] })

    renderClient()
    await user.upload(screen.getByLabelText("Choose photos to intake"), [photo("a.png")])

    expect(await screen.findByText("Could not create drafts, please retry")).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Retry" }))

    await waitFor(() => expect(aiApi.createDrafts).toHaveBeenCalledTimes(2))
    await waitFor(() =>
      expect(screen.queryByText("Could not create drafts, please retry")).not.toBeInTheDocument(),
    )
  })

  it("tells the user when photos were skipped because drafts already existed", async () => {
    const user = userEvent.setup()
    vi.mocked(uploadImage).mockResolvedValue(meta("img-1"))
    vi.mocked(aiApi.createDrafts).mockResolvedValue({
      created: [],
      skipped_image_ids: ["img-1"],
    })

    renderClient()
    await user.upload(screen.getByLabelText("Choose photos to intake"), [photo("a.png")])

    await waitFor(() =>
      expect(toast.info).toHaveBeenCalledWith(
        "1 photo(s) already had a draft and were skipped",
      ),
    )
  })
})

describe("DraftsClient 處理迴圈", () => {
  it("processes pending drafts one at a time", async () => {
    vi.mocked(aiApi.listDrafts).mockResolvedValue(listOf([draft({ id: "d1" }), draft({ id: "d2" })]))
    const first = deferred<DraftRead>()
    vi.mocked(aiApi.processDraft)
      .mockImplementationOnce(() => first.promise)
      .mockResolvedValue(draft({ id: "d2", status: "failed", error_code: "upstream_error" }))

    renderClient()

    await waitFor(() => expect(aiApi.processDraft).toHaveBeenCalledWith("d1", "jwt"))
    expect(aiApi.processDraft).toHaveBeenCalledTimes(1)
    expect(
      within(screen.getByTestId("draft-card-d1")).getByTestId("draft-status"),
    ).toHaveTextContent("Recognizing…")
    expect(
      within(screen.getByTestId("draft-card-d2")).getByTestId("draft-status"),
    ).toHaveTextContent("Queued")

    // 第一張完成後清單更新 → 自動續行第二張
    vi.mocked(aiApi.listDrafts).mockResolvedValue(
      listOf([draft({ id: "d1", status: "ready" }), draft({ id: "d2" })]),
    )
    first.resolve(draft({ id: "d1", status: "ready" }))

    await waitFor(() => expect(aiApi.processDraft).toHaveBeenCalledWith("d2", "jwt"))
    expect(aiApi.processDraft).toHaveBeenCalledTimes(2)
  })

  it("does not auto-resend drafts that are already processing", async () => {
    vi.mocked(aiApi.listDrafts).mockResolvedValue(listOf([draft({ id: "d1", status: "processing" })]))

    renderClient()

    expect(
      await screen.findByRole("button", { name: "Recognize again" }),
    ).toBeInTheDocument()
    await waitFor(() => expect(vi.mocked(aiApi.listDrafts)).toHaveBeenCalled())
    expect(aiApi.processDraft).not.toHaveBeenCalled()
  })

  it("keeps going when a draft fails for business reasons", async () => {
    vi.mocked(aiApi.listDrafts).mockResolvedValue(listOf([draft({ id: "d1" }), draft({ id: "d2" })]))
    vi.mocked(aiApi.processDraft).mockImplementationOnce(async () => {
      vi.mocked(aiApi.listDrafts).mockResolvedValue(
        listOf([
          draft({ id: "d1", status: "failed", error_code: "upstream_error" }),
          draft({ id: "d2" }),
        ]),
      )
      return draft({ id: "d1", status: "failed", error_code: "upstream_error" })
    })

    renderClient()

    await waitFor(() => expect(aiApi.processDraft).toHaveBeenCalledWith("d2", "jwt"))
    expect(toast.error).not.toHaveBeenCalled()
  })

  it("stops on a transport error and resumes on demand", async () => {
    const user = userEvent.setup()
    vi.mocked(aiApi.listDrafts).mockResolvedValue(listOf([draft({ id: "d1" }), draft({ id: "d2" })]))
    vi.mocked(aiApi.processDraft).mockRejectedValueOnce(new Error("network down"))

    renderClient()

    expect(
      await screen.findByText(
        "Processing stopped (connection problem); drafts that finished are unaffected",
      ),
    ).toBeInTheDocument()
    expect(aiApi.processDraft).toHaveBeenCalledTimes(1)

    // 中斷的那一張維持 pending：續行時應重試它
    const hang = deferred<DraftRead>()
    vi.mocked(aiApi.processDraft).mockImplementationOnce(() => hang.promise)

    await user.click(screen.getByRole("button", { name: "Continue" }))

    await waitFor(() => expect(aiApi.processDraft).toHaveBeenCalledTimes(2))
    expect(vi.mocked(aiApi.processDraft).mock.calls[1]?.[0]).toBe("d1")
    expect(screen.queryByRole("button", { name: "Continue" })).not.toBeInTheDocument()
  })

  it("skips drafts the server rejects and continues the queue", async () => {
    vi.mocked(aiApi.listDrafts).mockResolvedValue(listOf([draft({ id: "d1" }), draft({ id: "d2" })]))
    vi.mocked(aiApi.processDraft)
      .mockRejectedValueOnce(new ApiError(409, { detail: "draft already accepted" }))
      .mockResolvedValue(draft({ id: "d2", status: "failed", error_code: "upstream_error" }))

    renderClient()

    await waitFor(() => expect(aiApi.processDraft).toHaveBeenCalledWith("d2", "jwt"))
    expect(
      screen.queryByRole("button", { name: "Continue" }),
    ).not.toBeInTheDocument()
  })

  it("shows skeletons while the queue loads and an empty state afterwards", async () => {
    const pending = deferred<DraftListResponse>()
    vi.mocked(aiApi.listDrafts).mockImplementationOnce(() => pending.promise)

    renderClient()

    expect(screen.getAllByTestId("draft-card-skeleton")).toHaveLength(3)

    pending.resolve(listOf([]))
    expect(await screen.findByText("No drafts yet")).toBeInTheDocument()
    expect(screen.getByText("Upload photos above to start")).toBeInTheDocument()
    // 空狀態仍保留上傳入口
    expect(screen.getByTestId("draft-upload-zone")).toBeInTheDocument()
  })

  it("shows a retryable block error when the queue cannot load", async () => {
    const user = userEvent.setup()
    vi.mocked(aiApi.listDrafts).mockRejectedValueOnce(new Error("boom"))

    renderClient()

    expect(await screen.findByText("Could not load drafts")).toBeInTheDocument()
    vi.mocked(aiApi.listDrafts).mockResolvedValue(listOf([readyDraft("d1")]))

    await user.click(screen.getByRole("button", { name: "Retry" }))

    expect(await screen.findByTestId("draft-card-d1")).toBeInTheDocument()
  })
})

describe("DraftsClient 批量條", () => {
  it("disables bulk actions while nothing is selected", async () => {
    vi.mocked(aiApi.listDrafts).mockResolvedValue(listOf([readyDraft("d1")]))

    renderClient()

    const bar = await screen.findByTestId("draft-bulk-bar")
    expect(within(bar).getByRole("button", { name: "Accept all" })).toBeDisabled()
    expect(within(bar).getByRole("button", { name: "Discard all" })).toBeDisabled()
  })

  it("accepts only the selected ready drafts and reports the skipped ones", async () => {
    const user = userEvent.setup()
    vi.mocked(aiApi.listDrafts).mockResolvedValue(
      listOf([readyDraft("d1"), draft({ id: "d2", status: "failed", error_code: "ai_disabled" })]),
    )

    renderClient()
    const bar = await screen.findByTestId("draft-bulk-bar")
    await user.click(within(bar).getByRole("button", { name: "Select all" }))

    expect(within(bar).getByText("2 selected")).toBeInTheDocument()

    await user.click(within(bar).getByRole("button", { name: "Accept all" }))

    await waitFor(() => expect(aiApi.acceptDraft).toHaveBeenCalledTimes(1))
    expect(vi.mocked(aiApi.acceptDraft).mock.calls[0]?.[0]).toBe("d1")
    expect(vi.mocked(aiApi.acceptDraft).mock.calls[0]?.[1]).toMatchObject({
      name: "Coffee dripper",
    })
    await waitFor(() =>
      expect(toast.info).toHaveBeenCalledWith("Skipped 1 (not ready to review)"),
    )
    expect(toast.success).toHaveBeenCalledWith("Accepted 1 drafts")
  })

  it("discards the selection through the bulk endpoint", async () => {
    const user = userEvent.setup()
    vi.mocked(aiApi.listDrafts).mockResolvedValue(
      listOf([readyDraft("d1"), draft({ id: "d2", status: "failed", error_code: "ai_disabled" })]),
    )
    vi.mocked(aiApi.discardDrafts).mockResolvedValue({ discarded: 2, skipped: [] })

    renderClient()
    const bar = await screen.findByTestId("draft-bulk-bar")
    await user.click(within(bar).getByRole("button", { name: "Select all" }))
    await user.click(within(bar).getByRole("button", { name: "Discard all" }))

    await waitFor(() =>
      expect(aiApi.discardDrafts).toHaveBeenCalledWith(["d1", "d2"], "jwt"),
    )
    expect(toast.success).toHaveBeenCalledWith("Discarded 2 drafts")
  })

  it("reports single accept and discard outcomes through toasts", async () => {
    const user = userEvent.setup()
    vi.mocked(aiApi.listDrafts).mockResolvedValue(listOf([readyDraft("d1")]))

    renderClient()
    await user.click(await screen.findByRole("button", { name: "Accept" }))

    await waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith("Accepted “Coffee dripper”"),
    )

    vi.mocked(aiApi.listDrafts).mockResolvedValue(listOf([readyDraft("d2", "Tea tin")]))
    vi.mocked(aiApi.discardDraft).mockResolvedValue(draft({ id: "d2", status: "discarded" }))

    await user.click(await screen.findByRole("button", { name: "Discard" }))

    await waitFor(() => expect(toast.success).toHaveBeenCalledWith("Draft discarded"))
  })
})

describe("DraftsClient 唯讀", () => {
  it("replaces the queue with the viewer notice for viewers", () => {
    flags.readOnly = true

    renderClient()

    expect(screen.getByTestId("viewer-notice")).toBeInTheDocument()
    expect(screen.queryByTestId("draft-upload-zone")).not.toBeInTheDocument()
    expect(vi.mocked(aiApi.listDrafts)).not.toHaveBeenCalled()
  })
})
