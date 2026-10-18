import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { NextIntlClientProvider } from "next-intl"
import { beforeAll, describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"

import { AddMemberDialog } from "./add-member-dialog"

const addMutate = vi.hoisted(() => vi.fn())

vi.mock("@/lib/hooks/use-groups", () => ({
  useAddGroupMember: () => ({ mutateAsync: addMutate, isPending: false }),
}))

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn()
  Element.prototype.hasPointerCapture = vi.fn()
  Element.prototype.setPointerCapture = vi.fn()
  Element.prototype.releasePointerCapture = vi.fn()
})

function renderDialog() {
  return render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <AddMemberDialog groupId="g1" />
    </NextIntlClientProvider>,
  )
}

describe("AddMemberDialog roles (Phase 30)", () => {
  it("adds a member with the default editor role", async () => {
    addMutate.mockResolvedValue({})
    const user = userEvent.setup()
    renderDialog()

    await user.click(screen.getByRole("button", { name: "Add member" }))
    await user.type(screen.getByRole("textbox"), "bob")
    await user.click(screen.getByRole("button", { name: "Create" }))

    expect(addMutate).toHaveBeenCalledWith({ username: "bob", role: "editor" })
  })

  it("sends the selected role", async () => {
    addMutate.mockResolvedValue({})
    const user = userEvent.setup()
    renderDialog()

    await user.click(screen.getByRole("button", { name: "Add member" }))
    await user.type(screen.getByRole("textbox"), "carol")
    await user.click(screen.getByRole("combobox", { name: "Role" }))
    await user.click(await screen.findByRole("option", { name: "Admin" }))
    await user.click(screen.getByRole("button", { name: "Create" }))

    expect(addMutate).toHaveBeenCalledWith({ username: "carol", role: "admin" })
  })
})
