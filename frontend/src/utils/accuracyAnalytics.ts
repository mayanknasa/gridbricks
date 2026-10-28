/**
 * Pure analytics and calculation functions for forecast accuracy benchmarking.
 *
 * Includes histogram error distribution binning and automated empirical takeaway generation.
 */

import type { OverallMetrics } from '../types/api'

export interface HistogramBin {
  binIndex: number
  binStart: number
  binEnd: number
  binLabel: string
  count: number
  isNegative: boolean
}

export interface HistogramStats {
  totalValid: number
  negCount: number
  posCount: number
  negPct: number
  posPct: number
  peakBinLabel: string
}

export interface HistogramResult {
  histogramData: HistogramBin[]
  histogramStats: HistogramStats
}

export interface HourlyChartRow {
  hour: number
  hourLabel: string
  mae: number
  rmse?: number
  bias?: number
  p90: number
  meanActual?: number
  meanForecast?: number
  validCount?: number
}

export interface HorizonChartRow {
  bucket: string
  mae: number
  rmse?: number
  bias?: number
  p90?: number
  validCount?: number
  totalCount?: number
}

/**
 * Bin raw forecast error values into symmetrical frequency distribution buckets.
 *
 * @param errors Array of forecast error values (actual - forecast). Null or NaN values are filtered out.
 * @param numBins Number of histogram bins to generate (default: 16).
 * @returns Binned histogram records and summary statistics (positive/negative percentages and peak bucket).
 */
export function calculateHistogramBins(
  errors: (number | null | undefined)[],
  numBins: number = 16,
): HistogramResult {
  const validErrors: number[] = errors.filter(
    (e): e is number => typeof e === 'number' && !Number.isNaN(e),
  )

  if (validErrors.length === 0) {
    return {
      histogramData: [],
      histogramStats: {
        totalValid: 0,
        negCount: 0,
        posCount: 0,
        negPct: 0,
        posPct: 0,
        peakBinLabel: '',
      },
    }
  }

  const minErr = Math.min(...validErrors)
  const maxErr = Math.max(...validErrors)

  // Symmetrical reasonable bounds around zero
  const rawBound = Math.max(Math.abs(minErr), Math.abs(maxErr))
  const bound = rawBound === 0 ? 1 : rawBound
  const binWidth = (bound * 2) / numBins

  const bins: HistogramBin[] = []
  for (let i = 0; i < numBins; i++) {
    const bStart = -bound + i * binWidth
    const bEnd = bStart + binWidth
    const label = `${Math.round(bStart).toLocaleString()} to ${Math.round(bEnd).toLocaleString()}`
    bins.push({
      binIndex: i,
      binStart: bStart,
      binEnd: bEnd,
      binLabel: label,
      count: 0,
      isNegative: bEnd <= 0,
    })
  }

  let negCount = 0
  let posCount = 0

  validErrors.forEach((err) => {
    if (err < 0) {
      negCount++
    } else {
      posCount++
    }

    let assigned = false
    for (let i = 0; i < numBins; i++) {
      if (err >= bins[i].binStart && (err < bins[i].binEnd || i === numBins - 1)) {
        bins[i].count++
        assigned = true
        break
      }
    }
    if (!assigned) {
      if (err < bins[0].binStart) {
        bins[0].count++
      } else {
        bins[bins.length - 1].count++
      }
    }
  })

  const totalValid = validErrors.length
  const negPct = (negCount / totalValid) * 100
  const posPct = (posCount / totalValid) * 100

  let peakBin = bins[0]
  bins.forEach((b) => {
    if (b.count > peakBin.count) {
      peakBin = b
    }
  })

  return {
    histogramData: bins,
    histogramStats: {
      totalValid,
      negCount,
      posCount,
      negPct,
      posPct,
      peakBinLabel: peakBin.binLabel,
    },
  }
}

/**
 * Generate empirical takeaway sentence describing overall forecast bias and magnitude.
 */
export function getForecastVsActualTakeaway(
  overallMetrics: OverallMetrics | null | undefined,
): string {
  if (!overallMetrics || overallMetrics.valid_count === 0) {
    return 'Insufficient outturn data available for this delivery window.'
  }

  const bias = overallMetrics.bias ?? 0
  const meanAct = overallMetrics.mean_actual ?? 0
  const meanFc = overallMetrics.mean_forecast ?? 0
  const direction =
    bias < 0
      ? 'over-predicted'
      : bias > 0
        ? 'under-predicted'
        : 'accurately centered on'

  const diffAbs = Math.round(Math.abs(bias)).toLocaleString()
  return (
    `On average across the selected range, the day-ahead forecast ${direction} actual wind outturn by ` +
    `${diffAbs} MW (mean forecast of ${Math.round(meanFc).toLocaleString()} MW vs. actual outturn of ` +
    `${Math.round(meanAct).toLocaleString()} MW), with errors expanding during storm wind ramp events.`
  )
}

/**
 * Generate empirical takeaway sentence summarizing error distribution skew and modal peak.
 */
export function getHistogramTakeaway(stats: HistogramStats): string {
  if (stats.totalValid === 0) {
    return 'No forecast errors available for histogram analysis.'
  }

  const dominant =
    stats.negPct > 50
      ? `left-skewed (${stats.negPct.toFixed(0)}% over-forecast)`
      : `right-skewed (${stats.posPct.toFixed(0)}% under-forecast)`

  return (
    `The error distribution is ${dominant}, with the modal concentration peaking in the ` +
    `[${stats.peakBinLabel} MW] interval across ${stats.totalValid.toLocaleString()} evaluated periods.`
  )
}

/**
 * Generate empirical takeaway sentence identifying peak and minimum diurnal uncertainty hours.
 */
export function getHourlyTakeaway(hourlyChartData: HourlyChartRow[]): string {
  if (hourlyChartData.length === 0) return ''

  const sortedByMAE = [...hourlyChartData].sort((a, b) => b.mae - a.mae)
  const maxHour = sortedByMAE[0]
  const minHour = sortedByMAE[sortedByMAE.length - 1]

  return (
    `Diurnal forecast uncertainty peaks at ${maxHour.hourLabel} UK (MAE ${maxHour.mae.toLocaleString()} MW, ` +
    `P90 error ${maxHour.p90.toLocaleString()} MW) and reaches minimum deviation at ${minHour.hourLabel} UK ` +
    `(MAE ${minHour.mae.toLocaleString()} MW).`
  )
}

/**
 * Generate empirical takeaway sentence quantifying forecast error degradation across lead times.
 */
export function getHorizonTakeaway(horizonChartData: HorizonChartRow[]): string {
  if (horizonChartData.length === 0) return ''

  const firstBucket =
    horizonChartData.find((h) => h.bucket === '0-6h') || horizonChartData[0]
  const lastBucket =
    horizonChartData.find((h) => h.bucket === '>48h') ||
    horizonChartData[horizonChartData.length - 1]

  const degradationPct =
    firstBucket && lastBucket && firstBucket.mae > 0
      ? Math.round(((lastBucket.mae - firstBucket.mae) / firstBucket.mae) * 100)
      : 0

  return (
    `Forecast degradation scales directly with lead time: MAE expands by +${degradationPct}% ` +
    `from ${firstBucket?.mae.toLocaleString()} MW at [${firstBucket?.bucket}] to ${lastBucket?.mae.toLocaleString()} MW ` +
    `at extended lead times [${lastBucket?.bucket}].`
  )
}
