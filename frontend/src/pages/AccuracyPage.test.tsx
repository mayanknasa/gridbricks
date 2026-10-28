import React from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { FilterProvider } from '../context/FilterContext'
import {
  useCompare,
  useHorizonMetrics,
  useHourlyMetrics,
  useOverallMetrics,
} from '../hooks/useQueries'
import type {
  CompareResponse,
  HorizonMetricsResponse,
  HourlyMetricsResponse,
  OverallMetricsResponse,
} from '../types/api'
import { AccuracyPage } from './AccuracyPage'

// Mock the queries hook module
vi.mock('../hooks/useQueries', () => ({
  useOverallMetrics: vi.fn(),
  useCompare: vi.fn(),
  useHourlyMetrics: vi.fn(),
  useHorizonMetrics: vi.fn(),
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

const mockUseOverallMetrics = vi.mocked(useOverallMetrics)
const mockUseCompare = vi.mocked(useCompare)
const mockUseHourlyMetrics = vi.mocked(useHourlyMetrics)
const mockUseHorizonMetrics = vi.mocked(useHorizonMetrics)

const sampleOverallData: OverallMetricsResponse = {
  startDate: '2026-01-02',
  endDate: '2026-02-01',
  cutoff: '09:00',
  metrics: {
    total_count: 1488,
    valid_count: 1440,
    missing_count: 48,
    mae: 420.5,
    rmse: 610.8,
    bias: -85.2,
    nmae_pct: 7.2,
    p50: 310.0,
    p90: 890.4,
    p95: 1150.0,
    mean_actual: 5850.0,
    mean_forecast: 5935.2,
  },
}

const sampleCompareData: CompareResponse = {
  startDate: '2026-01-02',
  endDate: '2026-02-01',
  cutoff: '09:00',
  totalPeriods: 4,
  data: [
    {
      startTime: '2026-01-02T00:00:00Z',
      publishTime: '2026-01-01T08:30:00Z',
      actualGeneration: 5000,
      forecastGeneration: 5200,
      error: -200,
      absError: 200,
      isMissing: false,
    },
    {
      startTime: '2026-01-02T00:30:00Z',
      publishTime: null,
      actualGeneration: 5100,
      forecastGeneration: null,
      error: null,
      absError: null,
      isMissing: true,
    },
    {
      startTime: '2026-01-02T01:00:00Z',
      publishTime: '2026-01-01T08:30:00Z',
      actualGeneration: 5400,
      forecastGeneration: 5300,
      error: 100,
      absError: 100,
      isMissing: false,
    },
    {
      startTime: '2026-01-02T01:30:00Z',
      publishTime: '2026-01-01T08:30:00Z',
      actualGeneration: 5600,
      forecastGeneration: 5550,
      error: 50,
      absError: 50,
      isMissing: false,
    },
  ],
}

const sampleHourlyData: HourlyMetricsResponse = {
  startDate: '2026-01-02',
  endDate: '2026-02-01',
  cutoff: '09:00',
  data: [
    {
      hour: 0,
      total_count: 62,
      valid_count: 60,
      missing_count: 2,
      mae: 350.0,
      rmse: 480.0,
      bias: -50.0,
      p50: 250.0,
      p90: 700.0,
      p95: 900.0,
      mean_actual: 5000.0,
      mean_forecast: 5050.0,
    },
    {
      hour: 12,
      total_count: 62,
      valid_count: 62,
      missing_count: 0,
      mae: 650.0,
      rmse: 850.0,
      bias: -120.0,
      p50: 450.0,
      p90: 1200.0,
      p95: 1500.0,
      mean_actual: 6200.0,
      mean_forecast: 6320.0,
    },
  ],
}

const sampleHorizonData: HorizonMetricsResponse = {
  startDate: '2026-01-02',
  endDate: '2026-02-01',
  data: [
    {
      bucket: '0-6h',
      min_horizon_hours: 0,
      max_horizon_hours: 6,
      total_count: 200,
      valid_count: 200,
      missing_count: 0,
      mae: 250.0,
      rmse: 340.0,
      bias: -30.0,
      p50: 180.0,
      p90: 520.0,
      p95: 680.0,
    },
    {
      bucket: '>48h',
      min_horizon_hours: 48,
      max_horizon_hours: 72,
      total_count: 200,
      valid_count: 195,
      missing_count: 5,
      mae: 650.0,
      rmse: 890.0,
      bias: -150.0,
      p50: 480.0,
      p90: 1350.0,
      p95: 1700.0,
    },
  ],
}

describe('AccuracyPage component states', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders LoadingState when any accuracy query is loading', () => {
    mockUseOverallMetrics.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useOverallMetrics>)

    mockUseCompare.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCompare>)

    mockUseHourlyMetrics.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useHourlyMetrics>)

    mockUseHorizonMetrics.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useHorizonMetrics>)

    render(
      <FilterProvider>
        <AccuracyPage />
      </FilterProvider>,
    )

    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(
      screen.getByText('Computing comprehensive accuracy benchmarks...'),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/Analyzing 1,500\+ intervals/i),
    ).toBeInTheDocument()
  })

  it('renders ErrorState with error details and retries all queries on button click', () => {
    const mockRefetchOverall = vi.fn().mockResolvedValue({})
    const mockRefetchCompare = vi.fn().mockResolvedValue({})
    const mockRefetchHourly = vi.fn().mockResolvedValue({})
    const mockRefetchHorizon = vi.fn().mockResolvedValue({})

    mockUseOverallMetrics.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error('Failed to compute accuracy benchmarks from backend'),
      refetch: mockRefetchOverall,
    } as unknown as ReturnType<typeof useOverallMetrics>)

    mockUseCompare.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
      error: null,
      refetch: mockRefetchCompare,
    } as unknown as ReturnType<typeof useCompare>)

    mockUseHourlyMetrics.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
      error: null,
      refetch: mockRefetchHourly,
    } as unknown as ReturnType<typeof useHourlyMetrics>)

    mockUseHorizonMetrics.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
      error: null,
      refetch: mockRefetchHorizon,
    } as unknown as ReturnType<typeof useHorizonMetrics>)

    render(
      <FilterProvider>
        <AccuracyPage />
      </FilterProvider>,
    )

    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByText('Accuracy Benchmark Error')).toBeInTheDocument()
    expect(
      screen.getByText('Failed to compute accuracy benchmarks from backend'),
    ).toBeInTheDocument()

    const retryButton = screen.getByRole('button', { name: /retry request/i })
    expect(retryButton).toBeInTheDocument()

    fireEvent.click(retryButton)
    expect(mockRefetchOverall).toHaveBeenCalledTimes(1)
    expect(mockRefetchCompare).toHaveBeenCalledTimes(1)
    expect(mockRefetchHourly).toHaveBeenCalledTimes(1)
    expect(mockRefetchHorizon).toHaveBeenCalledTimes(1)
  })

  it('renders EmptyState when metrics return 0 total count', () => {
    mockUseOverallMetrics.mockReturnValue({
      data: {
        startDate: '2026-01-02',
        endDate: '2026-02-01',
        cutoff: '09:00',
        metrics: {
          total_count: 0,
          valid_count: 0,
          missing_count: 0,
          mae: null,
          rmse: null,
          bias: null,
          nmae_pct: null,
          p50: null,
          p90: null,
          p95: null,
          mean_actual: null,
          mean_forecast: null,
        },
      },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useOverallMetrics>)

    mockUseCompare.mockReturnValue({
      data: {
        startDate: '2026-01-02',
        endDate: '2026-02-01',
        cutoff: '09:00',
        totalPeriods: 0,
        data: [],
      },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCompare>)

    mockUseHourlyMetrics.mockReturnValue({
      data: {
        startDate: '2026-01-02',
        endDate: '2026-02-01',
        cutoff: '09:00',
        data: [],
      },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useHourlyMetrics>)

    mockUseHorizonMetrics.mockReturnValue({
      data: {
        startDate: '2026-01-02',
        endDate: '2026-02-01',
        data: [],
      },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useHorizonMetrics>)

    render(
      <FilterProvider>
        <AccuracyPage />
      </FilterProvider>,
    )

    expect(screen.getByText('No Benchmark Data Found')).toBeInTheDocument()
    expect(
      screen.getByText(/No evaluation intervals found between/i),
    ).toBeInTheDocument()
  })

  it('renders loaded accuracy dashboard with all 10 metric cards, 4 charts, and dynamic takeaways', () => {
    mockUseOverallMetrics.mockReturnValue({
      data: sampleOverallData,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useOverallMetrics>)

    mockUseCompare.mockReturnValue({
      data: sampleCompareData,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCompare>)

    mockUseHourlyMetrics.mockReturnValue({
      data: sampleHourlyData,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useHourlyMetrics>)

    mockUseHorizonMetrics.mockReturnValue({
      data: sampleHorizonData,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useHorizonMetrics>)

    render(
      <FilterProvider>
        <AccuracyPage />
      </FilterProvider>,
    )

    // 1. Check Page Header
    expect(screen.getByText('Forecast Accuracy Benchmark')).toBeInTheDocument()

    // 2. Check 5 Primary KPI Cards
    const maeElements = screen.getAllByText('Mean Absolute Error (MAE)')
    expect(maeElements.length).toBeGreaterThanOrEqual(1)
    expect(maeElements[0]).toBeInTheDocument()
    expect(screen.getByText('421 MW')).toBeInTheDocument()

    expect(screen.getByText('Root Mean Square Error (RMSE)')).toBeInTheDocument()
    expect(screen.getByText('611 MW')).toBeInTheDocument()

    expect(screen.getByText('Forecast Bias (Mean Error)')).toBeInTheDocument()
    expect(screen.getByText('-85 MW')).toBeInTheDocument()
    expect(
      screen.getByText('Over-predicting (Actual < Forecast)'),
    ).toBeInTheDocument()

    expect(screen.getByText('Normalised MAE (nMAE)')).toBeInTheDocument()
    expect(screen.getByText('7.2%')).toBeInTheDocument()

    expect(screen.getByText('P90 Absolute Error')).toBeInTheDocument()
    expect(screen.getByText('890 MW')).toBeInTheDocument()

    // 3. Check 5 Secondary Mini KPI Cards
    expect(screen.getByText('P50 (Median Absolute Error)')).toBeInTheDocument()
    expect(screen.getByText('310 MW')).toBeInTheDocument()

    expect(screen.getByText('P95 Absolute Error')).toBeInTheDocument()
    expect(screen.getByText('1,150 MW')).toBeInTheDocument()

    expect(screen.getByText('Mean Actual Generation')).toBeInTheDocument()
    expect(screen.getByText('5,850 MW')).toBeInTheDocument()

    expect(screen.getByText('Mean Forecast Generation')).toBeInTheDocument()
    expect(screen.getByText('5,935 MW')).toBeInTheDocument()

    expect(screen.getByText('Evaluated Coverage')).toBeInTheDocument()
    expect(screen.getByText('1,440 / 1,488')).toBeInTheDocument()

    // 4. Check All 4 Chart Headings
    expect(
      screen.getByText(
        'Forecast versus Actual Generation (Full Time-Series with Interactive Zoom)',
      ),
    ).toBeInTheDocument()
    expect(
      screen.getByText('Error Distribution Profile (Actual − Forecast)'),
    ).toBeInTheDocument()
    expect(
      screen.getByText('Diurnal Error Breakdown by Hour of Day (UK Local Time)'),
    ).toBeInTheDocument()
    expect(
      screen.getByText('Forecast Degradation by Lead Time Horizon'),
    ).toBeInTheDocument()

    // 5. Verify 4 ResponsiveContainer instances (one per chart)
    const chartContainers = screen.getAllByTestId('responsive-container')
    expect(chartContainers).toHaveLength(4)

    // 6. Verify Dynamic Empirical Takeaways
    expect(
      screen.getByText(
        /On average across the selected range, the day-ahead forecast over-predicted actual wind outturn by 85 MW/i,
      ),
    ).toBeInTheDocument()
    expect(
      screen.getByText(
        /The error distribution is right-skewed \(67% under-forecast\), with the modal concentration peaking in the/i,
      ),
    ).toBeInTheDocument()
    expect(
      screen.getByText(
        /Diurnal forecast uncertainty peaks at 12:00 UK \(MAE 650 MW, P90 error 1,200 MW\) and reaches minimum deviation at 00:00 UK \(MAE 350 MW\)/i,
      ),
    ).toBeInTheDocument()
    expect(
      screen.getByText(
        /Forecast degradation scales directly with lead time: MAE expands by \+160% from 250 MW at \[0-6h\] to 650 MW at extended lead times \[>48h\]/i,
      ),
    ).toBeInTheDocument()
  })

  it('allows changing the cutoff time from the control header', () => {
    mockUseOverallMetrics.mockReturnValue({
      data: sampleOverallData,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useOverallMetrics>)

    mockUseCompare.mockReturnValue({
      data: sampleCompareData,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCompare>)

    mockUseHourlyMetrics.mockReturnValue({
      data: sampleHourlyData,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useHourlyMetrics>)

    mockUseHorizonMetrics.mockReturnValue({
      data: sampleHorizonData,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useHorizonMetrics>)

    render(
      <FilterProvider>
        <AccuracyPage />
      </FilterProvider>,
    )

    const cutoffSelect = screen.getByLabelText(/Cutoff Time/i) as HTMLSelectElement
    expect(cutoffSelect.value).toBe('09:00')

    fireEvent.change(cutoffSelect, { target: { value: '12:00' } })
    expect(cutoffSelect.value).toBe('12:00')
  })
})
