import React, { useMemo } from 'react'
import {
  Bar,
  BarChart,
  Brush,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  BarChart2,
  Calendar,
  Clock,
  Info,
  Layers,
  Percent,
  RefreshCw,
  TrendingUp,
  Zap,
} from 'lucide-react'
import { EmptyState } from '../components/common/EmptyState'
import { ErrorState } from '../components/common/ErrorState'
import { LoadingState } from '../components/common/LoadingState'
import { useFilters } from '../context'
import {
  useCompare,
  useHorizonMetrics,
  useHourlyMetrics,
  useOverallMetrics,
} from '../hooks/useQueries'
import type { CompareItem } from '../types/api'
import {
  calculateHistogramBins,
  getForecastVsActualTakeaway,
  getHistogramTakeaway,
  getHorizonTakeaway,
  getHourlyTakeaway,
  type HistogramBin,
} from '../utils/accuracyAnalytics'

interface TimeSeriesPoint {
  index: number
  dateStr: string
  timeStr: string
  timeLabel: string
  fullDateTime: string
  actual: number | null
  forecast: number | null
  error: number | null
  absError: number | null
}

export const AccuracyPage: React.FC = () => {
  const {
    startDate,
    endDate,
    cutoff,
    setStartDate,
    setEndDate,
    setCutoff,
    setDateRange,
  } = useFilters()

  // 1. Fetch Overall Benchmark Metrics
  const overallQuery = useOverallMetrics(startDate, endDate, cutoff)

  // 2. Fetch Full Half-Hourly Actual vs Forecast Series (up to ~1,500 points)
  const compareQuery = useCompare(startDate, endDate, cutoff)

  // 3. Fetch Diurnal Metrics by Hour of Day (24 hours)
  const hourlyQuery = useHourlyMetrics(startDate, endDate, cutoff)

  // 4. Fetch Metrics by Lead Time Horizon
  const horizonQuery = useHorizonMetrics(startDate, endDate)

  const isLoading =
    overallQuery.isLoading ||
    compareQuery.isLoading ||
    hourlyQuery.isLoading ||
    horizonQuery.isLoading

  const isError =
    overallQuery.isError ||
    compareQuery.isError ||
    hourlyQuery.isError ||
    horizonQuery.isError

  const errorMessage =
    overallQuery.error?.message ||
    compareQuery.error?.message ||
    hourlyQuery.error?.message ||
    horizonQuery.error?.message ||
    'Failed to evaluate forecast accuracy metrics.'

  const handleRetryAll = () => {
    void overallQuery.refetch()
    void compareQuery.refetch()
    void hourlyQuery.refetch()
    void horizonQuery.refetch()
  }

  // -------------------------------------------------------------------------
  // Memoized: Time-Series Line Chart Data (Forecast vs Actual with Brush)
  // -------------------------------------------------------------------------
  const timeSeriesData: TimeSeriesPoint[] = useMemo(() => {
    if (!compareQuery.data?.data) return []

    return compareQuery.data.data.map((item: CompareItem, idx: number) => {
      const dt = new Date(item.startTime)
      const dateStr = dt.toISOString().split('T')[0]
      const timeStr = dt.toLocaleTimeString('en-GB', {
        timeZone: 'Europe/London',
        hour: '2-digit',
        minute: '2-digit',
      })

      // Show formatted label like "02 Jan 09:30"
      const dayMonth = dt.toLocaleDateString('en-GB', {
        timeZone: 'Europe/London',
        day: '2-digit',
        month: 'short',
      })
      const timeLabel = `${dayMonth} ${timeStr}`

      return {
        index: idx,
        dateStr,
        timeStr,
        timeLabel,
        fullDateTime: `${dateStr} ${timeStr} UK`,
        actual:
          item.actualGeneration !== null
            ? Math.round(item.actualGeneration * 10) / 10
            : null,
        forecast:
          item.forecastGeneration !== null
            ? Math.round(item.forecastGeneration * 10) / 10
            : null,
        error:
          item.error !== null ? Math.round(item.error * 10) / 10 : null,
        absError:
          item.absError !== null ? Math.round(item.absError * 10) / 10 : null,
      }
    })
  }, [compareQuery.data])

  // -------------------------------------------------------------------------
  // Memoized: Error Histogram Bins
  // -------------------------------------------------------------------------
  const { histogramData, histogramStats } = useMemo(() => {
    const errorList = compareQuery.data?.data?.map((item) => item.error) ?? []
    return calculateHistogramBins(errorList, 16)
  }, [compareQuery.data])

  // -------------------------------------------------------------------------
  // Memoized: Diurnal Hourly Chart Data
  // -------------------------------------------------------------------------
  const hourlyChartData = useMemo(() => {
    if (!hourlyQuery.data?.data) return []

    return hourlyQuery.data.data.map((row) => {
      const hourLabel = `${String(row.hour).padStart(2, '0')}:00`
      return {
        hour: row.hour,
        hourLabel,
        mae: row.mae !== null ? Math.round(row.mae * 10) / 10 : 0,
        rmse: row.rmse !== null ? Math.round(row.rmse * 10) / 10 : 0,
        bias: row.bias !== null ? Math.round(row.bias * 10) / 10 : 0,
        p90: row.p90 !== null ? Math.round(row.p90 * 10) / 10 : 0,
        meanActual: row.mean_actual !== null ? Math.round(row.mean_actual) : 0,
        meanForecast:
          row.mean_forecast !== null ? Math.round(row.mean_forecast) : 0,
        validCount: row.valid_count,
      }
    })
  }, [hourlyQuery.data])

  // -------------------------------------------------------------------------
  // Memoized: Horizon Chart Data
  // -------------------------------------------------------------------------
  const horizonChartData = useMemo(() => {
    if (!horizonQuery.data?.data) return []

    return horizonQuery.data.data.map((b) => ({
      bucket: b.bucket,
      mae: b.mae !== null ? Math.round(b.mae * 10) / 10 : 0,
      rmse: b.rmse !== null ? Math.round(b.rmse * 10) / 10 : 0,
      bias: b.bias !== null ? Math.round(b.bias * 10) / 10 : 0,
      p90: b.p90 !== null ? Math.round(b.p90 * 10) / 10 : 0,
      validCount: b.valid_count,
      totalCount: b.total_count,
    }))
  }, [horizonQuery.data])

  // -------------------------------------------------------------------------
  // Dynamic Takeaway Sentences Generated from Empirical Data
  // -------------------------------------------------------------------------
  const overallMetrics = overallQuery.data?.metrics

  const forecastVsActualTakeaway = useMemo(
    () => getForecastVsActualTakeaway(overallMetrics),
    [overallMetrics]
  )

  const histogramTakeaway = useMemo(
    () => getHistogramTakeaway(histogramStats),
    [histogramStats]
  )

  const hourlyTakeaway = useMemo(
    () => getHourlyTakeaway(hourlyChartData),
    [hourlyChartData]
  )

  const horizonTakeaway = useMemo(
    () => getHorizonTakeaway(horizonChartData),
    [horizonChartData]
  )

  // -------------------------------------------------------------------------
  // Render Loading & Error States
  // -------------------------------------------------------------------------
  if (isLoading) {
    return (
      <LoadingState
        message="Computing comprehensive accuracy benchmarks..."
        description={`Analyzing 1,500+ intervals across ${startDate} to ${endDate} at cutoff ${cutoff}`}
      />
    )
  }

  if (isError) {
    return (
      <ErrorState
        title="Accuracy Benchmark Error"
        message={errorMessage}
        onRetry={handleRetryAll}
      />
    )
  }

  if (!overallMetrics || overallMetrics.total_count === 0) {
    return (
      <EmptyState
        title="No Benchmark Data Found"
        description={`No evaluation intervals found between ${startDate} and ${endDate}.`}
      />
    )
  }

  return (
    <div className="page-wrapper">
      {/* --------------------------------------------------------------------- */}
      {/* Control Header & Range Selector */}
      {/* --------------------------------------------------------------------- */}
      <div className="decision-header-panel card">
        <div className="decision-title-group">
          <h1 className="page-title">Forecast Accuracy Benchmark</h1>
          <p className="page-subtitle">
            Statistical evaluation of Elexon <code>WINDFOR</code> forecasts versus metered actuals (
            <code>FUELHH WIND</code>) for delivery between <strong>{startDate}</strong> and{' '}
            <strong>{endDate}</strong> with decision cutoff <strong>{cutoff} UK</strong> on Day D-1.
          </p>
        </div>

        <div className="decision-controls-bar">
          <div className="control-field">
            <label htmlFor="accuracy-start" className="control-label">
              <Calendar size={14} className="control-icon" />
              <span>Start Date</span>
            </label>
            <input
              id="accuracy-start"
              type="date"
              min="2026-01-01"
              max="2026-02-02"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="control-input"
            />
          </div>

          <div className="control-field">
            <label htmlFor="accuracy-end" className="control-label">
              <Calendar size={14} className="control-icon" />
              <span>End Date</span>
            </label>
            <input
              id="accuracy-end"
              type="date"
              min="2026-01-01"
              max="2026-02-02"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="control-input"
            />
          </div>

          <div className="control-field">
            <label htmlFor="accuracy-cutoff" className="control-label">
              <Clock size={14} className="control-icon" />
              <span>Cutoff Time</span>
            </label>
            <select
              id="accuracy-cutoff"
              value={cutoff}
              onChange={(e) => setCutoff(e.target.value)}
              className="control-select"
            >
              <option value="09:00">09:00 UK (Standard)</option>
              <option value="12:00">12:00 UK (Midday)</option>
              <option value="17:00">17:00 UK (Evening Peak)</option>
              <option value="23:00">23:00 UK (End of Day D-1)</option>
            </select>
          </div>

          <div className="filter-actions" style={{ alignSelf: 'flex-end' }}>
            <button
              type="button"
              onClick={() => setDateRange('2026-01-02', '2026-02-01')}
              className="preset-btn"
              title="Full evaluated month (Jan 2 - Feb 1)"
            >
              <span>Full Jan</span>
            </button>
            <button
              type="button"
              onClick={handleRetryAll}
              className="preset-btn"
              title="Refresh all metrics"
            >
              <RefreshCw size={13} />
            </button>
          </div>
        </div>
      </div>

      {/* --------------------------------------------------------------------- */}
      {/* SECTION 1: Metric Cards (MAE, RMSE, Bias, nMAE, P90) */}
      {/* --------------------------------------------------------------------- */}
      <div className="kpi-grid">
        {/* MAE */}
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-label">Mean Absolute Error (MAE)</span>
            <Activity size={18} className="kpi-icon" />
          </div>
          <div className="kpi-value text-cyan">
            {overallMetrics.mae !== null
              ? `${Math.round(overallMetrics.mae).toLocaleString()} MW`
              : '—'}
          </div>
          <div className="kpi-subtext">Average absolute deviation per half-hour</div>
        </div>

        {/* RMSE */}
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-label">Root Mean Square Error (RMSE)</span>
            <BarChart2 size={18} className="kpi-icon" />
          </div>
          <div className="kpi-value">
            {overallMetrics.rmse !== null
              ? `${Math.round(overallMetrics.rmse).toLocaleString()} MW`
              : '—'}
          </div>
          <div className="kpi-subtext">Heavily penalizes extreme forecast errors</div>
        </div>

        {/* Bias */}
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-label">Forecast Bias (Mean Error)</span>
            {overallMetrics.bias !== null && overallMetrics.bias >= 0 ? (
              <ArrowUpRight size={18} className="kpi-icon text-success" />
            ) : (
              <ArrowDownRight size={18} className="kpi-icon text-warning" />
            )}
          </div>
          <div
            className={`kpi-value ${
              overallMetrics.bias !== null && overallMetrics.bias >= 0
                ? 'text-success'
                : 'text-warning'
            }`}
          >
            {overallMetrics.bias !== null
              ? `${overallMetrics.bias >= 0 ? '+' : ''}${Math.round(overallMetrics.bias).toLocaleString()} MW`
              : '—'}
          </div>
          <div className="kpi-subtext">
            {overallMetrics.bias !== null && overallMetrics.bias < 0
              ? 'Over-predicting (Actual < Forecast)'
              : 'Under-predicting (Actual > Forecast)'}
          </div>
        </div>

        {/* Normalised MAE */}
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-label">Normalised MAE (nMAE)</span>
            <Percent size={18} className="kpi-icon" />
          </div>
          <div className="kpi-value text-cyan">
            {overallMetrics.nmae_pct !== null
              ? `${overallMetrics.nmae_pct.toFixed(1)}%`
              : '—'}
          </div>
          <div className="kpi-subtext">MAE relative to average actual generation</div>
        </div>

        {/* P90 Error */}
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-label">P90 Absolute Error</span>
            <Zap size={18} className="kpi-icon" />
          </div>
          <div className="kpi-value">
            {overallMetrics.p90 !== null
              ? `${Math.round(overallMetrics.p90).toLocaleString()} MW`
              : '—'}
          </div>
          <div className="kpi-subtext">90% of error magnitudes fall below this threshold</div>
        </div>
      </div>

      {/* Secondary Context Metrics Strip */}
      <div className="kpi-grid secondary-kpis">
        <div className="kpi-card mini-card">
          <span className="kpi-label">P50 (Median Absolute Error)</span>
          <div className="kpi-value-sm">
            {overallMetrics.p50 !== null
              ? `${Math.round(overallMetrics.p50).toLocaleString()} MW`
              : '—'}
          </div>
        </div>
        <div className="kpi-card mini-card">
          <span className="kpi-label">P95 Absolute Error</span>
          <div className="kpi-value-sm">
            {overallMetrics.p95 !== null
              ? `${Math.round(overallMetrics.p95).toLocaleString()} MW`
              : '—'}
          </div>
        </div>
        <div className="kpi-card mini-card">
          <span className="kpi-label">Mean Actual Generation</span>
          <div className="kpi-value-sm">
            {overallMetrics.mean_actual !== null
              ? `${Math.round(overallMetrics.mean_actual).toLocaleString()} MW`
              : '—'}
          </div>
        </div>
        <div className="kpi-card mini-card">
          <span className="kpi-label">Mean Forecast Generation</span>
          <div className="kpi-value-sm">
            {overallMetrics.mean_forecast !== null
              ? `${Math.round(overallMetrics.mean_forecast).toLocaleString()} MW`
              : '—'}
          </div>
        </div>
        <div className="kpi-card mini-card">
          <span className="kpi-label">Evaluated Coverage</span>
          <div className="kpi-value-sm">
            {overallMetrics.valid_count.toLocaleString()} / {overallMetrics.total_count.toLocaleString()}
          </div>
        </div>
      </div>

      {/* --------------------------------------------------------------------- */}
      {/* CHART 1: Forecast versus Actual Time-Series Line Chart with Brush */}
      {/* --------------------------------------------------------------------- */}
      <div className="card chart-card">
        <div className="card-header">
          <div>
            <h2 className="card-title">
              <TrendingUp size={18} className="section-header-icon" />
              <span>Forecast versus Actual Generation (Full Time-Series with Interactive Zoom)</span>
            </h2>
            <p className="card-subtitle">
              Evaluating all {timeSeriesData.length.toLocaleString()} half-hour settlement periods across {startDate} to {endDate}.
              Drag the brush handles below to zoom into specific days or ramp events.
            </p>
          </div>
          <div className="chart-legend-indicator">
            <span className="legend-dot" style={{ backgroundColor: '#10b981' }} />
            <span className="legend-text">Actual Metered Outturn</span>
            <span className="legend-dot legend-dot-cyan" />
            <span className="legend-text">Selected Forecast</span>
          </div>
        </div>

        <div className="chart-wrapper">
          <ResponsiveContainer width="100%" height={380}>
            <LineChart
              data={timeSeriesData}
              margin={{ top: 15, right: 30, left: 15, bottom: 10 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(255, 255, 255, 0.08)"
                vertical={false}
              />
              <XAxis
                dataKey="timeLabel"
                stroke="#64748b"
                tick={{ fill: '#94a3b8', fontSize: 11, fontFamily: 'var(--font-mono)' }}
                interval={Math.floor(timeSeriesData.length / 10)}
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
                    const d = payload[0].payload as TimeSeriesPoint
                    return (
                      <div className="custom-chart-tooltip">
                        <div className="tooltip-header">
                          <span className="tooltip-sp">Period #{d.index + 1}</span>
                          <span className="tooltip-time">{d.fullDateTime}</span>
                        </div>
                        <div className="tooltip-body">
                          <div className="tooltip-metric">
                            <span className="tooltip-label" style={{ color: '#10b981' }}>
                              Actual Metered:
                            </span>
                            <span className="tooltip-val font-mono font-bold text-success">
                              {d.actual !== null ? `${d.actual.toLocaleString()} MW` : '—'}
                            </span>
                          </div>
                          <div className="tooltip-metric">
                            <span className="tooltip-label" style={{ color: '#06b6d4' }}>
                              Selected Forecast:
                            </span>
                            <span className="tooltip-val font-mono font-bold text-cyan">
                              {d.forecast !== null ? `${d.forecast.toLocaleString()} MW` : 'Missing (:30)'}
                            </span>
                          </div>
                          {d.error !== null && (
                            <div className="tooltip-meta">
                              <span className="tooltip-label">Error (Actual &minus; Forecast):</span>
                              <span
                                className={`tooltip-val font-mono font-bold ${
                                  d.error >= 0 ? 'text-success' : 'text-warning'
                                }`}
                              >
                                {d.error >= 0 ? '+' : ''}{d.error.toLocaleString()} MW
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  }
                  return null
                }}
              />
              <Legend verticalAlign="top" height={36} wrapperStyle={{ display: 'none' }} />

              {/* Actual generation line */}
              <Line
                type="monotone"
                dataKey="actual"
                name="Actual Generation (MW)"
                stroke="#10b981"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />

              {/* Forecast line (connectNulls=false to show missing :30 gaps) */}
              <Line
                type="monotone"
                dataKey="forecast"
                name="Selected Forecast (MW)"
                stroke="#06b6d4"
                strokeWidth={2}
                connectNulls={false}
                dot={false}
                isAnimationActive={false}
              />

              {/* Zooming / Panning Brush */}
              <Brush
                dataKey="timeLabel"
                height={34}
                stroke="#06b6d4"
                fill="#0f172a"
                tickFormatter={(val: string) => val.split(' ')[0]}
                travellerWidth={10}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* One line dynamic takeaway */}
        <div className="chart-takeaway-bar">
          <Info size={15} className="takeaway-icon text-cyan" />
          <span className="takeaway-text">
            <strong>Key Takeaway:</strong> {forecastVsActualTakeaway}
          </span>
        </div>
      </div>

      {/* --------------------------------------------------------------------- */}
      {/* SECTION 2: Error Distribution Histogram */}
      {/* --------------------------------------------------------------------- */}
      <div className="card chart-card">
        <div className="card-header">
          <div>
            <h2 className="card-title">
              <BarChart2 size={18} className="section-header-icon" />
              <span>Error Distribution Profile (Actual &minus; Forecast)</span>
            </h2>
            <p className="card-subtitle">
              Frequency distribution of forecast errors. Negative values indicate over-forecasting (actual shortfall);
              positive values indicate under-forecasting (actual surplus).
            </p>
          </div>
          <div className="badge badge-info">{histogramStats.totalValid.toLocaleString()} Sample Intervals</div>
        </div>

        <div className="chart-wrapper">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart
              data={histogramData}
              margin={{ top: 15, right: 30, left: 15, bottom: 25 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(255, 255, 255, 0.08)"
                vertical={false}
              />
              <XAxis
                dataKey="binLabel"
                stroke="#64748b"
                tick={{ fill: '#94a3b8', fontSize: 10, fontFamily: 'var(--font-mono)' }}
                interval={1}
                angle={-25}
                textAnchor="end"
                dy={6}
              />
              <YAxis
                stroke="#64748b"
                tick={{ fill: '#94a3b8', fontSize: 11, fontFamily: 'var(--font-mono)' }}
                tickFormatter={(val: number) => val.toLocaleString()}
                dx={-5}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length > 0) {
                    const b = payload[0].payload as HistogramBin
                    const pct =
                      histogramStats.totalValid > 0
                        ? ((b.count / histogramStats.totalValid) * 100).toFixed(1)
                        : '0.0'
                    return (
                      <div className="custom-chart-tooltip">
                        <div className="tooltip-header">
                          <span className="tooltip-sp">Error Bucket</span>
                          <span className="tooltip-time">{b.binLabel} MW</span>
                        </div>
                        <div className="tooltip-body">
                          <div className="tooltip-metric">
                            <span className="tooltip-label">Settlement Intervals:</span>
                            <span className="tooltip-val font-mono font-bold text-cyan">
                              {b.count.toLocaleString()} periods ({pct}%)
                            </span>
                          </div>
                          <div className="tooltip-meta">
                            <span className="tooltip-label">Trading Implication:</span>
                            <span
                              className={`tooltip-val font-semibold ${
                                b.isNegative ? 'text-warning' : 'text-success'
                              }`}
                            >
                              {b.isNegative
                                ? 'Over-Forecast (Downside Shortfall)'
                                : 'Under-Forecast (Surplus Outturn)'}
                            </span>
                          </div>
                        </div>
                      </div>
                    )
                  }
                  return null
                }}
              />
              <ReferenceLine x={0} stroke="#94a3b8" strokeDasharray="3 3" />
              <Bar dataKey="count" name="Frequency Count" radius={[4, 4, 0, 0]}>
                {histogramData.map((entry) => (
                  <Cell
                    key={`bar-${entry.binIndex}`}
                    fill={entry.isNegative ? '#f59e0b' : '#06b6d4'}
                    opacity={0.85}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* One line dynamic takeaway */}
        <div className="chart-takeaway-bar">
          <Info size={15} className="takeaway-icon text-cyan" />
          <span className="takeaway-text">
            <strong>Key Takeaway:</strong> {histogramTakeaway}
          </span>
        </div>
      </div>

      {/* --------------------------------------------------------------------- */}
      {/* SECTION 3: Error by Hour of Day Bar Chart */}
      {/* --------------------------------------------------------------------- */}
      <div className="card chart-card">
        <div className="card-header">
          <div>
            <h2 className="card-title">
              <Clock size={18} className="section-header-icon" />
              <span>Diurnal Error Breakdown by Hour of Day (UK Local Time)</span>
            </h2>
            <p className="card-subtitle">
              MAE and P90 absolute error grouped into 24 hour buckets across the selected delivery dates.
            </p>
          </div>
          <div className="chart-legend-indicator">
            <span className="legend-dot legend-dot-cyan" />
            <span className="legend-text">Mean Absolute Error (MAE)</span>
            <span className="legend-dot" style={{ backgroundColor: '#38bdf8' }} />
            <span className="legend-text">P90 Error Buffer</span>
          </div>
        </div>

        <div className="chart-wrapper">
          <ResponsiveContainer width="100%" height={320}>
            <BarChart
              data={hourlyChartData}
              margin={{ top: 15, right: 30, left: 15, bottom: 15 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(255, 255, 255, 0.08)"
                vertical={false}
              />
              <XAxis
                dataKey="hourLabel"
                stroke="#64748b"
                tick={{ fill: '#94a3b8', fontSize: 11, fontFamily: 'var(--font-mono)' }}
                interval={1}
                dy={6}
              />
              <YAxis
                stroke="#64748b"
                tick={{ fill: '#94a3b8', fontSize: 11, fontFamily: 'var(--font-mono)' }}
                tickFormatter={(val: number) => `${Math.round(val).toLocaleString()} MW`}
                dx={-5}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length > 0) {
                    const row = payload[0].payload
                    return (
                      <div className="custom-chart-tooltip">
                        <div className="tooltip-header">
                          <span className="tooltip-sp">Hour {row.hourLabel}</span>
                          <span className="tooltip-time">UK Local Time</span>
                        </div>
                        <div className="tooltip-body">
                          <div className="tooltip-metric">
                            <span className="tooltip-label">Mean Absolute Error:</span>
                            <span className="tooltip-val font-mono font-bold text-cyan">
                              {row.mae.toLocaleString()} MW
                            </span>
                          </div>
                          <div className="tooltip-metric">
                            <span className="tooltip-label">P90 Error Buffer:</span>
                            <span className="tooltip-val font-mono font-bold text-accent">
                              {row.p90.toLocaleString()} MW
                            </span>
                          </div>
                          <div className="tooltip-meta">
                            <span className="tooltip-label">Forecast Bias:</span>
                            <span
                              className={`tooltip-val font-mono ${
                                row.bias >= 0 ? 'text-success' : 'text-warning'
                              }`}
                            >
                              {row.bias >= 0 ? '+' : ''}{row.bias.toLocaleString()} MW
                            </span>
                          </div>
                          <div className="tooltip-meta">
                            <span className="tooltip-label">Mean Actual vs Forecast:</span>
                            <span className="tooltip-val font-mono text-muted">
                              {row.meanActual.toLocaleString()} / {row.meanForecast.toLocaleString()} MW
                            </span>
                          </div>
                        </div>
                      </div>
                    )
                  }
                  return null
                }}
              />
              <Bar dataKey="mae" name="MAE (MW)" fill="#06b6d4" radius={[4, 4, 0, 0]} />
              <Bar dataKey="p90" name="P90 (MW)" fill="#0284c7" radius={[4, 4, 0, 0]} opacity={0.65} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* One line dynamic takeaway */}
        <div className="chart-takeaway-bar">
          <Info size={15} className="takeaway-icon text-cyan" />
          <span className="takeaway-text">
            <strong>Key Takeaway:</strong> {hourlyTakeaway}
          </span>
        </div>
      </div>

      {/* --------------------------------------------------------------------- */}
      {/* SECTION 4: Error by Forecast Horizon Chart */}
      {/* --------------------------------------------------------------------- */}
      <div className="card chart-card">
        <div className="card-header">
          <div>
            <h2 className="card-title">
              <Layers size={18} className="section-header-icon" />
              <span>Forecast Degradation by Lead Time Horizon</span>
            </h2>
            <p className="card-subtitle">
              Evaluating accuracy decay as the lead time (hours between forecast run publishTime and settlement startTime) expands.
            </p>
          </div>
          <div className="chart-legend-indicator">
            <span className="legend-dot legend-dot-cyan" />
            <span className="legend-text">MAE</span>
            <span className="legend-dot" style={{ backgroundColor: '#8b5cf6' }} />
            <span className="legend-text">RMSE</span>
            <span className="legend-dot" style={{ backgroundColor: '#0284c7' }} />
            <span className="legend-text">P90</span>
          </div>
        </div>

        <div className="chart-wrapper">
          <ResponsiveContainer width="100%" height={320}>
            <BarChart
              data={horizonChartData}
              margin={{ top: 15, right: 30, left: 15, bottom: 15 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(255, 255, 255, 0.08)"
                vertical={false}
              />
              <XAxis
                dataKey="bucket"
                stroke="#64748b"
                tick={{ fill: '#94a3b8', fontSize: 11, fontFamily: 'var(--font-mono)' }}
                dy={6}
              />
              <YAxis
                stroke="#64748b"
                tick={{ fill: '#94a3b8', fontSize: 11, fontFamily: 'var(--font-mono)' }}
                tickFormatter={(val: number) => `${Math.round(val).toLocaleString()} MW`}
                dx={-5}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length > 0) {
                    const row = payload[0].payload
                    return (
                      <div className="custom-chart-tooltip">
                        <div className="tooltip-header">
                          <span className="tooltip-sp">Lead Horizon</span>
                          <span className="tooltip-time">{row.bucket}</span>
                        </div>
                        <div className="tooltip-body">
                          <div className="tooltip-metric">
                            <span className="tooltip-label">Mean Absolute Error (MAE):</span>
                            <span className="tooltip-val font-mono font-bold text-cyan">
                              {row.mae.toLocaleString()} MW
                            </span>
                          </div>
                          <div className="tooltip-metric">
                            <span className="tooltip-label">Root Mean Square Error:</span>
                            <span className="tooltip-val font-mono font-bold" style={{ color: '#a78bfa' }}>
                              {row.rmse.toLocaleString()} MW
                            </span>
                          </div>
                          <div className="tooltip-metric">
                            <span className="tooltip-label">P90 Error Buffer:</span>
                            <span className="tooltip-val font-mono font-bold text-accent">
                              {row.p90.toLocaleString()} MW
                            </span>
                          </div>
                          <div className="tooltip-meta">
                            <span className="tooltip-label">Evaluated Forecast Runs:</span>
                            <span className="tooltip-val font-mono text-muted">
                              {row.validCount.toLocaleString()} / {row.totalCount.toLocaleString()}
                            </span>
                          </div>
                        </div>
                      </div>
                    )
                  }
                  return null
                }}
              />
              <Bar dataKey="mae" name="MAE" fill="#06b6d4" radius={[4, 4, 0, 0]} />
              <Bar dataKey="rmse" name="RMSE" fill="#8b5cf6" radius={[4, 4, 0, 0]} opacity={0.7} />
              <Bar dataKey="p90" name="P90" fill="#0284c7" radius={[4, 4, 0, 0]} opacity={0.5} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* One line dynamic takeaway */}
        <div className="chart-takeaway-bar">
          <Info size={15} className="takeaway-icon text-cyan" />
          <span className="takeaway-text">
            <strong>Key Takeaway:</strong> {horizonTakeaway}
          </span>
        </div>
      </div>
    </div>
  )
}
