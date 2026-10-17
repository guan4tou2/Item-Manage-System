import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { NextIntlClientProvider } from "next-intl"
import { toast } from "sonner"
import { beforeEach, describe, expect, it, vi } from "vitest"

import * as api from "@/lib/api/backup"
import { ApiError } from "@/lib/api/client"
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
  return render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <BackupPanel />
    </NextIntlClientProvider>,
  )
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
