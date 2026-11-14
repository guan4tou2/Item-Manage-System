import { defineConfig, globalIgnores } from "eslint/config"
import nextVitals from "eslint-config-next/core-web-vitals"
import nextTs from "eslint-config-next/typescript"

// 與舊 .eslintrc.json 等價：next/core-web-vitals + next/typescript，
// 外加 no-unused-vars 的 `^_` 前綴例外。
export default defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    rules: {
      "@typescript-eslint/no-unused-vars": [
        "warn",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
          caughtErrorsIgnorePattern: "^_",
        },
      ],
      // eslint-plugin-react-hooks 7 新增的 React Compiler 系列規則：
      // 專案未啟用 React Compiler，且命中處皆為刻意的「掛載後同步外部狀態」
      // （matchMedia、URL 查詢字串、選取項校正等），改寫會改變行為，故關閉。
      "react-hooks/set-state-in-effect": "off",
      // react-hook-form 的 watch() 與 Compiler 不相容的提示，僅對 Compiler 有意義。
      "react-hooks/incompatible-library": "off",
    },
  },
  // 建置產物、相依套件、自動產生檔與測試輸出不納入 lint。
  globalIgnores([
    ".next/**",
    "node_modules/**",
    "next-env.d.ts",
    "test-results/**",
    "playwright-report/**",
    "coverage/**",
    "public/sw.js",
  ]),
])
