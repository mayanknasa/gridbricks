import { useContext } from 'react'
import { FilterContext, type FilterContextValue } from './filterState'

export const useFilters = (): FilterContextValue => {
  const context = useContext(FilterContext)
  if (!context) {
    throw new Error('useFilters must be used within a FilterProvider')
  }
  return context
}
