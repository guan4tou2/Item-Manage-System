import { readFile, writeFile } from "node:fs/promises"
import { fileURLToPath } from "node:url"
import ts from "typescript"

export function compileEngine(source) {
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText
  return `// 自動產生，勿手改。Run: node scripts/build-offline-engine.mjs\n(function () {\nvar exports = {};\n${compiled}\nself.imsOfflineEngine = exports;\n})();\n`
}
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const source = await readFile(new URL("../lib/offline/engine.ts", import.meta.url), "utf8")
  await writeFile(new URL("../public/offline-engine.js", import.meta.url), compileEngine(source))
}
