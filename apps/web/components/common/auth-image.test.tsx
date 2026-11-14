import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { StrictMode } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import * as client from "@/lib/api/client"
import { __resetBlobCacheForTests, setBlobCacheMaxSize } from "@/lib/images/blob-cache"

import { AuthImage } from "./auth-image"

const tokenMock = vi.hoisted(() => vi.fn<() => string | null>(() => "jwt"))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => tokenMock(),
}))

const PNG_BYTES = new Uint8Array([0x89, 0x50, 0x4e, 0x47])
const PNG2_BYTES = new Uint8Array([0x89, 0x50, 0x4e, 0x48])

function okResponse(bytes: Uint8Array<ArrayBuffer> = PNG_BYTES): Response {
  return new Response(bytes, { status: 200, headers: { "content-type": "image/png" } })
}

let createObjectURL: ReturnType<typeof vi.fn>
let revokeObjectURL: ReturnType<typeof vi.fn>

beforeEach(() => {
  vi.restoreAllMocks()
  vi.clearAllMocks()
  __resetBlobCacheForTests()
  tokenMock.mockReturnValue("jwt")
  createObjectURL = vi.fn(() => "blob:authed-1")
  revokeObjectURL = vi.fn()
  Object.defineProperty(URL, "createObjectURL", { configurable: true, value: createObjectURL })
  Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: revokeObjectURL })
})

describe("AuthImage", () => {
  it("StrictMode 的雙重 effect 不會多釋放引用：顯示中的圖不會被淘汰 revoke", async () => {
    vi.spyOn(client, "apiFetch").mockResolvedValue(okResponse())

    render(
      <StrictMode>
        <AuthImage imageId="img-1" alt="Draft photo" data-testid="thumb" />
      </StrictMode>,
    )
    expect(await screen.findByTestId("thumb")).toHaveAttribute("src", "blob:authed-1")

    // 上限設為 0 → 所有「無人使用」的項目立即被淘汰；仍在畫面上的不可被 revoke
    setBlobCacheMaxSize(0)
    expect(revokeObjectURL).not.toHaveBeenCalled()
  })

  it("fetches the image with the bearer token and renders an object URL", async () => {
    const fetchSpy = vi.spyOn(client, "apiFetch").mockResolvedValue(okResponse())

    render(<AuthImage imageId="img-1" alt="Draft photo" className="size-20" data-testid="thumb" />)

    const img = await screen.findByTestId("thumb")
    expect(img).toHaveAttribute("src", "blob:authed-1")
    expect(img).toHaveAttribute("alt", "Draft photo")
    expect(img).toHaveClass("size-20")
    expect(fetchSpy).toHaveBeenCalledWith("/images/img-1", { accessToken: "jwt" })
    expect(createObjectURL).toHaveBeenCalledTimes(1)
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

  it("unmount 後保留在快取，再次掛載不重新下載", async () => {
    vi.spyOn(client, "apiFetch").mockResolvedValue(okResponse())

    const { unmount } = render(<AuthImage imageId="img-1" alt="" data-testid="thumb" />)
    await screen.findByTestId("thumb")
    expect(client.apiFetch).toHaveBeenCalledTimes(1)

    unmount()
    expect(revokeObjectURL).not.toHaveBeenCalled()

    render(<AuthImage imageId="img-1" alt="" data-testid="thumb" />)
    await screen.findByTestId("thumb")

    expect(client.apiFetch).toHaveBeenCalledTimes(1)
    expect(createObjectURL).toHaveBeenCalledTimes(1)
  })

  it("兩個實例共用同一個 blob URL，一個卸載後另一個仍可用", async () => {
    vi.spyOn(client, "apiFetch").mockResolvedValue(okResponse())

    const { unmount: unmountA } = render(<AuthImage imageId="img-1" alt="" data-testid="a" />)
    const imgA = await screen.findByTestId("a")
    expect(imgA).toHaveAttribute("src", "blob:authed-1")
    expect(client.apiFetch).toHaveBeenCalledTimes(1)

    const { unmount: unmountB } = render(<AuthImage imageId="img-1" alt="" data-testid="b" />)
    const imgB = await screen.findByTestId("b")
    expect(imgB).toHaveAttribute("src", "blob:authed-1")
    expect(client.apiFetch).toHaveBeenCalledTimes(1)

    unmountA()
    expect(revokeObjectURL).not.toHaveBeenCalled()
    expect(imgB).toHaveAttribute("src", "blob:authed-1")

    unmountB()
  })

  it("refetches when the image id changes", async () => {
    const fetchSpy = vi
      .spyOn(client, "apiFetch")
      .mockResolvedValueOnce(okResponse(PNG_BYTES))
      .mockResolvedValueOnce(okResponse(PNG2_BYTES))
    createObjectURL.mockReturnValueOnce("blob:authed-1").mockReturnValueOnce("blob:authed-2")

    const { rerender } = render(<AuthImage imageId="img-1" alt="" data-testid="thumb" />)
    expect(await screen.findByTestId("thumb")).toHaveAttribute("src", "blob:authed-1")

    rerender(<AuthImage imageId="img-2" alt="" data-testid="thumb" />)

    await waitFor(() => expect(screen.getByTestId("thumb")).toHaveAttribute("src", "blob:authed-2"))
    expect(revokeObjectURL).not.toHaveBeenCalled()
    expect(fetchSpy).toHaveBeenLastCalledWith("/images/img-2", { accessToken: "jwt" })
  })
})


it("圖片解碼失敗時顯示 fallback 並通知呼叫端", async () => {
  vi.spyOn(client, "apiFetch").mockResolvedValue(okResponse())
  const onError = vi.fn()
  render(<AuthImage imageId="broken" alt="plan" fallback={<span>retry image</span>} onError={onError} />)
  fireEvent.error(await screen.findByRole("img", { name: "plan" }))
  expect(screen.getByText("retry image")).toBeInTheDocument()
  expect(screen.queryByRole("img")).not.toBeInTheDocument()
  expect(onError).toHaveBeenCalledOnce()
})
