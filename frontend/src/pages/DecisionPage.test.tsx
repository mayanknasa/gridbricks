import React from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { FilterProvider } from '../context/FilterContext'
import { useForecast, useHourlyMetrics } from '../hooks/useQueries'
import type { ForecastResponse, HourlyMetricsResponse } from '../types/api'
import { DecisionPage } from './DecisionPage'

// Mock the queries hook module
vi.mock('../hooks/useQueries', () => ({
  useForecast: vi.fn(),
  useHourlyMetrics: vi.fn(),
}))

// Mock Recharts ResponsiveContainer to ensure stable rendering in JSDOM
vi.mock('recharts', async () => {
  const actual = await vi.importActual<typeof import('recharts')>('recharts')
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container" style={{ width: '800px', height: '400px' }}>
        {children}
      </div>
    ),
  }
})

const mockUseForecast = vi.mocked(useForecast)
const mockUseHourlyMetrics = vi.mocked(useHourlyMetrics)

describe('DecisionPage component states', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseHourlyMetrics.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useHourlyMetrics>)
  })

  it('renders LoadingState when forecast query is loading', () => {
    mockUseForecast.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useForecast>)

    render(
      <FilterProvider>
        <DecisionPage />
      </FilterProvider>,
    )

    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(
      screen.getByText('Loading forecast and buffer recommendations...'),
    ).toBeInTheDocument()
    expect(screen.getByText(/Evaluating Day D delivery/i)).toBeInTheDocument()
  })

  it('renders ErrorState with error message and retries on button click', () => {
    const mockRefetch = vi.fn().mockResolvedValue({})
    mockUseForecast.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error('Failed to fetch forecast from server'),
      refetch: mockRefetch,
    } as unknown as ReturnType<typeof useForecast>)

    render(
      <FilterProvider>
        <DecisionPage />
      </FilterProvider>,
    )

    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByText('Failed to Load Forecast Decision')).toBeInTheDocument()
    expect(screen.getByText('Failed to fetch forecast from server')).toBeInTheDocument()

    const retryButton = screen.getByRole('button', { name: /retry request/i })
    expect(retryButton).toBeInTheDocument()

    fireEvent.click(retryButton)
    expect(mockRefetch).toHaveBeenCalledTimes(1)
  })

  it('renders EmptyState when forecast data array is empty', () => {
    mockUseForecast.mockReturnValue({
      data: {
        deliveryDate: '2026-01-02',
        cutoff: '09:00',
        totalPeriods: 0,
        data: [],
      },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useForecast>)

    render(
      <FilterProvider>
        <DecisionPage />
      </FilterProvider>,
    )

    expect(screen.getByText('No Forecast Found')).toBeInTheDocument()
    expect(
      screen.getByText(
        'No published forecasts prior to 09:00 UK were located for 2026-01-02.',
      ),
    ).toBeInTheDocument()
  })

  it('renders full decision dashboard when data is successfully loaded', () => {
    const mockForecast: ForecastResponse = {
      deliveryDate: '2026-01-02',
      cutoff: '09:00',
      totalPeriods: 48,
      data: Array.from({ length: 48 }, (_, i) => ({
        startTime: `2026-01-02T${String(Math.floor(i / 2)).padStart(2, '0')}:${i % 2 === 0 ? '00' : '30'}:00Z`,
        publishTime: '2026-01-01T08:00:00Z',
        generation: 12000 + Math.floor(i / 2) * 100,
        isMissing: false,
        isDerived: i % 2 !== 0,
        forecastType: i % 2 === 0 ? 'published' : 'step_hold',
      })),
    }

    const mockHourly: HourlyMetricsResponse = {
      startDate: '2026-01-02',
      endDate: '2026-02-01',
      cutoff: '09:00',
      data: Array.from({ length: 24 }, (_, h) => ({
        hour: h,
        total_count: 31,
        valid_count: 31,
        missing_count: 0,
        mae: 1000,
        rmse: 1300,
        bias: -50,
        p50: 800,
        p90: 2100,
        p95: 2600,
        mean_actual: 14000,
        mean_forecast: 14050,
      })),
    }

    mockUseForecast.mockReturnValue({
      data: mockForecast,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useForecast>)

    mockUseHourlyMetrics.mockReturnValue({
      data: mockHourly,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useHourlyMetrics>)

    render(
      <FilterProvider>
        <DecisionPage />
      </FilterProvider>,
    )

    // Page title and headers
    expect(screen.getByText('Day-Ahead Power Purchase Decision')).toBeInTheDocument()

    // KPI Cards
    expect(screen.getByText('Peak Forecast')).toBeInTheDocument()
    expect(screen.getByText('Average Forecast')).toBeInTheDocument()
    expect(screen.getByText('Cutoff Coverage')).toBeInTheDocument()
    expect(screen.getByText('Applied Decision Cutoff')).toBeInTheDocument()

    // Coverage KPI displays valid / total (48 / 48 under step-hold)
    expect(screen.getByText('48 / 48')).toBeInTheDocument()
    expect(
      screen.getByText('24 published (:00) + 24 step-hold (:30)'),
    ).toBeInTheDocument()

    // Step-hold chart labels and banner
    expect(screen.getByText('Published (:00)')).toBeInTheDocument()
    expect(screen.getByText('Step-Hold Derived (:30)')).toBeInTheDocument()
    expect(
      screen.getByText(/Hourly Block Step-Hold Active:/i),
    ).toBeInTheDocument()

    // Summary callout
    expect(screen.getByText('Executive Takeaway for Power Buyer')).toBeInTheDocument()

    // Buffer table header
    expect(
      screen.getByText('Hourly Procurement Buffer Recommendations (Historical P90 Error)'),
    ).toBeInTheDocument()
  })

  it('steps across a month boundary using Date.UTC calendar arithmetic', () => {
    mockUseForecast.mockReturnValue({
      data: {
        deliveryDate: '2026-01-31',
        cutoff: '09:00',
        totalPeriods: 48,
        data: [
          {
            startTime: '2026-01-31T00:00:00Z',
            publishTime: '2026-01-30T08:00:00Z',
            generation: 12000,
            isMissing: false,
            isDerived: false,
            forecastType: 'published',
          },
        ],
      },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useForecast>)

    render(
      <FilterProvider initialFilters={{ deliveryDate: '2026-01-31' }}>
        <DecisionPage />
      </FilterProvider>,
    )

    const dateInput = screen.getByLabelText('Delivery Date') as HTMLInputElement
    expect(dateInput.value).toBe('2026-01-31')

    // Click "Next Day" button to step across month boundary from Jan 31 to Feb 1
    const nextBtn = screen.getByRole('button', { name: 'Next Day' })
    fireEvent.click(nextBtn)

    expect(dateInput.value).toBe('2026-02-01')

    // Click "Previous Day" button to step backward across month boundary from Feb 1 to Jan 31
    const prevBtn = screen.getByRole('button', { name: 'Previous Day' })
    fireEvent.click(prevBtn)

    expect(dateInput.value).toBe('2026-01-31')
  })

  it('queries hourly metrics with baseline dates from the store', () => {
    mockUseForecast.mockReturnValue({
      data: {
        deliveryDate: '2026-01-02',
        cutoff: '09:00',
        totalPeriods: 48,
        data: [],
      },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useForecast>)

    render(
      <FilterProvider
        initialFilters={{
          startDate: '2026-01-05',
          endDate: '2026-01-25',
          cutoff: '12:00',
        }}
      >
        <DecisionPage />
      </FilterProvider>,
    )

    expect(mockUseHourlyMetrics).toHaveBeenCalledWith('2026-01-05', '2026-01-25', '12:00')
  })

  it('maps summer period starting at 23:00 UTC previous day to hour 0 in Europe/London', () => {
    mockUseForecast.mockReturnValue({
      data: {
        deliveryDate: '2026-07-01',
        cutoff: '09:00',
        totalPeriods: 48,
        data: [
          {
            startTime: '2026-06-30T23:00:00Z', // 00:00 BST delivery day
            publishTime: '2026-06-30T07:30:00Z',
            generation: 15000,
            isMissing: false,
            isDerived: false,
            forecastType: 'published',
          },
        ],
      },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useForecast>)

    mockUseHourlyMetrics.mockReturnValue({
      data: {
        startDate: '2026-01-02',
        endDate: '2026-02-01',
        cutoff: '09:00',
        data: [
          {
            hour: 0,
            total_count: 10,
            valid_count: 10,
            missing_count: 0,
            mae: 200,
            rmse: 250,
            bias: 10,
            p50: 150,
            p90: 500,
            p95: 600,
            mean_actual: 14500,
            mean_forecast: 15000,
          },
        ],
      },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useHourlyMetrics>)

    render(
      <FilterProvider initialFilters={{ deliveryDate: '2026-07-01' }}>
        <DecisionPage />
      </FilterProvider>,
    )

    // Hour 00:00 - 01:00 row should have forecastAvgMW = 15,000 MW and buffer P90 = 500 MW -> hedged = 14,500 MW
    expect(screen.getByText('00:00 – 01:00')).toBeInTheDocument()
    expect(screen.getByText('14,500 MW')).toBeInTheDocument()
  })
})
