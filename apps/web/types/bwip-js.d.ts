/**
 * `bwip-js` 型別宣告（Phase 37）。
 *
 * 套件本身未提供型別；此處只宣告我們實際使用的 `toSVG` 介面。
 * 官方 API 參考：https://www.bwipp-js.com/
 */
declare module "bwip-js" {
  export interface BwipJsOptions {
    /** 條碼種類（我們用 `code128`）。 */
    bcid: string
    /** 編碼內容。 */
    text: string
    /** 放大倍率。 */
    scale?: number
    /** 條碼高度（mm）。 */
    height?: number
    /** 是否輸出條碼下方的文字。 */
    includetext?: boolean
    paddingwidth?: number
    paddingheight?: number
    backgroundcolor?: string
    [key: string]: unknown
  }

  export interface BwipJs {
    toSVG(options: BwipJsOptions): string
  }

  const bwipjs: BwipJs
  export default bwipjs
}
