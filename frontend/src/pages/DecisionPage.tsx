import React, { useMemo } from 'react'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  AlertTriangle,
  Calendar,
  CheckCircle2,
  Clock,
  HelpCircle,
  Info,
  ShieldAlert,
  ShieldCheck,
  TrendingUp,
  Zap,
} from 'lucide-react'
import { EmptyState } from '../components/common/EmptyState'
import { ErrorState } from '../components/common/ErrorState'
import { LoadingState } from '../components/common/LoadingState'
import { useFilters } from '../context'
import { useForecast, useHourlyMetrics } from '../hooks/useQueries'
import type { ForecastItem } from '../types/api'
import { getEuropeLondonHour, stepDateUtc } from '../utils/dateTime'

interface ChartDataPoint {
  sp: number
  timeLabel: string
  fullInterval: string
  generation: number | null
  publishTimeDisplay: string
  horizonHoursDisplay: string
  isMissing: boolean
  isDerived: boolean
  forecastType: 'published' | 'step_hold' | 'missing'
}

interface BufferRecommendation {
  hour: number
  hourLabel: string
  forecastAvgMW: number | null
  p90BufferMW: number | null
  hedgedVolumeMW: number | null
  bufferRatioPct: number | null
  riskLevel: 'Low' | 'Moderate' | 'Elevated' | 'Unknown'
}

export const DecisionPage: React.FC = () => {
  const {
    startDate,
    endDate,
    deliveryDate,
    cutoff,
    datasetBounds,
    setDeliveryDate,
    setCutoff,
  } = useFilters()

  // 1. Fetch selected forecast for the target delivery date
  const forecastQuery = useForecast(deliveryDate, cutoff)

  // 2. Fetch historical baseline hourly metrics for benchmark period from store
  const baselineStart = startDate || datasetBounds.startDate
  const baselineEnd = endDate || datasetBounds.endDate
  const hourlyMetricsQuery = useHourlyMetrics(baselineStart, baselineEnd, cutoff)

  const isLoading = forecastQuery.isLoading || hourlyMetricsQuery.isLoading
  const isError = forecastQuery.isError || hourlyMetricsQuery.isError
  const errorMessage =
    forecastQuery.error?.message ||
    hourlyMetricsQuery.error?.message ||
    'Failed to load forecast decision data.'

  // Helper formatting functions
  const formatTimeUK = (isoString: string): string => {
    try {
      const dt = new Date(isoString)
      return dt.toLocaleTimeString('en-GB', {
        timeZone: 'Europe/London',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return isoString
    }
  }

  const formatPublishTimeUTC = (isoString: string | null): string => {
    if (!isoString) return 'None'
    try {
      const dt = new Date(isoString)
      return dt.toISOString().replace('T', ' ').substring(0, 16) + ' UTC'
    } catch {
      return isoString
    }
  }

  // -------------------------------------------------------------------------
  // Memoized: Chart Data preparation (48 half-hours)
  // -------------------------------------------------------------------------
  const chartData: ChartDataPoint[] = useMemo(() => {
    if (!forecastQuery.data?.data) return []

    return forecastQuery.data.data.map((item: ForecastItem, index: number) => {
      const sp = index + 1
      const timeLabel = formatTimeUK(item.startTime)

      let horizonHoursDisplay = '—'
      if (item.publishTime) {
        const startMs = new Date(item.startTime).getTime()
        const pubMs = new Date(item.publishTime).getTime()
        const diffH = (startMs - pubMs) / (1000 * 60 * 60)
        horizonHoursDisplay = `${diffH.toFixed(1)}h`
      }

      const nextPeriod = new Date(new Date(item.startTime).getTime() + 30 * 60 * 1000)
      const nextTimeLabel = nextPeriod.toLocaleTimeString('en-GB', {
        timeZone: 'Europe/London',
        hour: '2-digit',
        minute: '2-digit',
      })

      return {
        sp,
        timeLabel,
        fullInterval: `${timeLabel} – ${nextTimeLabel}`,
        generation: item.generation !== null ? Math.round(item.generation * 10) / 10 : null,
        publishTimeDisplay: formatPublishTimeUTC(item.publishTime),
        horizonHoursDisplay,
        isMissing: item.isMissing,
        isDerived: item.isDerived,
        forecastType: item.forecastType,
      }
    })
  }, [forecastQuery.data])

  // -------------------------------------------------------------------------
  // Memoized: Daily Statistics
  // -------------------------------------------------------------------------
  const dayStats = useMemo(() => {
    const items = forecastQuery.data?.data || []
    const valid = items.filter((i) => !i.isMissing && i.generation !== null)
    const published = valid.filter((i) => !i.isDerived)
    const derived = valid.filter((i) => i.isDerived)
    const generations = valid.map((i) => i.generation as number)

    const peakMW = generations.length > 0 ? Math.max(...generations) : null
    const minMW = generations.length > 0 ? Math.min(...generations) : null
    const avgMW =
      generations.length > 0
        ? generations.reduce((acc, curr) => acc + curr, 0) / generations.length
        : null

    return {
      total: items.length,
      validCount: valid.length,
      publishedCount: published.length,
      derivedCount: derived.length,
      missingCount: items.length - valid.length,
      peakMW,
      minMW,
      avgMW,
    }
  }, [forecastQuery.data])

  // -------------------------------------------------------------------------
  // Memoized: Buffer Recommendations Table (24 hourly buckets)
  // -------------------------------------------------------------------------
  const bufferRecommendations: BufferRecommendation[] = useMemo(() => {
    const hourlyP90Map: Record<number, number | null> = {}
    if (hourlyMetricsQuery.data?.data) {
      hourlyMetricsQuery.data.data.forEach((hm) => {
        hourlyP90Map[hm.hour] = hm.p90
      })
    }

    // Group day's selected forecasts by hour (0-23 UK local time)
    const dayForecastByHour: Record<number, number[]> = {}
    for (let h = 0; h < 24; h++) {
      dayForecastByHour[h] = []
    }

    if (forecastQuery.data?.data) {
      forecastQuery.data.data.forEach((item) => {
        if (!item.isMissing && item.generation !== null) {
          const ukHour = getEuropeLondonHour(item.startTime)
          if (dayForecastByHour[ukHour]) {
            dayForecastByHour[ukHour].push(item.generation)
          }
        }
      })
    }

    const recs: BufferRecommendation[] = []
    for (let h = 0; h < 24; h++) {
      const hourStr = String(h).padStart(2, '0')
      const nextHourStr = String((h + 1) % 24).padStart(2, '0')
      const hourLabel = `${hourStr}:00 – ${nextHourStr}:00`

      const gens = dayForecastByHour[h] || []
      const forecastAvgMW =
        gens.length > 0 ? gens.reduce((sum, v) => sum + v, 0) / gens.length : null

      const p90BufferMW = hourlyP90Map[h] ?? null

      let hedgedVolumeMW: number | null = null
      let bufferRatioPct: number | null = null
      let riskLevel: 'Low' | 'Moderate' | 'Elevated' | 'Unknown' = 'Unknown'

      if (forecastAvgMW !== null && p90BufferMW !== null) {
        hedgedVolumeMW = Math.max(0, forecastAvgMW - p90BufferMW)
        if (forecastAvgMW > 0) {
          bufferRatioPct = (p90BufferMW / forecastAvgMW) * 100.0
          if (bufferRatioPct < 22) {
            riskLevel = 'Low'
          } else if (bufferRatioPct <= 35) {
            riskLevel = 'Moderate'
          } else {
            riskLevel = 'Elevated'
          }
        }
      }

      recs.push({
        hour: h,
        hourLabel,
        forecastAvgMW,
        p90BufferMW,
        hedgedVolumeMW,
        bufferRatioPct,
        riskLevel,
      })
    }

    return recs
  }, [forecastQuery.data, hourlyMetricsQuery.data])

  // -------------------------------------------------------------------------
  // Memoized: Plain English Summary Sentence for a Power Buyer
  // -------------------------------------------------------------------------
  const buyerSummarySentence = useMemo(() => {
    if (bufferRecommendations.length === 0 || dayStats.validCount === 0) {
      return 'Insufficient data to compute buffer recommendations.'
    }

    // Find hour with maximum P90 error requirement
    const validRecs = bufferRecommendations.filter(
      (r) => r.p90BufferMW !== null && r.forecastAvgMW !== null
    )
    if (validRecs.length === 0) {
      return 'Historical error distributions are currently unavailable for this cutoff period.'
    }

    const maxP90Rec = [...validRecs].sort(
      (a, b) => (b.p90BufferMW || 0) - (a.p90BufferMW || 0)
    )[0]

    const avgP90 =
      validRecs.reduce((acc, r) => acc + (r.p90BufferMW || 0), 0) / validRecs.length

    const avgDayForecast = dayStats.avgMW || 1
    const avgBufferRatio = (avgP90 / avgDayForecast) * 100

    return (
      `To hedge against wind generation delivery shortfalls with 90% statistical confidence on ${deliveryDate} ` +
      `(under the ${cutoff} UK cutoff), power buyers should maintain an average operating buffer of ` +
      `${Math.round(avgP90).toLocaleString()} MW (~${avgBufferRatio.toFixed(0)}% of forecasted volume), ` +
      `with peak exposure concentrated during ${maxP90Rec.hourLabel} where historical P90 shortfall risk reaches ` +
      `${Math.round(maxP90Rec.p90BufferMW || 0).toLocaleString()} MW.`
    )
  }, [bufferRecommendations, dayStats, deliveryDate, cutoff])

  // Handlers for quick day navigation using calendar arithmetic (Date.UTC)
  const handleDateOffset = (offsetDays: number) => {
    try {
      const newDateStr = stepDateUtc(deliveryDate, offsetDays)
      if (newDateStr >= datasetBounds.minDate && newDateStr <= datasetBounds.maxDate) {
        setDeliveryDate(newDateStr)
      }
    } catch {
      // Ignored
    }
  }

  // -------------------------------------------------------------------------
  // Render States
  // -------------------------------------------------------------------------
  if (isLoading) {
    return (
      <LoadingState
        message="Loading forecast and buffer recommendations..."
        description={`Evaluating Day D delivery (${deliveryDate}) with Day D-1 cutoff (${cutoff} UK)`}
      />
    )
  }

  if (isError) {
    return (
      <ErrorState
        title="Failed to Load Forecast Decision"
        message={errorMessage}
        onRetry={() => {
          void forecastQuery.refetch()
          void hourlyMetricsQuery.refetch()
        }}
      />
    )
  }

  if (!forecastQuery.data?.data || forecastQuery.data.data.length === 0) {
    return (
      <EmptyState
        title="No Forecast Found"
        description={`No published forecasts prior to ${cutoff} UK were located for ${deliveryDate}.`}
      />
    )
  }

  return (
    <div className="page-wrapper">
      {/* Page Title & Controls Bar */}
      <div className="decision-header-panel card">
        <div className="decision-title-group">
          <h1 className="page-title">Day-Ahead Power Purchase Decision</h1>
          <p className="page-subtitle">
            Physical delivery schedule for <strong>{deliveryDate}</strong> determined at{' '}
            <strong>{cutoff} UK time</strong> on Day D-1. Includes historical P90 error buffers for trading risk mitigation.
          </p>
        </div>

        {/* Dedicated Interactive Controls */}
        <div className="decision-controls-bar">
          <div className="control-field">
            <label htmlFor="decision-date" className="control-label">
              <Calendar size={14} className="control-icon" />
              <span>Delivery Date</span>
            </label>
            <div className="date-nav-wrapper">
              <button
                type="button"
                onClick={() => handleDateOffset(-1)}
                className="step-btn"
                title="Previous Day"
                aria-label="Previous Day"
                disabled={deliveryDate <= datasetBounds.minDate}
              >
                &larr;
              </button>
              <input
                id="decision-date"
                type="date"
                min={datasetBounds.minDate}
                max={datasetBounds.maxDate}
                value={deliveryDate}
                onChange={(e) => setDeliveryDate(e.target.value)}
                className="control-input"
              />
              <button
                type="button"
                onClick={() => handleDateOffset(1)}
                className="step-btn"
                title="Next Day"
                aria-label="Next Day"
                disabled={deliveryDate >= datasetBounds.maxDate}
              >
                &rarr;
              </button>
            </div>
          </div>

          <div className="control-field">
            <label htmlFor="decision-cutoff" className="control-label">
              <Clock size={14} className="control-icon" />
              <span>Cutoff Time (UK Local)</span>
            </label>
            <select
              id="decision-cutoff"
              value={cutoff}
              onChange={(e) => setCutoff(e.target.value)}
              className="control-select"
            >
              <option value="09:00">09:00 UK (Standard Trading Cutoff)</option>
              <option value="12:00">12:00 UK (Midday)</option>
              <option value="17:00">17:00 UK (Evening Peak)</option>
              <option value="23:00">23:00 UK (End of Day D-1)</option>
            </select>
          </div>
        </div>
      </div>

      {/* KPI Cards Row */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-label">Peak Forecast</span>
            <Zap size={18} className="kpi-icon" />
          </div>
          <div className="kpi-value">
            {dayStats.peakMW !== null ? `${Math.round(dayStats.peakMW).toLocaleString()} MW` : '—'}
          </div>
          <div className="kpi-subtext">Maximum generation across 48 settlement periods</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-label">Average Forecast</span>
            <TrendingUp size={18} className="kpi-icon" />
          </div>
          <div className="kpi-value">
            {dayStats.avgMW !== null ? `${Math.round(dayStats.avgMW).toLocaleString()} MW` : '—'}
          </div>
          <div className="kpi-subtext">Average volume across covered periods</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-label">Cutoff Coverage</span>
            <CheckCircle2 size={18} className="kpi-icon text-success" />
          </div>
          <div className="kpi-value">
            {dayStats.validCount} / {dayStats.total}
          </div>
          <div className="kpi-subtext">
            {dayStats.publishedCount} published (:00) + {dayStats.derivedCount} step-hold (:30)
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-label">Applied Decision Cutoff</span>
            <Clock size={18} className="kpi-icon" />
          </div>
          <div className="kpi-value">{cutoff} UK</div>
          <div className="kpi-subtext">Forecast publishTime &le; cutoff on Day D-1</div>
        </div>
      </div>

      {/* --------------------------------------------------------------------- */}
      {/* SECTION 1: Selected Forecast Line Chart (Recharts) */}
      {/* --------------------------------------------------------------------- */}
      <div className="card chart-card">
        <div className="card-header">
          <div>
            <h2 className="card-title">Day-Ahead Wind Forecast Profile (48 Half-Hours)</h2>
            <p className="card-subtitle">
              Selected forecast volume per half hour matching the maximum publishTime prior to cutoff on Day D-1.
            </p>
          </div>
          <div className="chart-legend-indicator">
            <span className="legend-dot legend-dot-cyan" />
            <span className="legend-text">Published (:00)</span>
            <span className="legend-dot legend-dot-derived" />
            <span className="legend-text">Step-Hold Derived (:30)</span>
            {dayStats.missingCount > 0 && (
              <>
                <span className="legend-dot legend-dot-missing" />
                <span className="legend-text">Missing Interval</span>
              </>
            )}
          </div>
        </div>

        {/* Step-Hold Resolution Banner */}
        <div className="missing-notice-banner">
          <Info size={16} className="missing-notice-icon" />
          <span>
            <strong>Hourly Block Step-Hold Active:</strong> Elexon <code>WINDFOR</code> broadcasts forecasts as hourly
            average MW blocks (:00). Intermediate :30 settlement periods inherit the preceding :00 forecast with explicit
            derivation attribution, ensuring full 48-period coverage for day-ahead scheduling.
          </span>
        </div>

        {/* Recharts Line Chart Container */}
        <div className="chart-wrapper">
          <ResponsiveContainer width="100%" height={380}>
            <LineChart
              data={chartData}
              margin={{ top: 20, right: 30, left: 15, bottom: 25 }}
            >
              <defs>
                <linearGradient id="lineGlow" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#06b6d4" />
                  <stop offset="50%" stopColor="#38bdf8" />
                  <stop offset="100%" stopColor="#0284c7" />
                </linearGradient>
              </defs>

              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(255, 255, 255, 0.08)"
                vertical={false}
              />

              <XAxis
                dataKey="timeLabel"
                stroke="#64748b"
                tick={{ fill: '#94a3b8', fontSize: 11, fontFamily: 'var(--font-mono)' }}
                interval={3}
                tickLine={{ stroke: 'rgba(255, 255, 255, 0.15)' }}
                dy={8}
              />

              <YAxis
                stroke="#64748b"
                tick={{ fill: '#94a3b8', fontSize: 11, fontFamily: 'var(--font-mono)' }}
                tickFormatter={(val: number) => `${Math.round(val).toLocaleString()} MW`}
                tickLine={{ stroke: 'rgba(255, 255, 255, 0.15)' }}
                dx={-5}
              />

              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length > 0) {
                    const d = payload[0].payload as ChartDataPoint
                    return (
                      <div className="custom-chart-tooltip">
                        <div className="tooltip-header">
                          <span className="tooltip-sp">Settlement Period {d.sp}</span>
                          <span className="tooltip-time">{d.fullInterval} (UK)</span>
                        </div>
                        <div className="tooltip-body">
                          {d.isMissing ? (
                            <div className="tooltip-missing-alert">
                              <AlertTriangle size={14} className="text-warning" />
                              <span>Missing: No forecast published prior to cutoff</span>
                            </div>
                          ) : (
                            <>
                              <div className="tooltip-metric">
                                <span className="tooltip-label">Forecast Generation:</span>
                                <span className="tooltip-val font-mono font-bold text-cyan">
                                  {d.generation?.toLocaleString()} MW
                                </span>
                              </div>
                              <div className="tooltip-meta">
                                <span className="tooltip-label">Forecast Source:</span>
                                <span
                                  className="tooltip-val font-mono font-semibold"
                                  style={{ color: d.isDerived ? '#c084fc' : '#38bdf8' }}
                                >
                                  {d.isDerived
                                    ? 'Step-Hold Derived (:00 Block)'
                                    : 'Published WINDFOR Run'}
                                </span>
                              </div>
                              <div className="tooltip-meta">
                                <span className="tooltip-label">Selected Publication Run:</span>
                                <span className="tooltip-val font-mono text-muted">
                                  {d.publishTimeDisplay}
                                </span>
                              </div>
                              <div className="tooltip-meta">
                                <span className="tooltip-label">Lead Time Horizon:</span>
                                <span className="tooltip-val font-mono text-muted">
                                  {d.horizonHoursDisplay}
                                </span>
                              </div>
                            </>
                          )}
                        </div>
                      </div>
                    )
                  }
                  return null
                }}
              />

              <Legend verticalAlign="top" height={36} wrapperStyle={{ display: 'none' }} />

              <Line
                type="monotone"
                dataKey="generation"
                name="Selected Forecast (MW)"
                stroke="url(#lineGlow)"
                strokeWidth={3}
                connectNulls={false}
                dot={(props: { cx?: number; cy?: number; payload?: ChartDataPoint }) => {
                  const { cx, cy, payload } = props
                  if (!cx || !cy || !payload) return null
                  if (payload.isMissing) return null
                  const isDerived = payload.isDerived
                  return (
                    <circle
                      key={`dot-${payload.sp}`}
                      cx={cx}
                      cy={cy}
                      r={isDerived ? 3.5 : 4.5}
                      fill={isDerived ? '#a855f7' : '#090d16'}
                      stroke={isDerived ? '#c084fc' : '#06b6d4'}
                      strokeWidth={2}
                    />
                  )
                }}
                activeDot={{
                  r: 6,
                  fill: '#06b6d4',
                  stroke: '#fff',
                  strokeWidth: 2,
                }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* --------------------------------------------------------------------- */}
      {/* SECTION 2: Plain English Power Buyer Summary Callout Box */}
      {/* --------------------------------------------------------------------- */}
      <div className="buyer-summary-callout">
        <div className="summary-icon-box">
          <ShieldAlert size={28} className="summary-icon" />
        </div>
        <div className="summary-text-content">
          <div className="summary-badge">Executive Takeaway for Power Buyer</div>
          <p className="summary-statement">{buyerSummarySentence}</p>
        </div>
      </div>

      {/* --------------------------------------------------------------------- */}
      {/* SECTION 3: Buffer Recommendations Table (by Hour of Day) */}
      {/* --------------------------------------------------------------------- */}
      <div className="card table-card">
        <div className="card-header">
          <div>
            <h2 className="card-title">
              <ShieldCheck size={18} className="section-header-icon text-cyan" />
              <span>Hourly Procurement Buffer Recommendations (Historical P90 Error)</span>
            </h2>
            <p className="card-subtitle">
              Calculated from the 90th percentile absolute error for each hour of day during January 2026.
              Provides the recommended safety buffer volume to avoid Balancing Mechanism (BM) cashout penalties.
            </p>
          </div>
          <div className="badge badge-info">24 Hourly Intervals</div>
        </div>

        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: '120px' }}>Hour (UK)</th>
                <th className="text-right">Day-Ahead Forecast</th>
                <th className="text-right">P90 Buffer Required</th>
                <th className="text-right">Hedged Volume</th>
                <th className="text-right">Buffer Ratio</th>
                <th style={{ width: '130px' }} className="text-center">Risk Level</th>
              </tr>
            </thead>
            <tbody>
              {bufferRecommendations.map((row) => {
                return (
                  <tr key={row.hour}>
                    <td className="font-mono font-semibold">{row.hourLabel}</td>
                    <td className="text-right font-mono font-medium">
                      {row.forecastAvgMW !== null
                        ? `${Math.round(row.forecastAvgMW).toLocaleString()} MW`
                        : '—'}
                    </td>
                    <td className="text-right font-mono font-bold text-cyan">
                      {row.p90BufferMW !== null
                        ? `${Math.round(row.p90BufferMW).toLocaleString()} MW`
                        : '—'}
                    </td>
                    <td className="text-right font-mono text-muted">
                      {row.hedgedVolumeMW !== null
                        ? `${Math.round(row.hedgedVolumeMW).toLocaleString()} MW`
                        : '—'}
                    </td>
                    <td className="text-right font-mono">
                      {row.bufferRatioPct !== null
                        ? `${row.bufferRatioPct.toFixed(1)}%`
                        : '—'}
                    </td>
                    <td className="text-center">
                      {row.riskLevel === 'Low' && (
                        <span className="badge badge-success">
                          <span>Low Risk</span>
                        </span>
                      )}
                      {row.riskLevel === 'Moderate' && (
                        <span className="badge badge-warning">
                          <span>Moderate</span>
                        </span>
                      )}
                      {row.riskLevel === 'Elevated' && (
                        <span className="badge badge-error">
                          <span>Elevated</span>
                        </span>
                      )}
                      {row.riskLevel === 'Unknown' && (
                        <span className="badge badge-info">
                          <span>N/A</span>
                        </span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        <div className="card-footer">
          <div className="card-footer-note">
            <HelpCircle size={14} />
            <span>
              <strong>Methodology:</strong> P90 absolute error represents the error threshold that covers 90% of observed historical outcomes for that hour of day.
              If a buyer procures <em>Forecast &minus; Buffer</em> (hedged volume), their physical exposure to negative imbalances (where actual delivery falls short of contracted volume)
              is held below 10% probability under normal market operations.
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
