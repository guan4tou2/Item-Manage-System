# 下一輪開發 Roadmap：Phase 22–34

> **日期**：2026-10-15
> **狀態**：規劃確認 — 功能取捨與關鍵設計決策已與使用者以訪談方式逐項確認
> **定位**：下一輪開發 Roadmap。本文件只決定「做什麼、先後順序、範圍邊界與關鍵設計決策」；每個 phase 進入開發前，依既有慣例展開成 task-level TDD 實作計畫（見文末執行流程）。

---

## 一、現況盤點（2026-10-15）

| 面向 | 現況 |
|------|------|
| 版本 | v2（Next.js 15 + FastAPI 0.115 + PostgreSQL 16 monorepo），Phase 1–21 全部完成，處於維護期 |
| 最近工作 | item workflow improvements（批次操作、模板套用 UX、盤點效率、低庫存補貨）已合併 |
| 測試 | API 454 個測試函式、Web 41 個測試檔（約 160+ 案例）（以靜態掃描計數；執行前需先安裝依賴）；每次推進 main 前雙套全綠為慣例 |
| 遷移進度 | Alembic 至 `0015`（webhook retry），下一支從 `0016` 起編號 |
| 通知架構 | `emit()` 建立站內通知後 fan-out 至所有已綁定外部管道（Email/LINE/Telegram/Web Push）；**無 per-type 偏好控制** |
| 排程架構 | **無作用中的排程器**。`apscheduler` 依賴為 v1 遺留、目前未使用（Phase 24 展開時移除）；既有延遲任務模式 = 外部 cron 呼叫端點（Phase 21 `POST /api/webhooks/process-retries`） |
| 位置結構 | `locations` 為平面三欄（floor / room / zone），無巢狀 |
| 物品欄位缺口 | **無到期日、無條碼、無成本** 欄位 |
| 備份 | 只有 `GET /api/backup/export`，**無匯入還原** |
| Webhook | 後端（含重試）已於 Phase 21 完成，**前端 delivery 管理 UI 缺** |

### v1 有、v2 尚未移植
- 到期標註與儀表板到期卡片（v1 `item_service` expiry annotations）

---

## 二、本次決策紀錄（訪談確認）

### 規劃定位
- 下一輪開發 Roadmap（功能導向，非視覺重設計）

### 使用情境
- **家庭為底、協作為輔**：自己與家人使用為主軸，保留多人協作能力

### 優先方向（六項全選）
輸入與查找效率 ／ 提醒與自動化 ／ 行動與離線體驗 ／ AI 應用深化 ／ 協作與通知 ／ 資料治理與報表

### 功能取捨

| 項目 | 決策 | 粒度／備註 |
|------|------|-----------|
| 保存期限 | ✅ 納入 | **多批次到期管理**（同一物品多批、各帶到期日） |
| 條碼／ISBN 掃描 | ✅ 納入 | **內查＋外查兼具**：先查系統內，查無再查外部資料庫 |
| 多層位置樹 | ✅ 納入 | 現有 floor/room/zone 資料**砍掉重建**（不保證保真） |
| Webhook 管理 UI | ✅ 納入 | delivery 歷史、篩選、手動重試 |
| AI 深化 | ✅ 五項全納入 | 批次照片入庫、收據辨識、自然語言搜尋、智慧分類建議、物品問答 |
| 備份還原 | ✅ 納入 | export 已有，補 import（dry-run + 衝突策略） |
| 成本／庫存估值 | ✅ 納入 | 單價欄位 + 統計頁估值 |
| 定期報表 | ✅ 納入 | 月報為主 |
| 通知偏好中心 | ✅ 納入 | per-type × per-channel 開關 |
| 成員權限細化 | ✅ 納入 | 新增唯讀/查詢者角色 |
| 稽核查詢 UI | ❌ 未納入 | 保留候選 |
| Background Sync 離線新增 | ❌ 本次排除 | 明確不排入本輪；`行動與離線體驗` 方向以掃碼/快速輸入等輕量優化體現 |

---

## 三、排序邏輯

1. **家庭高頻價值先行**：到期管理是家庭場景（食品、藥品、化妝品）最高頻需求，且是 v1→v2 明確缺口 → 排最前。
2. **通知成長前先建控制**：到期提醒會讓通知類型與量體增加，通知偏好中心必須先於到期提醒上線（或至少同時），避免轟炸。
3. **結構性變更早做**：位置樹是破壞性 schema 變更，越晚做、要搬的功能越多 → 排在功能擴張前期。
4. **獨立小項穿插補位**：估值、Webhook UI 彼此獨立、工程量小，可穿插在大型 phase 之間保持推進節奏。
5. **AI 深化工程最大、依賴最少**：放後段，且收據辨識依賴成本欄位（Phase 27）、批次入庫與收據共用草稿審核 UI（Phase 32 → 33）。
6. **依賴鏈**：排程基建（24）→ 定期報表（31）；成本（27）→ 報表估值（31）、收據（33）。

```
Phase 依賴圖（依 §四 總表）：
  22 ─┐
      ├──▶ 24 ──┐
  23 ─┘         ├──▶ 31
  27 ──────────┘

  25 ┄(barcode 選配)┄▶ 32 ──▶ 33 ◀── 27

  無依賴：26、28、29、30、34
```

---

## 四、里程碑與 Phase 總表

### M1 — 家庭價值：到期與提醒（Phase 22–24）
> 讓「什麼快過期」成為系統的一等公民，並在通知量體成長前建立控制。

### M2 — 效率與結構：輸入與位置（Phase 25–26）
> 條碼打通「實體 → 系統」的輸入動線；位置樹打通「東西放在哪」的表達力。

### M3 — 治理與協作（Phase 27–31）
> 估值、Webhook UI、災難還原、權限、報表 — 讓資料「有價、可管、可回復」。

### M4 — AI 深化（Phase 32–34）
> 從單張照片 suggest 進化到批次入庫、收據解析與自然語言介面。

| Phase | 主題 | 里程碑 | 規模 | 主要產出 | 依賴 |
|-------|------|--------|------|----------|------|
| 22 | 批次到期管理 | M1 | M | `item_batches` 表、批次 CRUD/消耗/進貨 API、物品頁批次區塊、儀表板到期卡片 | — |
| 23 | 通知偏好中心 | M1 | S–M | 設定頁 IA 重構（前置）、`notification_preferences` 表、偏好矩陣 API + 設定頁 | — |
| 24 | 排程自動化＋到期提醒 | M1 | M | 冪等 job 端點機制、到期掃描 job、每日摘要通知 | 22, 23 |
| 25 | 條碼掃描（內查＋外查） | M2 | M | `items.barcode`、`barcode_lookups` 快取、掃描模式擴充、外部 provider、表單 prefill | — |
| 26 | 多層位置樹重建 | M2 | **L** | `locations` 樹化 schema、管理 UI、樹狀選擇器、遷移 | —（見風險） |
| 27 | 成本與庫存估值 | M3 | S | `items.cost`、幣別設定、估值統計 | — |
| 28 | Webhook 管理 UI | M3 | S | deliveries 列表/篩選/手動重試 UI | — |
| 29 | 備份還原 | M3 | M | `POST /api/backup/import`（dry-run、衝突策略）、匯入 UI | — |
| 30 | 成員權限細化 | M3 | S–M | viewer 角色、權限矩陣、群組角色 UI | — |
| 31 | 定期報表 | M3 | M | 月報 job、`reports` 表、`/reports` 頁（分析群組）、Email 交付、drawer 二層分組 | 24, 27 |
| 32 | AI 批次入庫＋智慧分類建議 | M4 | M–L | 多圖批次 suggest、草稿審核佇列、歷史規則建議 | 25（barcode 選配） |
| 33 | AI 收據辨識 | M4 | M | 收據結構化抽取、共用草稿 UI | 32, 27 |
| 34 | AI 自然語言搜尋＋物品問答 | M4 | L | NL→filters 轉譯、檢索問答、fallback | — |

> 規模僅為相對參考（S ≈ 1–3 天、M ≈ 一週上下、L ≈ 兩週以上，含測試與 i18n）。實際以此 repo 的 TDD 節奏展開。

---

## 五、UI/UX 設計契約（跨階段）

> 2026-10-15 設計審查（`/plan-design-review`）產出。本節條目為所有 phase 的 UI 實作契約；各 phase 展開 task-level 計畫時，直接將對應條目帶入驗收。

### 5.1 儀表板資訊階層契約（Phase 22 建立，24／27 遵循）

- **第一眼＝行動**：儀表板第一列固定為「行動卡群組」，排序 `已過期 ＞ 7 天內到期 ＞ 低庫存`；每張卡強制三元素：**數字** ＋ **一句下一步（deep link 至對應篩選視圖）** ＋ **狀態註記**
- 估值、統計、圖表一律排在行動卡群組之後；Phase 27 的估值卡不得插在行動卡之前
- Phase 24 的「今天已彙總提醒」註記屬既有卡片擴充，不改變排序
- 到期資訊在「無任何到期物」時的空狀態樣式見 §5.4 狀態契約

### 5.2 設定頁資訊架構（Phase 23 第一步執行）

設定頁由單排 tabs 重構為 **子路由 ＋ 設定首頁索引**：

- `/settings` 索引頁：四群組卡片，每組列出所屬頁面
- 子路由如 `/settings/notifications`：穩定深連結，供 Phase 24 提醒與 Phase 31 報表直接引用
- 分組映射：

| 群組 | 頁面 |
|------|------|
| 個人 | 個人資料、密碼、偏好（Phase 27 幣別設定在此；Phase 34 AI 傳送開關在此） |
| 通知與提醒 | 通知管道、通知偏好（Phase 23）、提醒排程（Phase 24，唯讀）、報表開關（Phase 31） |
| 整合與資料 | Webhooks（Phase 28）、API 權杖、CSV 匯入/匯出、備份（Phase 29）、自訂欄位與模板、分類／位置／標籤（既有 `/settings/taxonomy` 子頁） |
| 管理 | 成員管理、稽核記錄 |

- 硬上限：首層群組 ≤ 4、每群組頁面 ≤ 6；超出即重新分類，不得直接加頁
- Phase 23 第一步 = 完成重構；零回歸範圍＝既有 10 個設定面板＋`/settings/taxonomy` 子頁＋admin-only 面板可見性規則（含 BootstrapAdminButton 首次引導）；再把「通知偏好」放入「通知與提醒」

### 5.3 全站一級導覽契約（Phase 31 落地）

- `/reports` 併入「分析」群組（桌面：統計 dropdown 含報表；行動：drawer 二層展開），首層項目數維持 11
- 行動版 drawer 支援「群組標題 ＋ 二層展開」（新元件，計入 Phase 31 範圍）
- 未來新頁面（如 AI 草稿佇列＝物品新增頁內入口）優先掛「既有群組成員」或「頁內入口」，不新增首層項目；AI 傳送開關置於設定「個人＞偏好」（Phase 34）

### 5.4 互動狀態契約（所有新介面最低要求）

每個新介面在實作計畫中必須填寫本表；空狀態一律附「下一步動作」（`.impeccable.md` 原則）。

| 介面 | LOADING | EMPTY | ERROR | SUCCESS | PARTIAL |
|------|---------|-------|-------|---------|---------|
| 到期行動卡（22/24） | 卡片骨架 ×2 | 淡色低調「一切安好」（標註「無到期物」，不搶第一眼） | 卡內 compact 錯誤＋重試連結（不整頁壞） | 數字＋deep link＋狀態註記 | Phase 24 註記 append，不重排 |
| 批次區塊（22） | 列表 skeleton | 未開啟追蹤 → 引導開啟；已開啟無批次 → 引導建立 | 超額消耗＝行內驗證訊息「剩餘 N，無法消耗 M」（不 toast）；樂觀更新失敗 → 回滾＋toast | 即時剩餘預覽；歸零批次進「已耗盡」折疊（預設收起） | 進貨 sheet 送出中（按鈕 loading） |
| 掃碼（25） | 相機啟動中；外查中「查詢外部資料庫…」（≤3 秒） | 權限被拒 → 全頁空態＋「開啟權限」按鈕＋手動輸入保底；外查查無 → 「查無公開資料，已帶入條碼，請補名稱」 | 逾時/網路錯誤 → 「網路不穩，條碼已保留」＋重試按鈕（與查無區分） | 內查命中 → 單筆直接跳轉；多筆 → 候選列表（縮圖＋位置路徑） | — |
| 通知偏好（23） | 群組卡 skeleton | 未設定過 → 頂部摘要條「目前等同全部開啟」＋三群組卡（物品提醒／借還與協作／系統與報表） | 儲存失敗回滾＋toast；不可關類別顯示鎖頭＋tooltip | 樂觀切換＋「偏好已更新」toast | 未綁定管道 → 該欄禁用＋「前往綁定」引導 |
| 位置樹（26） | 樹 skeleton | 空樹 → 建立第一層引導；搜尋無結果 → 「建立新節點？」 | 刪除 409 → dialog「此位置有 N 件物品」＋「先搬移」按鈕（直接開搬移對話框）；非法拖放即時灰化＋tooltip | 拖放/搬移樂觀更新＋toast | — |
| 備份匯入（29） | 上傳/解析 progress；dry-run「比對中…」 | 空檔或格式錯誤 → 明確訊息 | 驗證失敗 → per-entity 錯誤列舉（前 5 筆） | 結果報告三態：全成功綠／部分成功橙＋失敗清單／全失敗紅 | 部分成功明確計數，不靜默 |
| AI 草稿佇列（32/33） | 逐卡狀態：排隊中／辨識中 shimmer | 無草稿 → 「拍張照片開始」；全部處理完 → 完成態 | 失敗卡＋單卡重試；配額耗盡 → 全局 banner＋pending 保留 | 卡片可編輯 → 接受後移出；進度「N/M 完成」 | 混合狀態共存；批量條：全選／全部接受（附計數二次確認）／全部丟棄 |
| 報表（31） | 生成中骨架 | 首月 → 「第一份月報於次月 1 日生成」期待管理；空資料月 → 站內留痕「本月無動態」（不缺席） | 載入失敗＋重試 | 清單＋詳情 | — |

**補充規格**
- **批次物品列表行（22）**：名稱＋總數＋**最急到期 badge（僅一枚）**；`is_depleted` 批次不得造成幽靈列
- **掃碼手輸 prefill（25）**：查無/逾時導向手動輸入時，表單必須已帶入掃到的條碼數字
- **掃碼幽靈結果（25）**：外查進行中離開掃描頁 → 結果丟棄；重進不殘留半套 prefill
- **備份 dry-run 摘要（29）**：必含 per-entity「現有 → 匯入後」對照（建立 N／名稱衝突加後綴 M／錯誤 K）；`replace` 顯示將刪除總數＋確認字串
- **草稿佇列恢復（32/33）**：離開後再進入 → 直接回到「未完成佇列」（伺服器端草稿為資料來源）

### 5.5 使用者旅程契約

**到期閉環（Phase 22 核心旅程，Phase 24 延伸）**

```
儀表板行動卡 → 到期模式視圖 → 行內 −1 → 樂觀更新 → 清零回饋
```

- **到期模式視圖**：物品列表的專用模式 — 按剩餘天數排序、行內 −1、批次展開；不清零即可一路處理多筆
- 處理後**樂觀更新**（卡片與列表即時反映）；全部清零時行動卡回到「一切安好」（§5.4）完成情緒收尾
- 儀表板卡與通知摘要的 deep link 一律落在到期模式視圖

**viewer 家人旅程（Phase 30）**

- 首次登入一次性說明（banner，可關閉、不重複）：「你是檢視者 — 可以查看所有物品，內容由群組成員維護」
- 編輯入口一律**不渲染**（非禁用）；物品詳情頁底部固定一句「你是檢視者，如需修改請聯絡群組管理員」
- 後端 403 僅作最後防線，不作為主要 UX 手段

### 5.6 設計系統契約

**狀態色彩（Phase 22 建立；`globals.css` ＋ tailwind config）**

| 語義 | Token | 建議值（實作時以 light/dark 對比度測試定案） |
|------|-------|------|
| 已過期 | `--destructive`（既有） | 沿用 |
| 7 天內到期 | `--warning`（新建） | light `32 95% 44%`／dark `38 92% 60%` |
| 健康・一切安好 | `--success`（新建） | light `142 71% 35%`／dark `142 69% 58%` |

- **N＝7**：`days_left < 0` 紅；`0 ≤ days_left ≤ 7` 橙（含當天到期）；`> 7` 中性無 badge
- 色彩不得為唯一訊息載體：badge 一律「顏色＋文字」（「過期 3 天」「5 天內」）
- 到期語義（badge、卡片、email、報表）一律引用同一組 token，不得各自調色

**AI 標記（Phase 32–34；決策：圖示化）**

- 所有 AI/LLM 產出統一加 **✦ 記號**（lucide `sparkles`；`muted-foreground` 小型圖示）＋tooltip／tap 說明「由 AI 產生，可編輯」；共用元件 `AiMark`（Phase 32 建立）
- 標記位置：批次草稿卡、收據品項、NL 搜尋「理解為」chip、問答回答（另附引用連結）
- 非 AI 來源用文字 badge：「依歷史：廚房」（規則式）、「來源：Open Food Facts」（外部 API）
- 禁用：漸層、發光、魔法動畫等裝飾性 AI 陳腔；記號不改變元件既有樣式

**金額與日期格式（Phase 27 建立）**

- 金額：`Intl.NumberFormat(locale, { style: 'currency', currency })`；TWD 於 zh-TW／en 均顯示 `NT$` 前綴（`NT$1,200`）
- 日期：ISO 儲存；顯示用 locale 短格式；報表與排程時區固定 `Asia/Taipei`

### 5.7 響應式與無障礙契約

**行動互動原則**
- **樹搬移**：桌面＝拖放（非法目標即時灰化＋tooltip）；行動＝「⋯ 選單 → 搬移至（搜尋選父）」— 行動版不做觸控拖拽
- **樹狀選擇器**（物品表單/篩選）：桌面＝cascading 展開；行動＝bottom sheet ＋扁平搜尋結果（顯示完整路徑）tap 回填
- **掃描 FAB**（Phase 25）：行動版固定 FAB＝掃描，避開底部導覽與 safe-area；桌面保留既有 toolbar 入口
- 寬表格（偏好矩陣、deliveries、報表）行動版一律卡片化（同 §5.4）

**無障礙基線（WCAG AA）**
- 新互動元件全部鍵盤可達：偏好矩陣 toggle、樹（方向鍵展開/移動、Enter 選擇）、批量條、FAB
- Focus ring 沿用 `--ring`；禁止無替代的 `outline: none`
- Tap target ≥ 44×44px；icon-only 按鈕必有 `aria-label`
- 狀態不得僅以色彩表達（見 §5.6）；非同步結果（toast／樂觀回滾）以 `aria-live="polite"` 播報
- 新 token 與 badge 組合在 light／dark 均需通過 4.5:1 文字對比測試

---

## 六、各 Phase 詳細

### Phase 22 — 批次到期管理

**目標**：物品可開啟「追蹤批次」模式；每批有數量與到期日；支援進貨、消耗（FEFO）；儀表板顯示即將到期／已過期。

**範圍**
- **DB（migration `0016`）**
  - `item_batches`：`id`(UUID)、`item_id`(FK cascade)、`quantity`(int ≥0)、`expiry_date`(date, nullable)、`received_at`(date, nullable)、`note`(nullable)、`created_at`、`updated_at`
  - 批次數量歸零 → 保留列並標記 `is_depleted`（歷史可追溯）；UI 收進「已耗盡」折疊區、預設收起，不得污染主列表（見 §5.4）
  - `items.track_batches`(bool, default false)：開啟後 `items.quantity` 為快取總和，維持既有查詢/統計相容
  - 索引：`item_batches.item_id`、`item_batches.expiry_date`（列表聚合、統計與 job 掃描用）
  - 閱讀路徑：物品列表的批次聚合（總數＋最急到期）與統計/掃描一律走單一聚合查詢＋索引，非 per-item 逐列查詢
- **API**（沿用既有 nested 風格，同 `/api/items/{id}/loans`）
  - `GET /api/items/{id}/batches` — 列表含 derived `days_left`、`status: ok | expiring | expired`
  - `POST /api/items/{id}/batches` — 進貨（建立批次）
  - `PATCH /api/items/{id}/batches/{batch_id}` — 修正數量/到期日/備註
  - `DELETE /api/items/{id}/batches/{batch_id}`
  - `POST /api/items/{id}/batches/{batch_id}/consume` `{quantity}` — 從指定批次消耗
  - `POST /api/items/{id}/consume` `{quantity}` — 便捷：FEFO 自動逐批扣
  - 所有消耗/進貨同步更新 `items.quantity` 並寫 `quantity_logs`（`reason` 含批次資訊）
  - `GET /api/stats/expiry?days=30` — `{ expired_count, expiring_count, items: […] }` 供儀表板卡片
- **Web**
  - 物品詳細頁「批次」區塊：到期日 badge（已過期紅／7 天內橙，見 §5.6）；行內「−1」快捷（樂觀更新、失敗回滾）；「進貨/調整」bottom sheet（數量、到期日、備註）；已耗盡收「歷史」折疊（見 §5.4）
  - 物品表單：庫存模式切換（單一數量 ↔ 追蹤批次）；切換時引導：「建立第一批時，現有數量會併入一筆無到期日批次」
  - 儀表板：到期行動卡依 §5.1 置於行動卡群組（排序：已過期 ＞ 7 天內到期 ＞ 低庫存；卡片含「數字＋下一步 deep link＋狀態註記」）→ 點擊進「到期模式視圖」（見 §5.5）
  - 物品列表：`expiry=expired|expiring_soon` 篩選；批次物品列顯示「總數＋最急到期 badge（僅一枚）」（見 §5.4）
  - 到期模式視圖：列表「到期模式」— 剩餘天數排序、行內 −1、批次展開、清零回饋（§5.5）；儀表板卡與通知摘要 deep link 的落點
- **CSV（stretch）**：匯出加 `expiry_date`（單一批次情境）；完整批次匯入/匯出留待後續

**關鍵設計決策**
1. **對帳 invariant**：`track_batches=true` 時恆等式 `items.quantity == Σ 未耗盡批次 quantity` — 以 service 層單一入口維護
2. **盤點整合**：盤點差額以「調整批次」表達（正差 → 新批次 note=`stocktake:<session>`；負差 → FEFO 消耗），維持 invariant
3. 建立第一批時自動開啟 `track_batches`（降低摩擦），當前數量併入一筆無到期日批次
4. **模式可關閉（併回總量）**：關閉對話框明示「批次將合併為單一數量，到期日資訊將刪除」→ 確認後刪除批次、`items.quantity` 維持；不存在「追蹤關閉但有批次」狀態，invariant 無例外
5. **併發安全**：所有批次寫入（進貨／消耗／盤點調整／模式切換）以 `SELECT … FOR UPDATE` 鎖定 item 列（或原子 UPDATE＋rowcount 檢查），防雙擊／雙視窗並行 consume 造成 lost update
6. **「今天」唯一定義**：`days_left`／`status`／列表篩選／Phase 24 門檻判定一律使用 Asia/Taipei 的「今天」（單一 helper，與 §5.6 排程時區一致）

**數量 invariant 流**

```
進貨／消耗（−1、FEFO）／盤點調整／模式切換
                     │
                     ▼
      批次 service 單一入口（FOR UPDATE 鎖 item 列）
                     ├──▶ item_batches（新增／消耗／調整／耗盡標記）
                     ├──▶ items.quantity = Σ 未耗盡批次（快取總和）
                     └──▶ quantity_logs（reason 含批次資訊）
```

**驗收大綱**
- FEFO 消耗正確性（跨批次、剛好歸零、超額拒絕）
- invariant 測試（批次操作、盤點、CSV 匯入後）
- 列表聚合查詢數不隨列數成長（query count 斷言）
- 到期模式視圖：剩餘天數排序、行內 −1、樂觀更新與清零回饋（§5.5）
- 未開啟追蹤模式的物品行為零回歸
- 併發雙 consume（同 item 並行）→ invariant 仍成立、無 lost update
- 台北午夜邊界：23:59／00:00 前後 `days_left`／篩選結果正確
- i18n 全字串（zh-TW + en）、深色模式

---

### Phase 23 — 通知偏好中心

**目標**：每個通知類型 × 每個管道可獨立開關；為到期提醒（Phase 24）與未來報表（Phase 31）鋪好降噪機制。

**範圍**
- **前置（第一步）**：設定頁 IA 重構 — 子路由 ＋ 索引頁四群組（見 §5.2）；既有 10 個設定頁功能零回歸
- **DB**：`notification_preferences`（`user_id`、`type`、`channel`、`enabled`）— 獨立表（可查詢、可展開預設）
  - 類型枚舉（實作時由現況盤點定案）：`low_stock`、`expiring_soon`、`expired`、`loan_open`、`loan_overdue`、`loan_returned`、`transfer.request`、`transfer.accepted`、`group_invite`、`report_ready`、`system`
  - 管道：`in_app`、`email`、`line`、`telegram`、`web_push`
- **API**：`GET /api/notifications/preferences`（回矩陣＋可用類型/管道清單）、`PUT /api/notifications/preferences`
- **行為**
  - `emit()` 仍寫站內表，但站內是否建立依偏好（可關）；`deliver_all()` 依偏好過濾
  - 不可關類別：群組邀請、帳號安全（後端強制）
  - 預設值：全部開啟（維持現行行為），`expired`/`expiring_soon` 預設站內＋推播、Email 預設關（降噪）
- **Web**：設定頁「通知與提醒」群組新增「通知偏好」頁（依 §5.2 結構）— 矩陣 UI（列=類型、行=管道開關），行動版卡片式（分組與預設態見 §5.4）

**驗收大綱**
- 偏好過濾單元測試（emit / deliver_all 各情境、不可關類別強制）
- API 契約：GET 回傳矩陣結構（類型×管道）、PUT→GET 反映、未知 type／管道拒絕
- UI 測試（切換、儲存、重置）
- 既有通知流程零回歸
- **CRITICAL 回歸（設定 IA 重構）**：10 面板子路由化後逐一面板 smoke（render＋核心操作）、`/settings/taxonomy` 子頁、admin-only 可見性（非 admin 隱藏、BootstrapAdminButton 首次引導）；以既有 customization／webhook／channels 3 個面板測試為基礎擴充；`navigation.spec.ts` 加設定子路由可達性抽查

**備註**：與 Phase 24 可平行；若 24 先上，到期通知會短暫無偏好控制（可接受，因預設低噪音）。

---

### Phase 24 — 排程自動化＋到期提醒

**目標**：建立可重複使用的排程 job 機制（本輪內 Phase 31 報表會重用）；第一個 job = 到期掃描與摘要提醒。

**Job 執行流**

```
外部 cron ─(PAT)─▶ POST /api/jobs/{job_name}/run
                        │
                        ▼
              job registry（expiry-scan；report.monthly）
                        ├──▶ 掃描門檻（Asia/Taipei 今天）
                        ├──▶ expiry_alerts 查／寫（UNIQUE 冪等）
                        ├──▶ 摘要 emit（尊重 Phase 23 偏好）
                        └──▶ job_runs 記錄（設定頁顯示／停跑警示）
```

**範圍**
- **機制（決策：外部 cron ＋ 冪等 job 端點）**
  - 與 Phase 21 `process-retries` 模式一致：**定案通用端點** `POST /api/jobs/{job_name}/run`（job registry 登錄制；Phase 31 `report.monthly` 共用），回 `{ job, processed, emitted }`；未知 `job_name` → 404；**觸發權＝帳號管理員（admin）；非管理員 → 403**（比 `process-retries` 更嚴；cron 文件範例使用管理員 PAT）
  - 認證：登入使用者（PAT）即可，語義同 `process-retries`（只處理已排程工作、不外洩 payload）
  - 文件補 cron 範例：crontab ／ systemd timer ／ GitHub Actions schedule
  - **冪等性**：同日重跑不重複發送（dedupe 記錄 `(batch_id, level, date)`）
  - 不使用 `apscheduler`（依賴閒置中；避免多 worker 生命週期複雜度）；**展開時一併移除 `apscheduler` 依賴（pyproject＋lock）**。未來若有分鐘級需求再另行評估
- **DB**
  - `job_runs`：`job_name`、`status`、`started_at`、`finished_at`、`result`(JSON) — 供設定頁「上次執行時間」與停跑觀測
  - `expiry_alerts`：`batch_id`(FK)、`level`(`d30|d7|d0|expired`)、`sent_on`(date) — UNIQUE(`batch_id`, `level`, `sent_on`)，冪等 dedupe 記錄
- **到期掃描邏輯**
  - 門檻：預設 30 天前、7 天前、當天、過期後（`expired` 每日彙總；**14 天後停止推播、站內保留**）
  - **摘要式**：每用戶每日最多一則彙總（「3 件即將到期、1 件已過期」＋ deep link），非逐批轟炸
  - 尊重 Phase 23 偏好（含 Email/LINE/TG/Push 過濾）
- **失敗語義**：執行中途異常 → `job_runs.status = failed` ＋ error 摘要；**已寫入的 alerts 保留**（部分成功可接受）；重跑依 dedupe 只補未送出的差額、不重複
- **Web**
  - 設定頁「通知與提醒」群組顯示「提醒排程」：目前門檻、上次執行時間（唯讀；門檻可調為 stretch）；**停跑警示：未執行過或超過預期間隔 → 顯示警示文案＋cron 設定文檔連結**
  - 儀表板到期卡片（Phase 22 已建）疊加「今天已彙總提醒」註記（卡片角落 muted 小字＋鈴鐺 icon；不改變排序與尺寸）

**驗收大綱**
- 時間旅行測試（freeze date 驗各門檻觸發）
- 冪等：同日重跑 emit 次數不變
- 偏好過濾（關閉 → 不外送、站內也不建立）
- 無批次物品、無到期批次 → job 正常結束且零輸出
- 停跑警示：`job_runs` 為空或 last_run 過舊 → 設定頁顯示警示態
- 中途失敗 → `job_runs.status` 正確轉 failed；重跑只補未送、不重複
- 端到端整合：進貨（含到期日）→ 掃描 → emit → 管道過濾 → deep link 落點存在
- 權限：非管理員觸發 → 403；未知 `job_name` → 404

**依賴**：Phase 22（資料）、Phase 23（偏好）

---

### Phase 25 — 條碼掃描（內查＋外查）

**目標**：掃 EAN/UPC/ISBN → 系統內快速定位；查無 → 外部資料庫帶入新增表單。

**範圍**
- **DB（migration）**
  - `items.barcode`（varchar nullable；**不設唯一** — 同一條碼可分開建檔多件；搜尋支援）
  - `barcode_lookups` 快取：`code`、`source`、`payload`(JSON)、`fetched_at`（TTL 30 天）
- **掃描前端（`/scan` 擴充）**
  - 模式自動：先 QR、再 1D 條碼；技術方案 — 評估 `@zxing/browser`（跨瀏覽器），原生 `BarcodeDetector` 可用時走快路徑（Safari 無原生支援）
  - 保留既有 QR 流程零回歸
  - **入口**：行動版掃描 FAB（shell 元件，避開底部導覽）；桌面 toolbar 入口保留（見 §5.7）
- **流程 A（內查）**：barcode 命中 → 單筆跳物品頁；多筆 → 候選列表（縮圖＋位置路徑＋總數，見 §5.4）
- **流程 B（外查）**：provider 抽象（`BarcodeProvider`）
  - EAN/UPC → Open Food Facts（食物類）；找不到或非食物 → 「查無公開資料，已帶入條碼，請補名稱」（見 §5.4）
  - ISBN → Open Library（含封面）
  - 逾時 3 秒、fail-soft；逾時/網路錯誤與「查無」採不同空態（「網路不穩，條碼已保留」＋重試，見 §5.4）；結果寫入 `barcode_lookups` 快取
  - 外部結果 → 新增表單 prefill（名稱、描述、分類建議）＋ 顯示來源標註
- **其他**
  - 物品表單：barcode 欄位（可手輸或掃描輸入）；詳細頁 monospace 顯示 + 複製
  - CSV：`barcode` 欄位 import/export
  - 標籤列印：QR 標籤下方加印條碼數字（stretch）

**關鍵設計決策**
- 外部查不到 ≠ 錯誤：一律引導手動輸入（家庭物品多數無公開資料庫條目）
- 快取先查：同條碼第二次掃描不打外部 API

**驗收大綱**
- provider mock 測試（命中/逾時/非 JSON/404）
- 快取命中與 TTL 過期
- 掃描頁 QR 與 1D 並存回歸

---

### Phase 26 — 多層位置樹重建

**目標**：位置改為任意深度樹（樓層 ＞ 房間 ＞ 櫃子 ＞ 抽屜）；現有資料砍掉重建（已確認）。

**範圍**
- **DB（migration）**：`locations` 重構
  - 欄位：`id`、`owner_id`、`parent_id`(self-FK, nullable)、`name`、`kind`（選填：`floor|room|shelf|box|other` 或自由文字）、`sort_order`、`floor_plan_image_id`(保留)
  - 查詢策略：adjacency list ＋ recursive CTE（PG 與 SQLite 測試皆支援）；材料化路徑（materialized path）為後續優化選項
  - **遷移**：舊 floor/room/zone → 一次性長出對應層級節點並重新指向（best-effort）。**保證：每件物品遷移後仍有 location_id（無孤兒）**；不保證路徑保真，但遷移報告列出節點合併數、孤兒節點數與未指派物品數；之後在使用者 UI 整理
  - `items.location_id` FK 維持，指向任意節點
- **warehouse 關係**：warehouse 維持獨立軸、樹不吸收倉庫；Phase 27/31 的 location 維度一律以樹節點為準（warehouse 單獨分組），避免報表分組重複或遺漏
- **API**
  - 既有 locations CRUD 改造（支援 `parent_id`、move、reorder）
  - `GET /api/locations/tree`、`GET /api/locations/{id}/path`
  - 刪除策略：**有物品或有子節點時一律禁止**（409＋引導：「先搬移 N 件物品」／「先處理子節點」按鈕，見 §5.4）；不提供遞移刪除
  - 防止循環：不能把節點移到自己的子孫之下（service 層驗證 + 測試）
- **Web**
  - `/locations` 樹管理頁：展開收合、改名、刪除；搬移＝桌面拖放（非法目標灰化）／行動「⋯ 選單 → 搬移至」（見 §5.7）
  - 物品表單/篩選：樹狀選擇器 — 桌面 cascading、行動 bottom sheet＋扁平搜尋（顯示完整路徑）（見 §5.7）
  - 物品詳情：麵包屑路徑（長路徑截斷「… / 抽屜」）
  - 篩選語義：選父節點**預設含子孫**，提供「僅此層」toggle
- **安全網**：遷移前強制 `GET /api/backup/export` 備份（若 Phase 29 尚未完成）；遷移以 dry-run 腳本先行審查

**驗收大綱**
- 樹操作 API 測試（move、防循環、刪除限制、排序）
- 行動版搬移（選單＋搜尋選父）與桌面拖放各自測試；樹的鍵盤操作（方向鍵/Enter）
- 含子孫查詢（recursive CTE）
- 遷移腳本測試（fixture：舊平面資料 → 樹）
- 物品列表/搜尋/統計在樹下的回歸

**風險**：本輪破壞性最大。若資料敏感，可考慮將 Phase 29（備份還原）插到此 phase 之前。

---

### Phase 27 — 成本與庫存估值

**目標**：物品可記單價；統計頁呈現庫存總值與分布。

**範圍**
- **DB**：`items.cost` `Numeric(12,2)` nullable（單價）；幣別為**帳號層級單一設定**（`users.preferences.currency`，預設 TWD，不做匯率換算）
- **API**：items CRUD 帶 `cost`；`GET /api/stats/value` — 總值、by category/location/warehouse、未填成本比例
- **Web**：表單成本欄位、詳細頁顯示；統計頁估值卡片＋圖表（圖表類型展開時先盤點既有統計頁圖類型再決定，避免新圖表語彙）；儀表板可選卡片（依 §5.1 只能排在行動卡群組之後）；幣別設定置於設定頁「個人 ＞ 偏好」（見 §5.2）
- **CSV**：`cost`、`currency` 欄位
- 批次成本（per-batch cost）為 stretch，後續再議

**驗收大綱**：Decimal 精度、null 成本處理（以 0 計、顯示未填比例）、i18n（金額格式）

**依賴**：無；Phase 31 估值變化、Phase 33 收據帶入成本依賴此。

---

### Phase 28 — Webhook 管理 UI

**目標**：把 Phase 21 已完成的後端能力（delivery 歷史、手動重試）端上前端。

**範圍**
- **API（小補）**：deliveries 分頁/篩選參數（status、event）、統計端點（若缺）
- **Web**：設定頁「整合與資料」群組 Webhooks 頁擴充（見 §5.2）
  - 每個 webhook 展開 deliveries 表：時間、事件、狀態碼、attempt、next_retry_at
  - 狀態篩選（成功／失敗／待重試）、response excerpt 展開
  - 手動「重試」按鈕（呼叫既有 `POST /api/webhooks/{id}/deliveries/{delivery_id}/retry`）
  - 概覽：成功率、最近成功時間

**驗收大綱**：UI 測試（列表、篩選、重試觸發）、空狀態、行動版佈局

---

### Phase 29 — 備份還原

**目標**：從 JSON 備份還原到帳號；災難恢復與「砍掉重建」的安全網。

**範圍**
- **API**：`POST /api/backup/import`（multipart JSON，`dry_run` 參數）
  - 驗證 `format_version`；回 per-entity 計數摘要與錯誤列舉
  - **衝突策略（兩模式）**
    - `create_only`（預設、安全）：所有實體以新 id 建立；名稱衝突自動加後綴；不覆蓋任何現有資料
    - `replace`（高風險）：**單一資料庫交易**清空當前帳號資料並匯入，失敗全數回滾；UI 需輸入確認字串＋匯入前自動提示先匯出備份
  - **不還原**：`audit_logs`、`api_tokens`（安全）；webhooks 還原為**停用**狀態（安全預設，不自動啟用）
  - 關聯重建：category/location/warehouse/tag 以名稱匹配或建立；loans、quantity_logs、`item_batches` 以 id-map 重建；匯入完成後逐 item 對帳 `items.quantity == Σ 未耗盡批次`（不一致列入結果報告）
  - **還原範圍與版本**：可還原實體＝當期 schema 全量（含 22–27、31 各 phase 新增欄位/表：`barcode`/`barcode_lookups`、位置樹、`cost`/幣別、`notification_preferences`、`reports` 等，以實際展開時序盤點登錄）；`format_version` 遞增規則＝新增可選欄位 +1、破壞性變更 +1，並附新舊相容矩陣（舊檔可匯入；新檔於舊版明確拒絕）
- **Web**：設定頁「整合與資料」群組「備份」頁 — 匯出（既有）＋ 匯入（選檔 → dry-run 摘要（per-entity「現有 → 匯入後」對照，見 §5.4）→ 確認 → 結果報告三態）

**驗收大綱**
- round-trip：export → import 到空帳號 → 資料等價
- dry-run 零寫入
- `replace` 模式隔離性（不影響其他帳號）與失敗回滾（匯入中途錯誤 → 原資料完整）
- 還原後 invariant 成立（批次物品對帳）
- 大檔處理（串流或大小上限）

---

### Phase 30 — 成員權限細化

**目標**：新增「唯讀/查詢者」角色，適合家人只查不修改。

**範圍**
- **角色模型**：群組層級 `owner / admin / editor / viewer`（現行 member ≈ editor）
- **權限矩陣（進入開發時定稿，原則如下）**

| 操作 | owner | admin | editor | viewer |
|------|-------|-------|--------|--------|
| 檢視群組物品/統計 | ✅ | ✅ | ✅ | ✅ |
| 物品 CRUD | ✅ | ✅ | ✅ | ❌ |
| 借出/歸還操作 | ✅ | ✅ | ✅ | ❌ |
| 盤點操作 | ✅ | ✅ | ✅ | ❌ |
| 清單編輯 | ✅ | ✅ | ✅ | ❌ |
| 群組管理/角色指派 | ✅ | ✅ | ❌ | ❌ |

- **DB（migration）**：`group_members.role`（`admin | editor | viewer`，default `editor`＋CHECK）；既有成員 backfill → `editor`；`owner` 唯一事實來源維持 `groups.owner_id`（權限檢查先判 owner，再判 role）
- **API**：權限檢查集中於 visibility/group service；`PATCH /api/groups/{id}/members/{user_id}` 角色變更；變更寫 audit log
- **Web**：群組詳情頁角色管理；viewer 依 §5.5 旅程契約（編輯入口不渲染＋首次一次性說明＋詳情頁引導句；403 為後端防線）

**驗收大綱**：矩陣式測試（角色 × 操作）、越權 403、audit 記錄、遷移後既有群組權限零回歸（含 owner 判定）

---

### Phase 31 — 定期報表

**目標**：每月自動彙整上月動態，站內 + Email 交付。

**範圍**
- **機制**：重用 Phase 24 job 機制（`report.monthly`）；每月 1 日生成上月報表
- **內容**：新增物品數、消耗（批次/數量調整）、借出/歸還、過期與即將到期、**庫存估值變化（依賴 27）**、熱門分類/位置
- **DB**：`reports`（`user_id`、`period`（`YYYY-MM`，Asia/Taipei）、`payload` JSON、`generated_at`）；**範圍**＝該使用者可見的全部物品（含群組共用），不摻入他人私人資料
- **交付**：站內通知（`report_ready` 類型）＋ Email HTML（CSV 附件為 stretch）；Email 與站內詳情共用同一 payload 渲染（站內詳情即 Email 預覽）；**Email 最小契約**：雙語模板（zh-TW／en 依收件者偏好）＋ plain-text fallback＋CSV 檔名 i18n；`/reports` 頁瀏覽歷史（清單 + 詳情）
- **導覽**：`/reports` 併入「分析」群組（見 §5.3）；行動版 drawer 二層分組元件計入本 phase
- **設定**：開啟/關閉（預設開，置於設定「通知與提醒」群組）；先做月報，週報 stretch
- **時區**：固定 `Asia/Taipei`（見 §5.6）

**驗收大綱**：排程冪等、空資料用戶跳過不發、內容正確性（fixture 對帳）、Email fail-soft、月初邊界（Asia/Taipei，含 UTC 差異）

**依賴**：Phase 24（排程機制）、Phase 27（估值資料）

---

### Phase 32 — AI 批次入庫＋智慧分類建議

**目標**：多張照片 → 批次建物品草稿；AI 建議融入歷史偏好。

**範圍**
- **批次入庫流程**
  - 多圖上傳（多選檔案/連續拍照）→ 上傳即建 `pending` 草稿；**處理模型：伺服器端狀態機＋前端逐張觸發** — 前端依序呼叫 `POST /api/ai/drafts/{id}/process`（伺服器單張呼叫既有 Gemini suggest；成功 → `ready`、失敗 → `failed`＋error）；**不引入背景 worker**
  - **草稿審核 UI**：卡片式（縮圖、AI 名稱/描述/分類/標籤建議、可編輯、接受/丟棄）；四態卡（排隊/辨識中/失敗重試/完成）＋頂部批量條（全選／全部接受／全部丟棄），狀態與離開恢復見 §5.4
  - 審核完成 → 批次建立；失敗可重試；速率控制（Gemini 配額）
- **DB**：`ai_draft_items`（`owner_id`、`source: batch_photo | receipt`（為 33 預留）、`image_id`、`payload` JSON、`status: pending|processing|ready|failed|accepted|discarded`、`error`(nullable)、`processed_at`(nullable)、`created_at`）— 存伺服器端，刷新不丟（四態卡以狀態為唯一來源）
- **智慧分類建議**：以本人歷史資料生成「名稱關鍵詞 → 分類/位置/標籤」局部規則；AI 建議附「依歷史：廚房」徽章；LLM 不可用時規則仍生效
- **隱私**：僅使用本人資料

**驗收大綱**：批處理狀態機、配額錯誤處理、草稿編輯後建立正確、建議排序（歷史優先）、失敗重試與離開恢復（伺服器端狀態為唯一來源）

---

### Phase 33 — AI 收據辨識

**目標**：拍收據 → 結構化品項 → 草稿審核 → 帶入成本建物品。

**範圍**
- 收據照片（可多張同次採購）→ Gemini 結構化抽取：商家、日期、品項（名稱、數量、單價、小計）
- 結果進**與 Phase 32 相同的草稿審核 UI**（重用元件）
- 確認後建物品：`cost` 帶入（依賴 27）；分類建議沿用 32 的歷史規則
- **對帳提示**：品項總計 vs 收據總額差異警告（不阻擋）

**驗收大綱**：fixture 收據（mock LLM）、多頁、單價缺失處理、草稿→物品欄位映射

**依賴**：Phase 32（草稿 UI）、Phase 27（成本欄位）

---

### Phase 34 — AI 自然語言搜尋＋物品問答

**目標**：用說的找東西（「廚房裡快過期的藥」、「借出去還沒還的工具」）；對物品資料問答。

**範圍**
- **NL 搜尋**：自然語言 → LLM function-calling 轉結構化 filters（category/location/expiry/loan/quantity）→ 執行既有搜尋 API
  - 顯示「理解為：位置=廚房、到期<7天」chip，可一鍵修正
  - **fallback**：LLM 不可用 → 關鍵字搜尋（現行行為），UI 不報錯
- **物品問答**：對檢索出的 top-k 物品摘要問答，回答附引用連結；明確聲明「以系統資料為限」
- **成本/安全**：rate limit、每日配額、prompt injection 防護（物品名/描述視為資料，非指令）；opt-in 開關（送出物品摘要至 Gemini）

**驗收大綱**：filters 轉譯純函式測試（含歧義句）、注入案例、無 LLM 時 fallback、配額耗盡行為、golden eval（≥20 句→filters；mock 模式進 CI、`EVAL_LIVE=1` 手動呼叫 Gemini 計分）

---

## 七、橫向技術主題

### 排程機制（Phase 24 建立、31 重用）
- 模式：**外部 cron ＋ 冪等 job 端點**（與 Phase 21 `process-retries` 一致）
- 認證：登入（PAT）；部署文件補 cron 範例
- `apscheduler` 依賴為 v1 遺留、維持未啟用（Phase 24 展開時移除）；若未來需要分鐘級排程再評估 worker 進程
- 所有 job 必須冪等且可重入（同日重跑安全）

### 位置樹查詢
- adjacency list ＋ recursive CTE（PG / SQLite 相容）；若未來層深或量大再考慮材料化路徑

### i18n 政策
- 所有新 UI 字串進 `messages/zh-TW.json` + `messages/en.json`（近期 commit 已建立慣例）
- 新增通知類型需同步兩語系標題模板

### 測試與型別
- 每 phase 依 TDD 節奏；API pytest ＋ Web vitest 全綠為 merge 前條件
- API 變更後 regen `packages/api-types`；web `tsc --noEmit`
- CHANGELOG 逐 phase 條目（`2.0.0-alpha.22` 起續編）
- migration 從 `0016` 起編號
- **LLM eval（小型）**：`apps/api/evals/` — golden cases（jsonl）＋ pytest 評分；mock 模式進 CI、`EVAL_LIVE=1` 手動呼叫 Gemini 計分；34 起累積，32／33 prompt 變更時同步補 case；不阻塞 merge

### 備份紀律
- Phase 26（位置樹）執行前，**強制** `GET /api/backup/export` 留存；若 Phase 29 已提前完成，改用還原流程驗證

### 開發流程
- 沿用 worktree（`.claude/worktrees/<name>`）→ TDD → 雙測試 → regen types → CHANGELOG → merge 節奏

---

## 八、未排程候選

| 項目 | 備註 |
|------|------|
| Background Sync（離線新增） | 本次明確排除；需 IndexedDB 佇列 + SW sync 事件 |
| 稽核查詢 UI | 本次未選；後端資料已在 |
| 樓層平面圖互動 | 點熱區篩選位置物品（平面圖欄位已存在） |
| 位置 QR 標籤 | 掃碼 → 該位置物品清單（貼在櫃子/箱子上） |
| 批次成本（per-batch cost） | Phase 27 的延伸 |
| 分享唯讀連結 | 對外展示清單（隱私設計需先想清楚） |
| 標籤列印加印條碼 | Phase 25 stretch |
| 週報 | Phase 31 的延伸 |
| v1 目錄下線 | 打 `v1-final` tag 後移除 `app/`、`templates/`、`static/`、`run_worker.py` 等 |

---

## 九、風險與待決事項

| # | 事項 | 說明 | 處置 |
|---|------|------|------|
| 1 | Phase 26 破壞性遷移 | 位置樹砍掉重建 | 遷移前強制備份；dry-run 腳本；考慮 29 提前 |
| 2 | 通知量體 | 到期提醒上線後量體成長 | 23 偏好中心先於 24；摘要式每日一則 |
| 3 | Gemini 成本/配額 | 32–34 大量使用 | per-user rate limit（額度耗盡僅影響該用戶，非全站）、每日配額、規則式 fallback |
| 4 | 外部條碼 provider 穩定性 | Open Food Facts / Open Library 可用性 | 快取、逾時、fail-soft、手動輸入保底 |
| 5 | 批次與盤點整合 | 差額如何反映到批次 | 調整批次方案（見 Phase 22 決策 2），實作時驗證 |
| 6 | 幣別假設 | 單一幣別、無匯率 | 已決策；文件註明 |
| 7 | 樹狀篩選語義 | 含子孫 vs 僅此層 | 預設含子孫 + toggle（實作時可調） |
| 8 | 批次模式誤開 | 開啟後想關閉 | 已決策：可關閉併回總量（Phase 22 決策 4） |
| 9 | 通知疲乏 | `expired` 每日彙總上限 | 已決策：14 天後停止推播、站內保留（Phase 24） |
| 10 | 設計文件落差 | `.impeccable.md` 寫 deep purple 但實作為藍色 primary；無 DESIGN.md | 方向待確認（改文件或改 token）；建議後續產出 DESIGN.md |

---

## 十、執行流程（每個 Phase 怎麼開始）

1. 從本文件挑出 phase → 以既有慣例展開 **task-level 實作計畫**（worktree、TDD 步驟、指令、驗收清單；參考 `docs/plans/2026-06-23-ims-workflow-improvements.md` 格式）
2. 開 worktree：`git worktree add .claude/worktrees/<name> -b claude/<name>`
3. TDD 實作 → API pytest ＋ Web vitest 全綠 → regen api-types → typecheck
4. CHANGELOG 條目 → merge 回 main → 更新 `docs/v2-roadmap.md` Phase 表
5. 每個里程碑結束時回顧本文件，按實際狀況調整後續排序
6. **平行化策略（多 worktree）**：Lane A：22 → 24（共用 items／batches／jobs）；Lane A2：23（settings/web，可與 24 平行）；Lane B：26（locations 破壞性，單獨線＋遷移前備份）；Lane C：25（scan／barcode）；Lane D：27 → 31（statistics／reports）；Lane E：28／29／30（互不衝突）；Lane F：32 → 33 → 34（AI 鏈）。衝突熱點：settings 目錄（23 首發，其後各線僅加子路由頁）、items 模組（22／25／26／27 觸碰 → 序列化或小心 rebase）

---

## GSTACK REVIEW REPORT

> Item-Manage-System × 本文件（main 分支）。gstack 工具鏈未安裝 → 文字模式（best effort：review-log／telemetry 以本附錄＋`~/.gstack/projects/guan4tou2-Item-Manage-System/` 檔案代替）。
> 2026-10-15 完成兩輪計畫審查：`/plan-design-review`（§五契約、D3–D17）＋ `/plan-eng-review`（21 findings 全數批准入稿）。Outside voices：設計 2 份＋工程 2 份（含免費模型）獨立報告，已交叉分析。

| Runs | Status | Findings |
|------|--------|----------|
| `/plan-design-review` · 2026-10-15 | CLEAR | 7 passes；score 3→9/10；D3–D17 定案入稿 |
| `/plan-eng-review` · 2026-10-15 | CLEAR | 21 findings（F1–F6／S2-A~C／S3-A~E／S4-A／OV-1~6）全數 fold；0 unresolved |

### 評分軌跡（plan-design-review）

| Pass | 維度 | 審查前 | 審查後 |
|------|------|--------|--------|
| 1 | Information Architecture | 3/10 | 9/10 |
| 2 | Interaction State Coverage | 2/10 | 8/10 |
| 3 | User Journey & Emotional Arc | 4/10 | 9/10 |
| 4 | AI Slop Risk | 7/10 | 9/10 |
| 5 | Design System Alignment | 6/10 | 9/10 |
| 6 | Responsive & A11y | 4/10 | 9/10 |
| 7 | Unresolved Design Decisions | 5/10 | 9/10 |

### NOT in scope（本次審查明確不處理）

- 完整視覺重設計、品牌重塑（維持現有設計系統）
- Background Sync／離線新增；稽核查詢 UI（本輪已排除）
- 品類化到期策略（N=7 固定；未來以「物品層級覆寫」擴充）
- 視覺 mockup 產出（後續；`DESIGN.md` 已於 consultation 產出）
- （eng）完整 LLM eval 平台（僅小型 golden harness）
- （eng）Email 深色／無障礙完整契約（僅最小契約：雙語＋plain-text fallback）
- （eng）位置樹路徑保真（維持 best-effort；遷移報告列合併／孤兒／未指派數）

### What already exists（已內化的既有資產）

- §5.1 行動卡群組＝既有 `stat-card`／`low-stock-card` 模式重排＋新增到期卡
- §5.2 設定頁重構保留既有 10 個設定面板元件；子路由＋索引頁為新增外殼
- §5.4 狀態表重用 `skeleton`／`sonner` toast／`alert-dialog`／`Badge`
- §5.5 到期模式視圖為 items 列表擴充模式，非新頁面
- §5.7 FAB 為新 shell 元件；樹鍵盤操作沿用既有無障礙模式
- （eng）job 模式沿用 `process-retries` 外部 cron 慣例；通知 fan-out 過濾點既有（`emit()`／`deliver_all()`）
- （eng）備份 export 既有（`format_version:1`）；測試三層資產既有（pytest 454／vitest 41 檔／playwright 11 specs）
- （eng）`QuantityLog`／`users.preferences` JSONB／Gemini `suggest_from_image` 既有；到期標註概念來自 v1（移植為批次模型）

### 實作任務（各 phase 展開時帶入）

| 契約 | 落點 phase | 展開時動作 |
|------|-----------|-----------|
| §5.1 | 22（建立）、24／27（遵循） | 行動卡群組實作＋既有卡片重排 |
| §5.2 | 23（第一步） | 設定頁子路由＋索引頁；10 面板零回歸遷移 |
| §5.3 | 31 | 分析群組；drawer 二層展開元件 |
| §5.4 | 22／23／25／26／29／31／32／33 | 狀態表逐介面填寫（驗收條件） |
| §5.5 | 22（到期模式視圖）、30（viewer） | 旅程與回饋實作 |
| §5.6 | 22（tokens）、27（金額格式）、32（AiMark） | token 建立＋對比度測試 |
| §5.7 | 25（FAB）、26（樹雙模式）、30（a11y） | 響應式與無障礙驗收 |
| eng F5・S4-A | 22 | FOR UPDATE＋Asia/Taipei helper＋聚合索引＋query count 斷言 |
| eng F1・S2-B・S2-C・OV-5 | 24 | job_runs／expiry_alerts、admin 觸發（403）、失敗語義、停跑警示、移除 apscheduler、未知 job→404 |
| eng F2 | 30 | `group_members.role`＋backfill＋矩陣／403 測試 |
| eng F3・OV-2 | 29 | 全量實體＋format_version 政策＋交易回滾＋invariant 對帳 |
| eng F4・OV-4 | 32 | 狀態機 enum＋逐張觸發＋恢復；§5.2 個人＞偏好 AI 開關 |
| eng S2-A・S3-A | 23 | 10 面板＋taxonomy＋admin 可見性 CRITICAL 回歸；API 契約測試 |
| eng S3-B~E・S4-A | 23/24/31/34 | 契約／端到端／月初時區／golden eval（`apps/api/evals/`） |
| eng OV-1・OV-3・OV-5 | 26/31 | warehouse 正交＋報告檢查列；報表 scope／period＋Email 契約 |
| eng（inline 圖） | 22/24/29/30/32 | 批次 service／jobs／backup import／visibility／ai draft 服務加 ASCII 流程註解 |

### 待辦（TODOS.md）

1. 釐清 `.impeccable.md` 與實作色票落差（deep purple vs 藍色 primary）→ 統一方針
2. 後續以 `/design-consultation` 產出 `DESIGN.md`（沉澱 §五契約）
3. （可選）安裝 gstack designer 後補跑視覺審查
4. 各 phase 展開時：§5.4 狀態表逐介面填寫，作為驗收條件

### Review Log

- 2026-10-15：`/plan-design-review` on `docs/plans/2026-10-15-next-iteration-roadmap.md`，7 passes 完成
- 決策 D3–D17 已與使用者逐項確認並寫入本文件（§五 ＋ 各 phase 範圍）
- Outside voices：2 份獨立報告已交叉分析（高信心共識：儀表板層級、IA 崩潰、狀態缺口、備份信任斷點、viewer 體驗）
- 2026-10-15：`/plan-eng-review` 完成（Sections 1–4 ＋ outside voice ×2 ＋ required outputs）；21 findings 全數經使用者逐一批准並已入稿；Test Plan Artifact＝`docs/plans/2026-10-15-eng-review-test-plan.md`；tasks JSONL＝`~/.gstack/projects/guan4tou2-Item-Manage-System/tasks-eng-review-*.jsonl`
- 工程 outside voices：2 份獨立報告交叉分析（採納：warehouse 正交、還原版本政策、報表範圍／Email 契約、AI 入口落點、三項澄清；裁定不動：viewer enforcement 已覆蓋、nav 11 已核實、M3 依賴已聲明）
- 已知限制：本機未安裝 gstack 工具鏈（designer/browse/log），review log 以本附錄為正式紀錄

**VERDICT:** DESIGN + ENG CLEARED — ready to implement

NO UNRESOLVED DECISIONS
