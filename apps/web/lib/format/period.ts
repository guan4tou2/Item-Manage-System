/**
 * 月報週期（`YYYY-MM`）顯示格式（Phase 31）。
 *
 * 以 UTC 中午（避開時區位移）建立日期，再交給 `Intl.DateTimeFormat`
 * 產生在地化「年月」標題（zh-TW → `2026年9月`、en → `September 2026`）。
 * 無法解析的字串一律原樣回傳，永不拋錯。
 */
export function formatPeriod(period: string, locale: string): string {
  const match = /^(\d{4})-(\d{2})$/.exec(period)
  if (!match) return period
  const year = Number(match[1])
  const month = Number(match[2])
  if (month < 1 || month > 12) return period
  try {
    return new Intl.DateTimeFormat(locale, {
      year: "numeric",
      month: "long",
      timeZone: "UTC",
    }).format(new Date(Date.UTC(year, month - 1, 1, 12)))
  } catch {
    return period
  }
}
