import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { toast } from "sonner"
import { beforeEach, describe, expect, it, vi } from "vitest"

import * as api from "@/lib/api/backup"
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
