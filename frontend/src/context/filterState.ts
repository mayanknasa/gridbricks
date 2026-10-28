import { createContext } from 'react'

export interface DatasetBounds {
  minDate: string
  maxDate: string
  startDate: string
  endDate: string
}

export const DATASET_BOUNDS: DatasetBounds = {
  minDate: '2026-01-01',
  maxDate: '2026-02-02',
  startDate: '2026-01-02',
  endDate: '2026-02-01',
}

export interface FilterState {
  startDate: string
  endDate: string
  cutoff: string
  deliveryDate: string
  datasetBounds: DatasetBounds
}

export interface FilterContextValue extends FilterState {
  setStartDate: (date: string) => void
  setEndDate: (date: string) => void
  setCutoff: (cutoff: string) => void
  setDeliveryDate: (date: string) => void
  setDateRange: (start: string, end: string) => void
  resetFilters: () => void
}

export const DEFAULT_FILTERS: FilterState = {
  startDate: DATASET_BOUNDS.startDate,
  endDate: DATASET_BOUNDS.endDate,
  cutoff: '09:00',
  deliveryDate: '2026-01-02',
  datasetBounds: DATASET_BOUNDS,
}

export const FilterContext = createContext<FilterContextValue | undefined>(undefined)
