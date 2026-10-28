import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Automatically clean up after each test run
afterEach(() => {
  cleanup()
})

// Mock ResizeObserver for Recharts ResponsiveContainer in JSDOM
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

window.ResizeObserver = ResizeObserverMock

// Mock window.scrollTo
window.scrollTo = () => {}
