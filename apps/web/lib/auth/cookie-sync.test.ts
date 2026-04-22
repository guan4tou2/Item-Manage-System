import { beforeEach, describe, expect, it } from "vitest"

import { writeTokenCookie } from "./cookie-sync"

function readCookie(name: string): string | null {
  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`))
  if (!match) return null
  return decodeURIComponent(match.slice(name.length + 1))
}

function clearAllCookies(): void {
  document.cookie.split("; ").forEach((row) => {
    const [name] = row.split("=")
    if (name) document.cookie = `${name}=; Path=/; Max-Age=0`
  })
}

describe("writeTokenCookie", () => {
  beforeEach(() => clearAllCookies())

  it("writes ims_token=1 when hasToken is true", () => {
    writeTokenCookie(true)
    expect(readCookie("ims_token")).toBe("1")
  })

  it("clears cookie when hasToken is false", () => {
    document.cookie = "ims_token=1; Path=/"
    writeTokenCookie(false)
    expect(readCookie("ims_token")).toBeNull()
  })
})
