/**
 * Date and time helper utilities for timezone-aware formatting and arithmetic.
 */

const londonHourFormatter = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'Europe/London',
  hour: 'numeric',
  hourCycle: 'h23',
})

/**
 * Extract hour of day (0-23) in Europe/London timezone from an ISO string or Date object.
 *
 * Correctly accounts for Daylight Saving Time (BST = UTC+1 vs GMT = UTC+0).
 * For example:
 *   - "2026-01-02T14:30:00Z" (GMT) -> hour 14
 *   - "2026-06-30T23:00:00Z" (BST, period 1 starts 23:00 UTC previous day = 00:00 BST) -> hour 0
 *
 * @param dateInput ISO timestamp string or Date instance.
 * @returns Hour of day in UK local time (0 to 23).
 */
export function getEuropeLondonHour(dateInput: string | Date): number {
  const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput
  if (Number.isNaN(date.getTime())) {
    throw new RangeError(
      `Invalid date input for Europe/London hour extraction: ${String(dateInput)}`,
    )
  }
  const parts = londonHourFormatter.formatToParts(date)
  const hourPart = parts.find((part) => part.type === 'hour')
  if (!hourPart) {
    throw new Error(
      `Unable to extract hour part from Europe/London date: ${date.toISOString()}`,
    )
  }
  return parseInt(hourPart.value, 10)
}

/**
 * Step a calendar date (YYYY-MM-DD) by a given number of days using pure Date.UTC arithmetic.
 *
 * Avoids any local browser timezone methods (getDate, setDate, getFullYear, etc.)
 * which can cause day shifts across timezones or Daylight Saving clock changes.
 *
 * @param dateStr ISO date string in YYYY-MM-DD format.
 * @param offsetDays Number of days to add (positive) or subtract (negative).
 * @returns New ISO date string in YYYY-MM-DD format.
 */
export function stepDateUtc(dateStr: string, offsetDays: number): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dateStr)
  if (!match) {
    throw new RangeError(
      `Invalid date string format: '${dateStr}'. Expected YYYY-MM-DD.`,
    )
  }

  const year = parseInt(match[1], 10)
  const month = parseInt(match[2], 10) // 1-12
  const day = parseInt(match[3], 10)

  // Use Date.UTC calendar arithmetic: monthIndex is 0-indexed (month - 1).
  // Adding offsetDays to day normalizes month and year rollovers automatically.
  const utcMs = Date.UTC(year, month - 1, day + offsetDays)
  const dateObj = new Date(utcMs)

  const resYear = dateObj.getUTCFullYear()
  const resMonth = String(dateObj.getUTCMonth() + 1).padStart(2, '0')
  const resDay = String(dateObj.getUTCDate()).padStart(2, '0')

  return `${resYear}-${resMonth}-${resDay}`
}
