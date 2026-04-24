import fs from "node:fs"
import path from "node:path"
import { describe, expect, it } from "vitest"

const swPath = path.resolve(__dirname, "..", "..", "public", "sw.js")
const swSource = fs.readFileSync(swPath, "utf8")

describe("public/sw.js", () => {
  it("declares a current cache name", () => {
    expect(swSource).toMatch(/const\s+CACHE\s*=\s*["']ims-v\d+["']/)
  })

  it("precaches the /offline fallback on install", () => {
    expect(swSource).toContain("/offline")
  })

  it("does NOT call skipWaiting unconditionally at install-time (update prompt)", () => {
    // Find the install handler block and assert skipWaiting is not inside it.
    // We still allow skipWaiting inside the SKIP_WAITING message handler.
    const installHandler = swSource.match(
      /addEventListener\(\s*["']install["'][\s\S]*?\}\)/,
    )
    expect(installHandler).not.toBeNull()
    expect(installHandler![0]).not.toMatch(/skipWaiting\(\)/)
  })

  it("handles a SKIP_WAITING postMessage from the page", () => {
    expect(swSource).toMatch(/["']SKIP_WAITING["']/)
    expect(swSource).toMatch(/addEventListener\(\s*["']message["']/)
  })

  it("excludes /scan from navigate caching", () => {
    expect(swSource).toContain('"/scan"')
  })
})
