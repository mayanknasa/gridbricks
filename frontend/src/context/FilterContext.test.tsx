import React from 'react'
import { act, renderHook } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { FilterProvider } from './FilterContext'
import { DEFAULT_FILTERS } from './filterState'
import { useFilters } from './useFilters'

describe('FilterContext & useFilters store', () => {
  it('throws an error if useFilters is called outside of a FilterProvider', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => renderHook(() => useFilters())).toThrow(
      'useFilters must be used within a FilterProvider',
    )
    spy.mockRestore()
  })

  it('provides default filter state correctly', () => {
    const { result } = renderHook(() => useFilters(), {
      wrapper: ({ children }: { children: React.ReactNode }) => (
        <FilterProvider>{children}</FilterProvider>
      ),
    })

    expect(result.current.startDate).toBe(DEFAULT_FILTERS.startDate)
    expect(result.current.endDate).toBe(DEFAULT_FILTERS.endDate)
    expect(result.current.cutoff).toBe(DEFAULT_FILTERS.cutoff)
    expect(result.current.deliveryDate).toBe(DEFAULT_FILTERS.deliveryDate)
    expect(result.current.datasetBounds).toEqual(DEFAULT_FILTERS.datasetBounds)
  })

  it('updates deliveryDate when setDeliveryDate is called', () => {
    const { result } = renderHook(() => useFilters(), {
      wrapper: ({ children }: { children: React.ReactNode }) => (
        <FilterProvider>{children}</FilterProvider>
      ),
    })

    act(() => {
      result.current.setDeliveryDate('2026-01-15')
    })

    expect(result.current.deliveryDate).toBe('2026-01-15')
  })

  it('updates cutoff when setCutoff is called', () => {
    const { result } = renderHook(() => useFilters(), {
      wrapper: ({ children }: { children: React.ReactNode }) => (
        <FilterProvider>{children}</FilterProvider>
      ),
    })

    act(() => {
      result.current.setCutoff('17:00')
    })

    expect(result.current.cutoff).toBe('17:00')
  })

  it('updates date range when setStartDate, setEndDate, and setDateRange are called', () => {
    const { result } = renderHook(() => useFilters(), {
      wrapper: ({ children }: { children: React.ReactNode }) => (
        <FilterProvider>{children}</FilterProvider>
      ),
    })

    act(() => {
      result.current.setStartDate('2026-01-05')
    })
    expect(result.current.startDate).toBe('2026-01-05')

    act(() => {
      result.current.setEndDate('2026-01-20')
    })
    expect(result.current.endDate).toBe('2026-01-20')

    act(() => {
      result.current.setDateRange('2026-01-10', '2026-01-25')
    })
    expect(result.current.startDate).toBe('2026-01-10')
    expect(result.current.endDate).toBe('2026-01-25')
  })

  it('resets filters to DEFAULT_FILTERS when resetFilters is called', () => {
    const { result } = renderHook(() => useFilters(), {
      wrapper: ({ children }: { children: React.ReactNode }) => (
        <FilterProvider>{children}</FilterProvider>
      ),
    })

    act(() => {
      result.current.setDeliveryDate('2026-01-20')
      result.current.setCutoff('23:00')
      result.current.setDateRange('2026-01-15', '2026-01-30')
    })

    expect(result.current.deliveryDate).toBe('2026-01-20')
    expect(result.current.cutoff).toBe('23:00')

    act(() => {
      result.current.resetFilters()
    })

    expect(result.current.startDate).toBe(DEFAULT_FILTERS.startDate)
    expect(result.current.endDate).toBe(DEFAULT_FILTERS.endDate)
    expect(result.current.cutoff).toBe(DEFAULT_FILTERS.cutoff)
    expect(result.current.deliveryDate).toBe(DEFAULT_FILTERS.deliveryDate)
  })
})
