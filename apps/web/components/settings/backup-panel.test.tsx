import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { NextIntlClientProvider } from "next-intl"
import { toast } from "sonner"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import * as api from "@/lib/api/backup"
import { ApiError } from "@/lib/api/client"
import { useAuthStore } from "@/lib/auth/auth-store"
import enMessages from "@/messages/en.json"

import { BackupPanel } from "./backup-panel"

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => "jwt",
}))

vi.mock("@/lib/api/backup", () => ({
  downloadBackup: vi.fn(),
  importBackup: vi.fn(),
}))

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

const t = enMessages.settings.backup

const dryRunResult = {
  format_version: 4,
  mode: "create_only" as const,
  dry_run: true,
  status: "ok" as const,
  deleted_total: 0,
  entities: [
    {
      entity: "items",
      existing: 3,
      imported: 2,
      created: 2,
      reused: 0,
      renamed: 0,
      skipped: 0,
      errors: 0,
    },
    {
      entity: "categories",
      existing: 0,
      imported: 1,
      created: 1,
      reused: 0,
      renamed: 0,
      skipped: 0,
      errors: 0,
    },
  ],
  errors: [],
  errors_total: 0,
  warnings: [],
  reconciliation: [],
}

const replaceDryRunResult = {
  ...dryRunResult,
  mode: "replace" as const,
  deleted_total: 7,
}

function fileInput(container: HTMLElement) {
  return container.querySelector('input[type="file"]') as HTMLInputElement
}

const backupFile = () =>
  new File(["{}"], "backup.json", { type: "application/json" })

function renderPanel() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return {
    ...render(
      <QueryClientProvider client={queryClient}>
        <NextIntlClientProvider locale="en" messages={enMessages}>
          <BackupPanel />
        </NextIntlClientProvider>
      </QueryClientProvider>,
    ),
    queryClient,
  }
}

describe("BackupPanel export card", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.downloadBackup).mockResolvedValue(undefined)
  })

  it("renders the export card with description and button", () => {
    renderPanel()

    expect(screen.getByText(t.export.title)).toBeInTheDocument()
    expect(screen.getByText(t.export.description)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: t.export.download })).toBeEnabled()
  })

  it("downloads the backup with the access token and toasts success", async () => {
    renderPanel()

    fireEvent.click(screen.getByRole("button", { name: t.export.download }))

    await waitFor(() => {
      expect(vi.mocked(api.downloadBackup)).toHaveBeenCalledWith("jwt")
    })
    expect(vi.mocked(toast.success)).toHaveBeenCalledWith(t.export.toast.done)
  })

  it("toasts an error when the download fails", async () => {
    vi.mocked(api.downloadBackup).mockRejectedValue(new Error("boom"))
    renderPanel()

    fireEvent.click(screen.getByRole("button", { name: t.export.download }))

    await waitFor(() => {
      expect(vi.mocked(toast.error)).toHaveBeenCalledWith(t.export.toast.failed)
    })
  })
})

describe("BackupPanel import card", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.downloadBackup).mockResolvedValue(undefined)
  })

  it("previews a picked file with a create_only dry-run and renders the entity table", async () => {
    vi.mocked(api.importBackup).mockResolvedValue(dryRunResult)
    const { container } = renderPanel()

    // 無檔案空態
    expect(screen.getByText(t.import.empty)).toBeInTheDocument()

    const file = backupFile()
    await userEvent.upload(fileInput(container), file)

    await waitFor(() =>
      expect(vi.mocked(api.importBackup)).toHaveBeenCalledWith(
        file,
        { mode: "create_only", dryRun: true },
        "jwt",
      ),
    )
    expect(screen.getByText(t.summary.title)).toBeInTheDocument()

    const itemsRow = screen.getByRole("row", {
      name: new RegExp(t.entities.items, "i"),
    })
    const itemsCells = within(itemsRow)
      .getAllByRole("cell")
      .map((cell) => cell.textContent)
    // 匯入後 = existing + created + renamed = 3 + 2
    expect(itemsCells).toEqual([
      t.entities.items,
      "3",
      "5",
      "2",
      "0",
      "0",
      "0",
      "0",
    ])

    const categoriesRow = screen.getByRole("row", {
      name: new RegExp(t.entities.categories, "i"),
    })
    expect(
      within(categoriesRow)
        .getAllByRole("cell")
        .map((cell) => cell.textContent),
    ).toEqual([t.entities.categories, "0", "1", "1", "0", "0", "0", "0"])
  })

  it("mirrors the summary as cards for small screens（§5.7 寬表格卡片化）", async () => {
    vi.mocked(api.importBackup).mockResolvedValue(dryRunResult)
    const { container } = renderPanel()

    await userEvent.upload(fileInput(container), backupFile())
    await screen.findByText(t.summary.title)

    const cards = within(screen.getByTestId("backup-summary-cards"))
    const itemsCard = cards.getByText(t.entities.items).closest("li") as HTMLElement
    expect(itemsCard).not.toBeNull()
    // 現有 3 → 匯入後 5；建立 2
    expect(itemsCard).toHaveTextContent(
      t.summary.mobileFlow.replace("{existing}", "3").replace("{after}", "5"),
    )
    expect(within(itemsCard).getByText(t.summary.created)).toBeInTheDocument()
    expect(within(itemsCard).getByText("2")).toBeInTheDocument()
  })

  it("re-runs the dry-run with mode=replace when the mode is switched", async () => {
    vi.mocked(api.importBackup)
      .mockResolvedValueOnce(dryRunResult)
      .mockResolvedValueOnce(replaceDryRunResult)
    const { container } = renderPanel()

    const file = backupFile()
    await userEvent.upload(fileInput(container), file)
    await waitFor(() => expect(vi.mocked(api.importBackup)).toHaveBeenCalledTimes(1))

    await userEvent.click(
      screen.getByRole("radio", { name: t.import.modeReplace }),
    )

    await waitFor(() =>
      expect(vi.mocked(api.importBackup)).toHaveBeenLastCalledWith(
        file,
        { mode: "replace", dryRun: true },
        "jwt",
      ),
    )
    // replace 摘要之「匯入後」＝ created + renamed（不含 existing）
    const itemsRow = screen.getByRole("row", {
      name: new RegExp(t.entities.items, "i"),
    })
    expect(
      within(itemsRow)
        .getAllByRole("cell")
        .map((cell) => cell.textContent),
    ).toEqual([t.entities.items, "3", "2", "2", "0", "0", "0", "0"])
    expect(
      screen.getByText(t.replace.warning.replace("{count}", "7")),
    ).toBeInTheDocument()
  })

  it("shows at most five row errors, warnings, and reconciliation mismatches", async () => {
    const errors = Array.from({ length: 5 }, (_, i) => ({
      entity: "items",
      index: i,
      name: `壞列 ${i}`,
      message: `第 ${i} 列有誤`,
    }))
    vi.mocked(api.importBackup).mockResolvedValue({
      ...dryRunResult,
      status: "partial" as const,
      errors,
      errors_total: 7,
      warnings: ["幣別 create_only 不還原"],
      reconciliation: [
        {
          item_id: "11111111-1111-4111-8111-111111111111",
          name: "米",
          quantity: 5,
          batch_total: 3,
        },
      ],
    })
    const { container } = renderPanel()
    await userEvent.upload(fileInput(container), backupFile())

    expect(await screen.findByText(t.import.errorsTitle)).toBeInTheDocument()
    expect(screen.getAllByText(/第 \d 列有誤/)).toHaveLength(5)
    expect(screen.getByText(t.import.moreErrors.replace("{count}", "2"))).toBeInTheDocument()
    expect(screen.getByText("幣別 create_only 不還原")).toBeInTheDocument()
    expect(screen.getByText(t.import.reconciliationTitle)).toBeInTheDocument()
    expect(
      screen.getByText(
        t.import.reconciliationRow
          .replace("{name}", "米")
          .replace("{quantity}", "5")
          .replace("{batch_total}", "3"),
      ),
    ).toBeInTheDocument()
  })

  it("gates the replace confirm button on the exact REPLACE phrase", async () => {
    vi.mocked(api.importBackup).mockResolvedValue(replaceDryRunResult)
    const { container } = renderPanel()

    await userEvent.click(
      screen.getByRole("radio", { name: t.import.modeReplace }),
    )
    await userEvent.upload(fileInput(container), backupFile())
    expect(
      await screen.findByText(t.replace.warning.replace("{count}", "7")),
    ).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: t.replace.downloadFirst }))
    await waitFor(() =>
      expect(vi.mocked(api.downloadBackup)).toHaveBeenCalledWith("jwt"),
    )

    const confirmButton = screen.getByRole("button", { name: t.import.confirm })
    expect(confirmButton).toBeDisabled()

    const confirmInput = screen.getByPlaceholderText("REPLACE")
    await userEvent.type(confirmInput, "WRONG")
    expect(confirmButton).toBeDisabled()

    await userEvent.clear(confirmInput)
    await userEvent.type(confirmInput, "REPLACE")
    expect(confirmButton).toBeEnabled()
  })

  it("renders a hard 400 detail inline", async () => {
    vi.mocked(api.importBackup).mockRejectedValue(
      new ApiError(400, { detail: "format_version 不支援（> 4）" }),
    )
    const { container } = renderPanel()

    await userEvent.upload(fileInput(container), backupFile())

    expect(
      await screen.findByText("format_version 不支援（> 4）"),
    ).toBeInTheDocument()
    expect(vi.mocked(toast.error)).toHaveBeenCalled()
  })

  it("marks the card busy while the dry-run is in flight", async () => {
    let resolveDryRun!: (value: typeof dryRunResult) => void
    vi.mocked(api.importBackup).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveDryRun = resolve
        }),
    )
    const { container } = renderPanel()

    await userEvent.upload(fileInput(container), backupFile())

    await waitFor(() =>
      expect(screen.getByText(t.import.analyzing)).toBeInTheDocument(),
    )
    expect(container.querySelector('[aria-busy="true"]')).not.toBeNull()

    resolveDryRun(dryRunResult)
    expect(await screen.findByText(t.summary.title)).toBeInTheDocument()
  })
})

const appliedResult = {
  ...dryRunResult,
  dry_run: false,
}

describe("BackupPanel import execution", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.downloadBackup).mockResolvedValue(undefined)
  })

  it("imports with create_only, reports success, and invalidates queries", async () => {
    vi.mocked(api.importBackup)
      .mockResolvedValueOnce(dryRunResult)
      .mockResolvedValueOnce(appliedResult)
    const { container, queryClient } = renderPanel()
    const invalidate = vi.spyOn(queryClient, "invalidateQueries")

    await userEvent.upload(fileInput(container), backupFile())
    await screen.findByText(t.summary.title)
    await userEvent.click(screen.getByRole("button", { name: t.import.confirm }))

    await waitFor(() =>
      expect(vi.mocked(api.importBackup)).toHaveBeenLastCalledWith(
        expect.any(File),
        { mode: "create_only", dryRun: false },
        "jwt",
      ),
    )
    const report = await screen.findByRole("status")
    expect(report).toHaveTextContent(
      t.result.ok.replace("{created}", "3").replace("{deleted}", "0"),
    )
    expect(invalidate).toHaveBeenCalled()

    // 「重新比對」以同一檔案重跑 dry-run
    vi.mocked(api.importBackup).mockResolvedValueOnce(dryRunResult)
    fireEvent.click(screen.getByRole("button", { name: t.result.recheck }))
    await waitFor(() =>
      expect(vi.mocked(api.importBackup)).toHaveBeenLastCalledWith(
        expect.any(File),
        { mode: "create_only", dryRun: true },
        "jwt",
      ),
    )
    await waitFor(() => expect(screen.queryByRole("status")).toBeNull())
  })

  it("sends confirm=REPLACE for a non-dry-run replace import", async () => {
    vi.mocked(api.importBackup)
      .mockResolvedValueOnce(replaceDryRunResult)
      .mockResolvedValueOnce({ ...replaceDryRunResult, dry_run: false })
    const { container } = renderPanel()

    await userEvent.click(
      screen.getByRole("radio", { name: t.import.modeReplace }),
    )
    await userEvent.upload(fileInput(container), backupFile())
    await screen.findByText(t.replace.warning.replace("{count}", "7"))
    await userEvent.type(screen.getByPlaceholderText("REPLACE"), "REPLACE")
    await userEvent.click(screen.getByRole("button", { name: t.import.confirm }))

    await waitFor(() =>
      expect(vi.mocked(api.importBackup)).toHaveBeenLastCalledWith(
        expect.any(File),
        { mode: "replace", dryRun: false, confirm: "REPLACE" },
        "jwt",
      ),
    )
    const report = await screen.findByRole("status")
    expect(report).toHaveTextContent(
      t.result.ok.replace("{created}", "3").replace("{deleted}", "7"),
    )
  })

  it("reports a partial import with row errors in orange", async () => {
    vi.mocked(api.importBackup)
      .mockResolvedValueOnce(dryRunResult)
      .mockResolvedValueOnce({
        ...appliedResult,
        status: "partial" as const,
        errors: [
          { entity: "items", index: 4, name: "壞", message: "名稱為必填" },
        ],
        errors_total: 1,
      })
    const { container } = renderPanel()

    await userEvent.upload(fileInput(container), backupFile())
    await screen.findByText(t.summary.title)
    await userEvent.click(screen.getByRole("button", { name: t.import.confirm }))

    const report = await screen.findByRole("status")
    expect(report).toHaveTextContent(
      t.result.partial
        .replace("{created}", "3")
        .replace("{deleted}", "0")
        .replace("{errors}", "1"),
    )
    expect(report).toHaveTextContent("名稱為必填")
  })

  it("reports an error import as unchanged and skips invalidate", async () => {
    vi.mocked(api.importBackup)
      .mockResolvedValueOnce(dryRunResult)
      .mockResolvedValueOnce({
        ...appliedResult,
        status: "error" as const,
        errors: [
          { entity: "items", index: 0, name: "壞", message: "名稱為必填" },
        ],
        errors_total: 1,
      })
    const { container, queryClient } = renderPanel()
    const invalidate = vi.spyOn(queryClient, "invalidateQueries")

    await userEvent.upload(fileInput(container), backupFile())
    await screen.findByText(t.summary.title)
    await userEvent.click(screen.getByRole("button", { name: t.import.confirm }))

    const report = await screen.findByRole("status")
    expect(report).toHaveTextContent(t.result.error)
    expect(invalidate).not.toHaveBeenCalled()
    // 失敗態不提供「重新比對」以外的重新執行（狀態為 error 時無此按鈕）
    expect(screen.queryByRole("button", { name: t.result.recheck })).toBeNull()
  })

  it("toasts and shows a retryable inline error when the import request fails", async () => {
    vi.mocked(api.importBackup)
      .mockResolvedValueOnce(dryRunResult)
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce(appliedResult)
    const { container } = renderPanel()

    await userEvent.upload(fileInput(container), backupFile())
    await screen.findByText(t.summary.title)
    await userEvent.click(screen.getByRole("button", { name: t.import.confirm }))

    await waitFor(() =>
      expect(vi.mocked(toast.error)).toHaveBeenCalledWith(t.import.importFailed),
    )
    expect(screen.getByRole("alert")).toHaveTextContent(t.import.importFailed)
    expect(screen.queryByRole("status")).toBeNull()

    // 可重試：再按一次即成功
    await userEvent.click(screen.getByRole("button", { name: t.import.confirm }))
    expect(await screen.findByRole("status")).toBeInTheDocument()
  })

  it("clears the previous report when a new file is picked", async () => {
    vi.mocked(api.importBackup)
      .mockResolvedValueOnce(dryRunResult)
      .mockResolvedValueOnce(appliedResult)
      .mockResolvedValueOnce(dryRunResult)
    const { container } = renderPanel()

    await userEvent.upload(fileInput(container), backupFile())
    await screen.findByText(t.summary.title)
    await userEvent.click(screen.getByRole("button", { name: t.import.confirm }))
    expect(await screen.findByRole("status")).toBeInTheDocument()

    const second = new File(["{}"], "backup2.json", { type: "application/json" })
    await userEvent.upload(fileInput(container), second)

    await waitFor(() =>
      expect(vi.mocked(api.importBackup)).toHaveBeenLastCalledWith(
        second,
        { mode: "create_only", dryRun: true },
        "jwt",
      ),
    )
    expect(screen.queryByRole("status")).toBeNull()
    await screen.findByText(t.summary.title)
  })
})

describe("BackupPanel read-only viewer (Phase 30)", () => {
  afterEach(() => {
    useAuthStore.setState({ accessToken: null, user: null })
  })

  it("renders only the export card for viewers", () => {
    useAuthStore.setState({ accessToken: "jwt", user: { id: "viewer-1", is_read_only: true } as never })
    renderPanel()
    expect(screen.getByText(t.export.title)).toBeInTheDocument()
    expect(screen.queryByText(t.import.title)).not.toBeInTheDocument()
  })

  it("renders both cards for writers (zero regression)", () => {
    useAuthStore.setState({ accessToken: "jwt", user: { id: "writer-1", is_read_only: false } as never })
    renderPanel()
    expect(screen.getByText(t.export.title)).toBeInTheDocument()
    expect(screen.getByText(t.import.title)).toBeInTheDocument()
  })
})
