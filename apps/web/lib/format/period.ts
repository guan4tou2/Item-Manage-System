/**
 * 報表週期顯示格式（Phase 31 月報、Phase 42 週報）。
 *
 * 月報 key 為 `YYYY-MM`；週報以 `period_start`／`period_end` 兩個 ISO 日期
 * 產生在地化範圍。所有日期都以 UTC 中午建立（避開時區位移），
 * 無法解析的輸入一律原樣回傳，永不拋錯。
 */

interface IsoDate {
  year: number
  month: number
  day: number
}

function parseIsoDate(value: string): IsoDate | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (!match) return null
  const year = Number(match[1])
  const month = Number(match[2])
  const day = Number(match[3])
  const date = new Date(Date.UTC(year, month - 1, day, 12))
  if (
    date.getUTCFullYear() !== year ||
    date.getUTCMonth() !== month - 1 ||
    date.getUTCDate() !== day
  ) {
    return null
  }
  return { year, month, day }
}

function isZh(locale: string): boolean {
  return locale.toLowerCase().startsWith("zh")
}

function shortMonth(month: number): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    timeZone: "UTC",
  }).format(new Date(Date.UTC(2000, month - 1, 15, 12)))
}

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

/**
 * 週報日期範圍：同月省略重複年月，跨月／跨年完整標示。
 *
 * zh-TW → `2026 年 10 月 12–18 日`
 * en     → `Oct 12–18, 2026`
 */
export function formatPeriodRange(
  start: string,
  end: string,
  locale: string,
): string {
  const first = parseIsoDate(start)
  const last = parseIsoDate(end)
  if (!first || !last) return `${start}–${end}`

  if (isZh(locale)) {
    if (first.year === last.year) {
      if (first.month === last.month) {
        return `${first.year} 年 ${first.month} 月 ${first.day}–${last.day} 日`
      }
      return (
        `${first.year} 年 ${first.month} 月 ${first.day} 日–` +
        `${last.month} 月 ${last.day} 日`
      )
    }
    return (
      `${first.year} 年 ${first.month} 月 ${first.day} 日–` +
      `${last.year} 年 ${last.month} 月 ${last.day} 日`
    )
  }

  const firstMonth = shortMonth(first.month)
  const lastMonth = shortMonth(last.month)
  if (first.year === last.year) {
    if (first.month === last.month) {
      return `${firstMonth} ${first.day}–${last.day}, ${first.year}`
    }
    return `${firstMonth} ${first.day}–${lastMonth} ${last.day}, ${first.year}`
  }
  return (
    `${firstMonth} ${first.day}, ${first.year}–` +
    `${lastMonth} ${last.day}, ${last.year}`
  )
}
