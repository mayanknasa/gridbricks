import React, { useMemo, useState } from 'react'
import {
  DEFAULT_FILTERS,
  FilterContext,
  type FilterContextValue,
  type FilterState,
} from './filterState'

export const FilterProvider: React.FC<{
  children: React.ReactNode
  initialFilters?: Partial<FilterState>
}> = ({ children, initialFilters }) => {
  const [filters, setFilters] = useState<FilterState>(() => ({
    ...DEFAULT_FILTERS,
    ...initialFilters,
  }))

  const value = useMemo<FilterContextValue>(
    () => ({
      ...filters,
      setStartDate: (startDate: string) => setFilters((prev) => ({ ...prev, startDate })),
      setEndDate: (endDate: string) => setFilters((prev) => ({ ...prev, endDate })),
      setCutoff: (cutoff: string) => setFilters((prev) => ({ ...prev, cutoff })),
      setDeliveryDate: (deliveryDate: string) => setFilters((prev) => ({ ...prev, deliveryDate })),
      setDateRange: (startDate: string, endDate: string) =>
        setFilters((prev) => ({ ...prev, startDate, endDate })),
      resetFilters: () => setFilters(DEFAULT_FILTERS),
    }),
    [filters],
  )

  return <FilterContext.Provider value={value}>{children}</FilterContext.Provider>
}
