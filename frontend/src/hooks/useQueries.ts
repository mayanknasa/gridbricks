/**
 * TanStack Query hooks for asynchronous API data fetching.
 */

import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import type {
  CompareResponse,
  ForecastResponse,
  HealthStatus,
  HorizonMetricsResponse,
  HourlyMetricsResponse,
  OverallMetricsResponse,
} from '../types/api'

const STALE_TIME_MS = 1000 * 60 * 5 // 5 minutes

export const useHealth = () => {
  return useQuery<HealthStatus, Error>({
    queryKey: ['health'],
    queryFn: apiClient.getHealth,
    staleTime: 1000 * 30, // 30 seconds
    retry: 1,
  })
}

export const useForecast = (deliveryDate: string, cutoff: string) => {
  return useQuery<ForecastResponse, Error>({
    queryKey: ['forecast', deliveryDate, cutoff],
    queryFn: () => apiClient.getForecast(deliveryDate, cutoff),
    staleTime: STALE_TIME_MS,
    enabled: Boolean(deliveryDate && cutoff),
  })
}

export const useCompare = (start: string, end: string, cutoff: string) => {
  return useQuery<CompareResponse, Error>({
    queryKey: ['compare', start, end, cutoff],
    queryFn: () => apiClient.getCompare(start, end, cutoff),
    staleTime: STALE_TIME_MS,
    enabled: Boolean(start && end && cutoff),
  })
}

export const useOverallMetrics = (start: string, end: string, cutoff: string) => {
  return useQuery<OverallMetricsResponse, Error>({
    queryKey: ['metrics', 'overall', start, end, cutoff],
    queryFn: () => apiClient.getOverallMetrics(start, end, cutoff),
    staleTime: STALE_TIME_MS,
    enabled: Boolean(start && end && cutoff),
  })
}

export const useHourlyMetrics = (start: string, end: string, cutoff: string) => {
  return useQuery<HourlyMetricsResponse, Error>({
    queryKey: ['metrics', 'hourly', start, end, cutoff],
    queryFn: () => apiClient.getHourlyMetrics(start, end, cutoff),
    staleTime: STALE_TIME_MS,
    enabled: Boolean(start && end && cutoff),
  })
}

export const useHorizonMetrics = (start: string, end: string) => {
  return useQuery<HorizonMetricsResponse, Error>({
    queryKey: ['metrics', 'horizon', start, end],
    queryFn: () => apiClient.getHorizonMetrics(start, end),
    staleTime: STALE_TIME_MS,
    enabled: Boolean(start && end),
  })
}
