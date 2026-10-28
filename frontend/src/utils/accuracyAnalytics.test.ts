import { describe, expect, it } from 'vitest'
import type { OverallMetrics } from '../types/api'
import {
  calculateHistogramBins,
  getForecastVsActualTakeaway,
  getHistogramTakeaway,
  getHorizonTakeaway,
  getHourlyTakeaway,
} from './accuracyAnalytics'

describe('calculateHistogramBins', () => {
  it('handles empty or non-numeric error inputs gracefully', () => {
    const result = calculateHistogramBins([])
    expect(result.histogramData).toEqual([])
    expect(result.histogramStats.totalValid).toBe(0)
    expect(result.histogramStats.peakBinLabel).toBe('')

    const filtered = calculateHistogramBins([null, NaN, undefined])
    expect(filtered.histogramData).toEqual([])
    expect(filtered.histogramStats.totalValid).toBe(0)
  })

  it('bins symmetric hand-checked error values correctly', () => {
    // Errors: -200, -100, +100, +200
    const errors = [-200, -100, 100, 200]
    const result = calculateHistogramBins(errors, 4)

    expect(result.histogramStats.totalValid).toBe(4)
    expect(result.histogramStats.negCount).toBe(2)
    expect(result.histogramStats.posCount).toBe(2)
    expect(result.histogramStats.negPct).toBe(50)
    expect(result.histogramStats.posPct).toBe(50)

    // Total counts across all bins must equal the number of valid errors
    const totalCount = result.histogramData.reduce((sum, b) => sum + b.count, 0)
    expect(totalCount).toBe(4)
    expect(result.histogramData).toHaveLength(4)
  })

  it('identifies skewed error distribution and peak bin', () => {
    // Left-skewed (majority negative over-forecast errors)
    const errors = [-150, -140, -130, -50, 20]
    const result = calculateHistogramBins(errors, 6)

    expect(result.histogramStats.totalValid).toBe(5)
    expect(result.histogramStats.negCount).toBe(4)
    expect(result.histogramStats.posCount).toBe(1)
    expect(result.histogramStats.negPct).toBe(80)
    expect(result.histogramStats.posPct).toBe(20)
    expect(result.histogramStats.peakBinLabel).toBeTruthy()
  })

  it('safely handles zero-only error arrays without division by zero', () => {
    const result = calculateHistogramBins([0, 0, 0])
    expect(result.histogramStats.totalValid).toBe(3)
    expect(result.histogramData).toHaveLength(16)
  })
})

describe('getForecastVsActualTakeaway', () => {
  it('returns fallback message when metrics are missing or have no valid counts', () => {
    expect(getForecastVsActualTakeaway(null)).toBe(
      'Insufficient outturn data available for this delivery window.',
    )
    expect(
      getForecastVsActualTakeaway({
        total_count: 48,
        valid_count: 0,
        missing_count: 48,
        mae: null,
        rmse: null,
        bias: null,
        nmae_pct: null,
        p50: null,
        p90: null,
        p95: null,
        mean_actual: null,
        mean_forecast: null,
      }),
    ).toBe('Insufficient outturn data available for this delivery window.')
  })

  it('generates over-prediction takeaway when bias is negative', () => {
    const metrics: OverallMetrics = {
      total_count: 48,
      valid_count: 48,
      missing_count: 0,
      mae: 320,
      rmse: 410,
      bias: -250.4,
      nmae_pct: 2.1,
      p50: 250,
      p90: 520,
      p95: 610,
      mean_actual: 12000,
      mean_forecast: 12250,
    }

    const takeaway = getForecastVsActualTakeaway(metrics)
    expect(takeaway).toContain('over-predicted')
    expect(takeaway).toContain('250 MW')
    expect(takeaway).toContain('mean forecast of 12,250 MW vs. actual outturn of 12,000 MW')
  })

  it('generates under-prediction takeaway when bias is positive', () => {
    const metrics: OverallMetrics = {
      total_count: 48,
      valid_count: 48,
      missing_count: 0,
      mae: 280,
      rmse: 350,
      bias: 180.2,
      nmae_pct: 1.2,
      p50: 210,
      p90: 450,
      p95: 530,
      mean_actual: 15000,
      mean_forecast: 14820,
    }

    const takeaway = getForecastVsActualTakeaway(metrics)
    expect(takeaway).toContain('under-predicted')
    expect(takeaway).toContain('180 MW')
  })

  it('generates centered takeaway when bias is exactly zero', () => {
    const metrics: OverallMetrics = {
      total_count: 48,
      valid_count: 48,
      missing_count: 0,
      mae: 100,
      rmse: 120,
      bias: 0,
      nmae_pct: 1.0,
      p50: 90,
      p90: 150,
      p95: 180,
      mean_actual: 10000,
      mean_forecast: 10000,
    }

    const takeaway = getForecastVsActualTakeaway(metrics)
    expect(takeaway).toContain('accurately centered on')
  })
})

describe('getHistogramTakeaway', () => {
  it('returns fallback message when totalValid is 0', () => {
    const takeaway = getHistogramTakeaway({
      totalValid: 0,
      negCount: 0,
      posCount: 0,
      negPct: 0,
      posPct: 0,
      peakBinLabel: '',
    })
    expect(takeaway).toBe('No forecast errors available for histogram analysis.')
  })

  it('identifies left-skewed over-forecast distribution', () => {
    const takeaway = getHistogramTakeaway({
      totalValid: 1440,
      negCount: 1008,
      posCount: 432,
      negPct: 70.0,
      posPct: 30.0,
      peakBinLabel: '-500 to 0',
    })
    expect(takeaway).toContain('left-skewed (70% over-forecast)')
    expect(takeaway).toContain('[-500 to 0 MW]')
    expect(takeaway).toContain('1,440 evaluated periods')
  })

  it('identifies right-skewed under-forecast distribution', () => {
    const takeaway = getHistogramTakeaway({
      totalValid: 100,
      negCount: 40,
      posCount: 60,
      negPct: 40.0,
      posPct: 60.0,
      peakBinLabel: '0 to 200',
    })
    expect(takeaway).toContain('right-skewed (60% under-forecast)')
  })
})

describe('getHourlyTakeaway', () => {
  it('returns empty string when dataset is empty', () => {
    expect(getHourlyTakeaway([])).toBe('')
  })

  it('identifies peak and minimum uncertainty hours correctly', () => {
    const rows = [
      { hour: 0, hourLabel: '00:00', mae: 150, p90: 300 },
      { hour: 8, hourLabel: '08:00', mae: 420, p90: 750 },
      { hour: 14, hourLabel: '14:00', mae: 210, p90: 450 },
      { hour: 18, hourLabel: '18:00', mae: 580, p90: 980 },
    ]

    const takeaway = getHourlyTakeaway(rows)
    expect(takeaway).toContain('uncertainty peaks at 18:00 UK (MAE 580 MW, P90 error 980 MW)')
    expect(takeaway).toContain('minimum deviation at 00:00 UK (MAE 150 MW)')
  })
})

describe('getHorizonTakeaway', () => {
  it('returns empty string when horizon array is empty', () => {
    expect(getHorizonTakeaway([])).toBe('')
  })

  it('calculates degradation scaling between 0-6h and >48h buckets', () => {
    const buckets = [
      { bucket: '<0h', mae: 180 },
      { bucket: '0-6h', mae: 200 },
      { bucket: '6-12h', mae: 260 },
      { bucket: '12-24h', mae: 340 },
      { bucket: '24-36h', mae: 410 },
      { bucket: '36-48h', mae: 480 },
      { bucket: '>48h', mae: 520 },
    ]

    // (520 - 200) / 200 * 100 = 160%
    const takeaway = getHorizonTakeaway(buckets)
    expect(takeaway).toContain('Forecast degradation scales directly with lead time')
    expect(takeaway).toContain('+160%')
    expect(takeaway).toContain('200 MW at [0-6h]')
    expect(takeaway).toContain('520 MW at extended lead times [>48h]')
  })
})
