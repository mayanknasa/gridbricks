/**
 * REST API client module communicating with FastAPI /api/v1 endpoints.
 */

import type {
  CompareResponse,
  ForecastResponse,
  HealthStatus,
  HorizonMetricsResponse,
  HourlyMetricsResponse,
  OverallMetricsResponse,
} from '../types/api'

const rawApiBase = import.meta.env.VITE_API_URL || ''
const API_BASE = rawApiBase.replace(/\/+$/, '')

export class ApiError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

async function request<T>(endpoint: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${API_BASE}${endpoint}`, window.location.origin)
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        url.searchParams.append(key, value)
      }
    })
  }

  const response = await fetch(url.toString(), {
    headers: {
      Accept: 'application/json',
    },
  })

  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`
    try {
      const errBody = await response.json()
      if (errBody && typeof errBody.detail === 'string') {
        errorDetail = errBody.detail
      }
    } catch {
      // Body was not JSON
    }
    throw new ApiError(response.status, errorDetail)
  }

  return response.json() as Promise<T>
}

export const apiClient = {
  /**
   * Check system health and backend service connectivity.
   */
  getHealth: (): Promise<HealthStatus> => {
    return request<HealthStatus>('/api/v1/health')
  },

  /**
   * Fetch selected day-ahead forecast per settlement period for a delivery date.
   */
  getForecast: (deliveryDate: string, cutoff: string): Promise<ForecastResponse> => {
    return request<ForecastResponse>('/api/v1/forecast', {
      delivery_date: deliveryDate,
      cutoff,
    })
  },

  /**
   * Compare selected forecasts against actual outturn per target half-hour.
   */
  getCompare: (start: string, end: string, cutoff: string): Promise<CompareResponse> => {
    return request<CompareResponse>('/api/v1/compare', {
      start,
      end,
      cutoff,
    })
  },

  /**
   * Fetch overall benchmark performance metrics across a date range.
   */
  getOverallMetrics: (start: string, end: string, cutoff: string): Promise<OverallMetricsResponse> => {
    return request<OverallMetricsResponse>('/api/v1/metrics', {
      start,
      end,
      cutoff,
    })
  },

  /**
   * Fetch 24-hour diurnal profile of forecast errors by hour of day (UK local time).
   */
  getHourlyMetrics: (start: string, end: string, cutoff: string): Promise<HourlyMetricsResponse> => {
    return request<HourlyMetricsResponse>('/api/v1/metrics/by_hour', {
      start,
      end,
      cutoff,
    })
  },

  /**
   * Fetch forecast error metrics bucketed by lead time horizon.
   */
  getHorizonMetrics: (start: string, end: string): Promise<HorizonMetricsResponse> => {
    return request<HorizonMetricsResponse>('/api/v1/metrics/by_horizon', {
      start,
      end,
    })
  },
}
