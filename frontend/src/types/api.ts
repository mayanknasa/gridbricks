/**
 * TypeScript types mirroring FastAPI Pydantic response models.
 */

export interface HealthStatus {
  status: string
  version: string
  timestamp: string
}

export type ForecastType = 'published' | 'step_hold' | 'missing'

export interface ForecastItem {
  startTime: string
  publishTime: string | null
  generation: number | null
  isMissing: boolean
  isDerived: boolean
  forecastType: ForecastType
}

export interface ForecastResponse {
  deliveryDate: string
  cutoff: string
  totalPeriods: number
  data: ForecastItem[]
}

export interface CompareItem {
  startTime: string
  publishTime: string | null
  forecastGeneration: number | null
  actualGeneration: number | null
  error: number | null
  absError: number | null
  isMissing: boolean
  isDerived?: boolean
  forecastType?: ForecastType
}

export interface CompareResponse {
  startDate: string
  endDate: string
  cutoff: string
  totalPeriods: number
  data: CompareItem[]
}

export interface OverallMetrics {
  total_count: number
  valid_count: number
  missing_count: number
  mae: number | null
  rmse: number | null
  bias: number | null
  nmae_pct: number | null
  p50: number | null
  p90: number | null
  p95: number | null
  mean_actual: number | null
  mean_forecast: number | null
}

export interface OverallMetricsResponse {
  startDate: string
  endDate: string
  cutoff: string
  metrics: OverallMetrics
}

export interface HourlyMetrics {
  hour: number
  total_count: number
  valid_count: number
  missing_count: number
  mae: number | null
  rmse: number | null
  bias: number | null
  p50: number | null
  p90: number | null
  p95: number | null
  mean_actual: number | null
  mean_forecast: number | null
}

export interface HourlyMetricsResponse {
  startDate: string
  endDate: string
  cutoff: string
  data: HourlyMetrics[]
}

export interface HorizonMetrics {
  bucket: string
  min_horizon_hours: number | null
  max_horizon_hours: number | null
  total_count: number
  valid_count: number
  missing_count: number
  mae: number | null
  rmse: number | null
  bias: number | null
  p50: number | null
  p90: number | null
  p95: number | null
}

export interface HorizonMetricsResponse {
  startDate: string
  endDate: string
  data: HorizonMetrics[]
}

export interface ApiErrorDetail {
  detail: string
  status?: number
}
