import { render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import * as client from "@/lib/api/client"

import { AuthImage } from "./auth-image"

const tokenMock = vi.hoisted(() => vi.fn<() => string | null>(() => "jwt"))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => tokenMock(),
}))

const BLOB = new Blob(["png"], { type: "image/png" })

function okResponse(blob: Blob = BLOB): Response {
  return { ok: true, status: 200, blob: async () => blob } as unknown as Response
}

let createObjectURL: ReturnType<typeof vi.fn>
let revokeObjectURL: ReturnType<typeof vi.fn>

beforeEach(() => {
  vi.restoreAllMocks()
  vi.clearAllMocks()
  tokenMock.mockReturnValue("jwt")
  createObjectURL = vi.fn(() => "blob:authed-1")
  revokeObjectURL = vi.fn()
  Object.defineProperty(URL, "createObjectURL", { configurable: true, value: createObjectURL })
  Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: revokeObjectURL })
})

describe("AuthImage", () => {
  it("fetches the image with the bearer token and renders an object URL", async () => {
    const fetchSpy = vi.spyOn(client, "apiFetch").mockResolvedValue(okResponse())

    render(<AuthImage imageId="img-1" alt="Draft photo" className="size-20" data-testid="thumb" />)

    const img = await screen.findByTestId("thumb")
    expect(img).toHaveAttribute("src", "blob:authed-1")
    expect(img).toHaveAttribute("alt", "Draft photo")
    expect(img).toHaveClass("size-20")
    expect(fetchSpy).toHaveBeenCalledWith("/images/img-1", { accessToken: "jwt" })
    expect(createObjectURL).toHaveBeenCalledWith(BLOB)
  })

  it("shows the fallback when the image cannot be fetched", async () => {
    vi.spyOn(client, "apiFetch").mockRejectedValue(new client.ApiError(404, null))

    render(
      <AuthImage
        imageId="img-1"
        alt="Draft photo"
        fallback={<span>photo unavailable</span>}
      />,
    )

    expect(await screen.findByText("photo unavailable")).toBeInTheDocument()
    expect(screen.queryByTestId("thumb")).not.toBeInTheDocument()
    expect(screen.queryByRole("img")).not.toBeInTheDocument()
  })

  it("shows the placeholder while loading", () => {
    vi.spyOn(client, "apiFetch").mockImplementation(() => new Promise(() => {}))

    render(
      <AuthImage
        imageId="img-1"
        alt=""
        placeholder={<span>loading photo</span>}
        fallback={<span>photo unavailable</span>}
      />,
    )

    expect(screen.getByText("loading photo")).toBeInTheDocument()
    expect(screen.queryByText("photo unavailable")).not.toBeInTheDocument()
  })

  it("does not fetch when there is no token and shows the fallback", () => {
    tokenMock.mockReturnValue(null)
    const fetchSpy = vi.spyOn(client, "apiFetch").mockResolvedValue(okResponse())

    render(<AuthImage imageId="img-1" alt="" fallback={<span>photo unavailable</span>} />)

    expect(screen.getByText("photo unavailable")).toBeInTheDocument()
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it("revokes the object URL on unmount", async () => {
    vi.spyOn(client, "apiFetch").mockResolvedValue(okResponse())

    const { unmount } = render(<AuthImage imageId="img-1" alt="" data-testid="thumb" />)
    await screen.findByTestId("thumb")

    unmount()

    expect(revokeObjectURL).toHaveBeenCalledWith("blob:authed-1")
  })

  it("refetches when the image id changes", async () => {
    const fetchSpy = vi
      .spyOn(client, "apiFetch")
      .mockResolvedValueOnce(okResponse())
      .mockResolvedValueOnce(okResponse(new Blob(["png2"], { type: "image/png" })))
    createObjectURL.mockReturnValueOnce("blob:authed-1").mockReturnValueOnce("blob:authed-2")

    const { rerender } = render(<AuthImage imageId="img-1" alt="" data-testid="thumb" />)
    expect(await screen.findByTestId("thumb")).toHaveAttribute("src", "blob:authed-1")

    rerender(<AuthImage imageId="img-2" alt="" data-testid="thumb" />)

    await waitFor(() => expect(screen.getByTestId("thumb")).toHaveAttribute("src", "blob:authed-2"))
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:authed-1")
    expect(fetchSpy).toHaveBeenLastCalledWith("/images/img-2", { accessToken: "jwt" })
  })
})
