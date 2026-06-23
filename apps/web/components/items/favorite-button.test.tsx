import { render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"
import zhMessages from "@/messages/zh-TW.json"
import { FavoriteButton } from "./favorite-button"

vi.mock("@/lib/hooks/use-favorite", () => ({
  useToggleFavorite: () => ({
    isPending: false,
    mutate: vi.fn(),
  }),
}))

describe("FavoriteButton", () => {
  it("uses clear English labels for the favorite state", () => {
    render(
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <FavoriteButton itemId="item-1" isFavorite={false} />
        <FavoriteButton itemId="item-2" isFavorite />
      </NextIntlClientProvider>,
    )

    expect(screen.getByRole("button", { name: "Add to favorites" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Remove from favorites" })).toBeInTheDocument()
  })

  it("uses Traditional Chinese labels", () => {
    render(
      <NextIntlClientProvider locale="zh-TW" messages={zhMessages}>
        <FavoriteButton itemId="item-1" isFavorite={false} />
        <FavoriteButton itemId="item-2" isFavorite />
      </NextIntlClientProvider>,
    )

    expect(screen.getByRole("button", { name: "加入最愛" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "從最愛移除" })).toBeInTheDocument()
  })
})
