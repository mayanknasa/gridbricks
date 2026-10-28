import React from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppLayout } from './components/layout/AppLayout'
import { FilterProvider } from './context'
import { AccuracyPage } from './pages/AccuracyPage'
import { DecisionPage } from './pages/DecisionPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <FilterProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<AppLayout />}>
              <Route index element={<Navigate to="/decision" replace />} />
              <Route path="decision" element={<DecisionPage />} />
              <Route path="accuracy" element={<AccuracyPage />} />
              <Route path="*" element={<Navigate to="/decision" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </FilterProvider>
    </QueryClientProvider>
  )
}

export default App
