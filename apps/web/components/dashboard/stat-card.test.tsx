import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { StatCard } from "./stat-card"

describe("StatCard", () => {
  it("renders label and numeric value", () => {
    render(<StatCard label="Items" value={42} />)
    expect(screen.getByText("Items")).toBeInTheDocument()
    expect(screen.getByText("42")).toBeInTheDocument()
  })

  it("shows skeleton when loading", () => {
    const { container } = render(<StatCard label="Items" loading />)
    expect(container.querySelector(".animate-pulse")).toBeInTheDocument()
  })
})
