import { describe, expect, it } from 'vitest'
import { getEuropeLondonHour, stepDateUtc } from './dateTime'

describe('getEuropeLondonHour', () => {
  it('extracts correct hour during winter GMT (UTC+0)', () => {
    // 14:30 UTC in January is 14:30 GMT (hour 14)
    expect(getEuropeLondonHour('2026-01-02T14:30:00Z')).toBe(14)
    // 00:00 UTC in January is 00:00 GMT (hour 0)
    expect(getEuropeLondonHour('2026-01-02T00:00:00Z')).toBe(0)
    // 23:30 UTC in January is 23:30 GMT (hour 23)
    expect(getEuropeLondonHour('2026-01-02T23:30:00Z')).toBe(23)
  })

  it('extracts correct hour during summer BST (UTC+1)', () => {
    // In BST, period 1 starts at 23:00 UTC the previous day, corresponding to 00:00 BST delivery day
    expect(getEuropeLondonHour('2026-06-30T23:00:00Z')).toBe(0)
    expect(getEuropeLondonHour('2026-06-30T23:30:00Z')).toBe(0)

    // Midday: 12:00 UTC in July is 13:00 BST
    expect(getEuropeLondonHour('2026-07-01T12:00:00Z')).toBe(13)

    // 22:00 UTC in July is 23:00 BST
    expect(getEuropeLondonHour('2026-07-01T22:00:00Z')).toBe(23)
  })

  it('accepts Date objects directly', () => {
    const d = new Date('2026-01-15T08:00:00Z')
    expect(getEuropeLondonHour(d)).toBe(8)
  })

  it('throws RangeError for invalid date inputs', () => {
    expect(() => getEuropeLondonHour('not-a-valid-date')).toThrow(RangeError)
  })
})

describe('stepDateUtc', () => {
  it('steps forward and backward within the same month', () => {
    expect(stepDateUtc('2026-01-15', 1)).toBe('2026-01-16')
    expect(stepDateUtc('2026-01-15', -1)).toBe('2026-01-14')
    expect(stepDateUtc('2026-01-15', 0)).toBe('2026-01-15')
  })

  it('steps across a month boundary forward (e.g. Jan 31 to Feb 1)', () => {
    expect(stepDateUtc('2026-01-31', 1)).toBe('2026-02-01')
    expect(stepDateUtc('2026-01-30', 3)).toBe('2026-02-02')
  })

  it('steps across a month boundary backward (e.g. Feb 1 to Jan 31)', () => {
    expect(stepDateUtc('2026-02-01', -1)).toBe('2026-01-31')
    expect(stepDateUtc('2026-03-01', -1)).toBe('2026-02-28') // 2026 is non-leap year
  })

  it('handles leap year month boundaries correctly', () => {
    expect(stepDateUtc('2024-02-28', 1)).toBe('2024-02-29')
    expect(stepDateUtc('2024-02-29', 1)).toBe('2024-03-01')
    expect(stepDateUtc('2024-03-01', -1)).toBe('2024-02-29')
  })

  it('steps across year boundaries forward and backward', () => {
    expect(stepDateUtc('2025-12-31', 1)).toBe('2026-01-01')
    expect(stepDateUtc('2026-01-01', -1)).toBe('2025-12-31')
  })

  it('throws RangeError for invalid date string format', () => {
    expect(() => stepDateUtc('2026/01/15', 1)).toThrow(RangeError)
    expect(() => stepDateUtc('invalid', 1)).toThrow(RangeError)
  })
})
