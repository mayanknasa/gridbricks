import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiClient } from './client'

describe('apiClient and ApiError handling', () => {
  const originalFetch = globalThis.fetch

  beforeEach(() => {
    vi.restoreAllMocks()
  })

  afterEach(() => {
    globalThis.fetch = originalFetch
  })

  it('instantiates ApiError correctly with status and detail', () => {
    const error = new ApiError(400, "Invalid cutoff time '25:00'")
    expect(error).toBeInstanceOf(Error)
    expect(error.name).toBe('ApiError')
    expect(error.status).toBe(400)
    expect(error.detail).toBe("Invalid cutoff time '25:00'")
    expect(error.message).toBe("Invalid cutoff time '25:00'")
  })

  it('rejects with ApiError containing detail on 400 Bad Request with JSON body', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      statusText: 'Bad Request',
      json: vi.fn().mockResolvedValue({
        detail: 'delivery_date (2025-12-31) is outside available January 2026 data range',
      }),
    } as unknown as Response)

    await expect(apiClient.getForecast('2025-12-31', '09:00')).rejects.toThrow(ApiError)

    try {
      await apiClient.getForecast('2025-12-31', '09:00')
    } catch (err) {
      const apiErr = err as ApiError
      expect(apiErr.status).toBe(400)
      expect(apiErr.detail).toContain('outside available January 2026 data range')
    }
  })

  it('rejects with fallback message on 500 Internal Server Error when JSON parsing fails', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: vi.fn().mockRejectedValue(new Error('Invalid JSON')),
    } as unknown as Response)

    try {
      await apiClient.getForecast('2026-01-02', '09:00')
      expect.unreachable('Should have thrown an ApiError')
    } catch (err) {
      const apiErr = err as ApiError
      expect(apiErr).toBeInstanceOf(ApiError)
      expect(apiErr.status).toBe(500)
      expect(apiErr.detail).toBe('Request failed with status 500')
    }
  })

  it('propagates network failures when fetch throws', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'))

    await expect(apiClient.getHealth()).rejects.toThrow('Failed to fetch')
  })

  it('successfully makes request and serializes query parameters', async () => {
    const mockData = {
      deliveryDate: '2026-01-02',
      cutoff: '09:00',
      totalPeriods: 48,
      data: [],
    }

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: vi.fn().mockResolvedValue(mockData),
    } as unknown as Response)

    const result = await apiClient.getForecast('2026-01-02', '09:00')

    expect(result).toEqual(mockData)
    expect(globalThis.fetch).toHaveBeenCalledTimes(1)
    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string
    expect(calledUrl).toContain('/api/v1/forecast')
    expect(calledUrl).toContain('delivery_date=2026-01-02')
    expect(calledUrl).toContain('cutoff=09%3A00')
  })

  it('queries getHorizonMetrics without cutoff parameter', async () => {
    const mockHorizonData = {
      startDate: '2026-01-02',
      endDate: '2026-01-10',
      data: [],
    }

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: vi.fn().mockResolvedValue(mockHorizonData),
    } as unknown as Response)

    const result = await apiClient.getHorizonMetrics('2026-01-02', '2026-01-10')

    expect(result).toEqual(mockHorizonData)
    expect(globalThis.fetch).toHaveBeenCalledTimes(1)
    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string
    expect(calledUrl).toContain('/api/v1/metrics/by_horizon')
    expect(calledUrl).toContain('start=2026-01-02')
    expect(calledUrl).toContain('end=2026-01-10')
    expect(calledUrl).not.toContain('cutoff')
  })
})
