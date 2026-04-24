import fs from "node:fs"
import path from "node:path"
import { describe, expect, it } from "vitest"

const publicDir = path.resolve(__dirname, "..", "..", "public")
const manifestPath = path.join(publicDir, "manifest.webmanifest")
const iconsDir = path.join(publicDir, "icons")
const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8")) as Record<
  string,
  unknown
>

describe("manifest.webmanifest", () => {
  it("declares required PWA identity fields", () => {
    expect(manifest.id).toBe("/dashboard")
    expect(manifest.name).toBeTruthy()
    expect(manifest.short_name).toBeTruthy()
    expect(manifest.start_url).toBe("/dashboard")
    expect(manifest.scope).toBe("/")
    expect(manifest.display).toBe("standalone")
  })

  it("uses valid theme + background hex colors", () => {
    expect(manifest.theme_color).toMatch(/^#[0-9a-fA-F]{6}$/)
    expect(manifest.background_color).toMatch(/^#[0-9a-fA-F]{6}$/)
  })

  it("ships both 192 and 512 icons as PNG", () => {
    const icons = manifest.icons as Array<{ sizes: string; type: string; src: string }>
    expect(icons.length).toBeGreaterThanOrEqual(2)
    const sizes = icons.map((i) => i.sizes)
    expect(sizes).toContain("192x192")
    expect(sizes).toContain("512x512")
    for (const icon of icons) {
      expect(icon.type).toBe("image/png")
    }
  })

  it("every icon src resolves to a real file on disk", () => {
    const icons = manifest.icons as Array<{ src: string }>
    for (const icon of icons) {
      const rel = icon.src.replace(/^\//, "")
      const diskPath = path.join(publicDir, rel)
      expect(fs.existsSync(diskPath), `missing: ${icon.src}`).toBe(true)
    }
  })

  it("declares a maskable icon variant (Android 12+ home screen)", () => {
    const icons = manifest.icons as Array<{ purpose?: string }>
    const hasMaskable = icons.some((i) =>
      (i.purpose ?? "").split(/\s+/).includes("maskable"),
    )
    expect(hasMaskable).toBe(true)
  })

  it("defines shortcut jumps for /scan, /items/new, and /dashboard", () => {
    const shortcuts = manifest.shortcuts as Array<{ url: string }> | undefined
    expect(shortcuts).toBeDefined()
    const urls = (shortcuts ?? []).map((s) => s.url)
    expect(urls).toContain("/scan")
    expect(urls).toContain("/items/new")
    expect(urls).toContain("/dashboard")
  })

  it("includes shipped PNG icon files (valid PNG signature)", () => {
    const icon192 = fs.readFileSync(path.join(iconsDir, "icon-192.png"))
    expect(icon192.slice(0, 8)).toEqual(
      Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    )
  })
})
