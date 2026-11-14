// @vitest-environment node
import { readFileSync } from "node:fs"
import { runInNewContext } from "node:vm"
import { expect, it } from "vitest"
import ts from "typescript"

const source = readFileSync(new URL("./engine.ts", import.meta.url), "utf8")
const artifact = readFileSync(new URL("../../public/offline-engine.js", import.meta.url), "utf8")
it("generated engine is in sync with the TypeScript source", () => {
  const output = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText
  expect(artifact).toBe(`// 自動產生，勿手改。Run: node scripts/build-offline-engine.mjs\n(function () {\nvar exports = {};\n${output}\nself.imsOfflineEngine = exports;\n})();\n`)
  expect(source).not.toMatch(/^import\s/m)
})
it("classic worker artifact exposes functioning exports on a fake self", async () => {
  const self = {} as { imsOfflineEngine: typeof import("./engine") }
  runInNewContext(artifact, { self })
  const engine = self.imsOfflineEngine
  expect(typeof engine.executeItem).toBe("function")
  expect(typeof engine.applyResult).toBe("function")
  expect(engine.failureCode({ status: 403, body: null })).toBe("403")
  const row = { status: "pending" as const, attempts: 0, error_code: null, steps: [{ method: "POST" as const, path: "/items" }] }
  const outcome = await engine.executeItem(row, async () => ({ status: 201, body: { id: "created" } }))
  expect(outcome).toEqual({ type: "success", item_id: "created" })
  expect(engine.applyResult(row, outcome)).toBeNull()
})
