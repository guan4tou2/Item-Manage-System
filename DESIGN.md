# DESIGN.md — Item-Manage-System 設計系統

> **定位**：本文件是設計的**唯一權威**（source of truth）。價值觀摘要：`.impeccable.md`；互動規格契約：`docs/plans/2026-10-15-next-iteration-roadmap.md` §五（本文件只索引、不重複）。實作落點：`apps/web/app/globals.css`、`apps/web/tailwind.config.ts`。
> **建立**：2026-10-15（`/design-consultation`，使用者逐項確認 D1–D5）｜**方向**：Quiet Instrument（安靜的儀表）｜**preview**：`~/.slate/designs/ims-quiet-instrument.html`

## 1. 產品脈絡

- 自架家庭物品管理（Next.js 16 + FastAPI；Docker；PWA）。
- 使用者：家庭成員（含 viewer 長輩）＋小型工作室；主要情境＝廚房裡用手機。
- 語言 zh-TW／en；light／dark。
- **記憶點（北極星）：「快」**——掃了就進去、家人一學就會、零摩擦輸入。
- 3 秒讀感：一眼看到今天有沒有事要處理；沒有就安心，有就直接行動。

## 2. 美學方向：Quiet Instrument

Notion／Linear 血統、資料優先、零裝飾；情緒「篤定」。把「快」具體化成兩個簽名：

1. **掃描儀式**（§6）——0.4 秒內完成的回饋編排（起→落→回）。
2. **語意色紀律**（§3）——飽和色只給狀態，橙／紅 3 公尺外可見。

## 3. 色彩

### 3.1 核心 tokens（維持現況）

| Token | Light | Dark | 用途 |
|---|---|---|---|
| `--background` | `0 0% 100%` | `222 47% 6%` | 頁面底 |
| `--foreground` | `222 47% 11%` | `210 20% 98%` | 主文字 |
| `--card` | `0 0% 100%` | `222 47% 8%` | 卡片面 |
| `--muted` / `--muted-foreground` | `210 40% 96%` / `215 16% 47%` | `217 33% 17%` / `215 20% 65%` | 次要底與文字 |
| `--border` / `--input` | `214 32% 91%` | `217 33% 17%` | 邊框 |
| `--primary` | `221 83% 53%` | `217 91% 60%` | 主動作、連結、focus ring |
| `--destructive` | `0 84% 60%` | `0 72% 51%` | 已過期、破壞性操作 |

### 3.2 狀態語意（Phase 22 建立）

- `--warning`（7 天內到期，`0 ≤ days_left ≤ 7` 含當天）：light `32 95% 44%`／dark `38 92% 60%`
- `--success`（健康・一切安好）：light `142 71% 35%`／dark `142 69% 58%`
- 已過期沿用 `--destructive`；`days_left > 7` 中性、無 badge
- 語意一律「顏色＋文字」；badge／卡片／email／報表引用同一組 token（roadmap §5.6）

### 3.3 徽章：實心貼紙（決策）

到期徽章採**實心色塊**（便利商店即期貼紙隱喻），非淡底。色階已含 4.5:1（roadmap §5.7 要求）：

| 徽章 | Light（bg／fg） | Dark（bg／fg） | 對比 |
|---|---|---|---|
| 已過期 | `0 72% 45%`／白 | 同左＋1px 白 ring 14% | 5.8:1 |
| 7 天內 | `32 95% 44%`／`28 100% 10%` | `38 92% 60%`／`30 100% 8%` | 4.7:1／7.4:1 |
| 一切安好 | `142 71% 29%`／白 | 同左 | 5.1:1 |

- 大面積（行動卡、摘要條）用 token 淡底（7–14% alpha）；文字與徽章一律實心或深字階。
- Phase 22 加入 `globals.css`：

```css
:root {
  --warning: 32 95% 44%;
  --success: 142 71% 35%;
  --badge-expired: 0 72% 45%;
  --badge-expired-foreground: 0 0% 100%;
  --badge-expiring: 32 95% 44%;
  --badge-expiring-foreground: 28 100% 10%;
  --badge-ok: 142 71% 29%;
  --badge-ok-foreground: 0 0% 100%;
}
.dark {
  --warning: 38 92% 60%;
  --success: 142 69% 58%;
  --badge-expiring: 38 92% 60%;
  --badge-expiring-foreground: 30 100% 8%;
}
```

（tailwind config 對應色票於 Phase 22 加入；dark 徽章另加 ring 分離。）

### 3.4 色彩紀律

- **飽和色只給狀態**；其餘一律 slate 中性；一般統計用 muted。
- primary 藍只給：主動作、連結、focus ring。
- 禁用：裝飾性彩色、漸層、發光。
- 圖表 palette（提案；Phase 27 統計頁、31 報表定案）：`--chart-1..5` = 藍 `221 83% 53%`／青 `175 77% 32%`／紫 `262 83% 58%`／琥珀 `32 95% 44%`／巖灰 `215 16% 47%`（dark 對應提亮；圖例與非色彩編碼為義務）。

## 4. 字型

- **現況維持**：Inter（`next/font/google`，`--font-sans`）＋ tailwind CJK fallback 堆疊已就緒：`var(--font-sans), ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, PingFang TC, Microsoft JhengHei, Noto Sans TC, sans-serif`。
- **不載入新 webfont（含 CJK）**：首屏速度＝「快」的一部分。Inter 雖屬常見選擇，對既存成熟系統零遷移、拉丁最優——正式保留（與外部聲音「換字型」建議相反，理由是遷移成本與負收益）。
- 規則：
  - 數字（數量、天數、金額、日期）一律 `tabular-nums`；
  - 技術識別（條碼、UUID、token）用 `font-mono`（ui-monospace 系統堆疊）；
  - 標題 600；內文 400／500；資料介面內文預設 `text-sm`。

| 角色 | 規格 |
|---|---|
| 頁面標題 | `text-2xl`／600 |
| 卡片標題 | `text-sm`／600 |
| 內文 | `text-sm`／400 |
| 徽章 | `text-xs`／600 |
| 大數字（行動卡） | `text-2xl`／700＋tabular-nums |

## 5. 間距・圓角・層級

- 4px base（Tailwind 現況）；卡片內 16、區塊間 24、行動頁邊 16、桌面頁邊 24–32。
- 觸控目標 ≥ 44×44px（roadmap §5.7）。
- 圓角：`--radius: 0.5rem`（lg 8／md 6／sm 4）；徽章與頭像用 pill。新寫的 4px 圓角用 `rounded-sm`；既有的 `rounded-[0.25rem]` 是 Tailwind 4 遷移時為了維持 v3 裸 `rounded` 的數值而保留的寫法。
- Tailwind CSS 4（2026-11-14 起）：`globals.css` 以 `@import 'tailwindcss'`＋`@config '../tailwind.config.ts'` 載入，token 落點不變。`globals.css` 內有一段 v3 相容層（預設邊框色、預設 ring 色、按鈕游標、placeholder 色、`container`、`space-*`／`divide-y`、`hover`），刪改前先確認視覺不變。v4 改名的類別：`shadow-sm`→`shadow-xs`、`backdrop-blur`→`backdrop-blur-sm`、`outline-none`→`outline-hidden`、`flex-shrink-*`→`shrink-*`、CSS 變數用小括號（`max-h-(--var)`）。
- 層級：**邊框優先、陰影克制**；shadow 僅用於 popover／dialog／dropdown／FAB。

## 6. 動態

- 原則：功能性、100–200ms、ease-out；不慶祝、不裝飾。
- 「快」的體感主要來自**樂觀更新**（roadmap §5.5），不是動畫。
- **掃描儀式（簽名，Phase 25）**：
  1. **起** — 取景框掃線來回（僅掃描中）。
  2. **落** — 命中 <100ms 停止掃線＋支援裝置震動 30ms；新物品列 scale 0.96→1 淡入 180ms（「啪」）。
  3. **回** — 自動回首頁，primary 8% 閃示該列 2s。
  4. `prefers-reduced-motion` → 全部退化為即時狀態切換＋高亮；無震動。
- 現況 keyframes 僅 accordion；不新增動畫庫。

## 7. 元件與互動契約索引（roadmap §五）

| 契約 | 內容一句 | 落地 |
|---|---|---|
| §5.1 | 儀表板行動卡群組（已過期 ＞ 7 天內 ＞ 低庫存；數字＋下一步＋註記） | Phase 22 建立 |
| §5.2 | 設定頁子路由＋索引（個人／通知與提醒／整合與資料／管理） | Phase 23 第一步 |
| §5.3 | `/reports` 併入「分析」群組；行動 drawer 二層展開 | Phase 31 |
| §5.4 | 互動狀態表（LOADING／EMPTY／ERROR／SUCCESS／PARTIAL）＋行動清單收據行 | 各 phase 展開時填表 |
| §5.5 | 到期閉環（行動卡 → 到期模式 → 行內 −1 → 樂觀 → 清零回饋）；viewer 旅程 | Phase 22／30 |
| §5.6 | 狀態色彩、N＝7、✦ AiMark「由 AI 產生，可編輯」 | Phase 22／32 |
| §5.7 | FAB＝掃描；樹雙模式；WCAG AA；44px | Phase 25／26／30 |

## 8. 無障礙基準

- WCAG AA：文字 4.5:1（本文件徽章值已驗：5.8／4.7／5.1）；focus ring＝`--ring`；禁止無替代的 `outline:none`。
- 狀態不得僅以色彩表達（顏色＋文字＋圖示）。
- 非同步結果（toast／樂觀回滾）以 `aria-live="polite"` 播報。
- 鍵盤可達：偏好矩陣、位置樹、批量條、FAB（roadmap §5.7）。

## 9. Do / Don't

**Do**
- 行動卡三元素（數字＋一句下一步＋註記）；deep link 一律落到期模式視圖。
- 徽章實心貼紙＋AA 色階；狀態＝顏色＋文字。
- 數字 tabular-nums 右對齊；識別碼 mono。
- 行動清單收據行（hairline、無卡中卡）；空狀態低調正向。
- ✦ 標 AI；非 AI 來源用文字徽章。

**Don't**
- 裝飾色／漸層／發光／emoji 分類。
- 卡中卡、卡片陰影堆疊。
- 慶祝動畫／音效；掃描以外不做「儀式」。
- 新 webfont（含 CJK）；深紫（已修正為藍）。
- primary 濫用為裝飾（它只給主動作、連結、ring）。

## 10. 決策紀錄

- **2026-10-15 建立**（`/design-consultation`；使用者逐項確認；此為現行系統的正式化，非視覺重設計）：
  1. 方向：Quiet Instrument（安靜的儀表）。
  2. 記憶點「快」；簽名動作＝掃描儀式。
  3. 徽章＝實心貼紙＋AA 色階（§3.3）；淡底只留大面積。
  4. 字型＝保留 Inter＋系統 CJK；明文化 tnum／mono 規則；不載入 webfont。
  5. 行動清單＝收據行密度（行動）；桌面維持卡片。
  6. primary 正典＝藍色；`.impeccable.md` deep purple 為文件錯誤、已修正。
  7. 圖表 palette 5 色提案（Phase 27／31 定案）。
  8. 外部聲音（免費模型）「Receipt-Punk」：採納（掃碼儀式、3m 可見、密度、混排痛點）；否決（換皮、換字型、米黃底）。
  9. preview 產出：`~/.slate/designs/ims-quiet-instrument.html`。
- **變更記錄**
  - v1 — 2026-10-15（建立）。
