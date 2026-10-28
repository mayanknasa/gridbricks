import React from 'react'
import { Loader2 } from 'lucide-react'

interface LoadingStateProps {
  message?: string
  description?: string
  minHeight?: string | number
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Loading data...',
  description = 'Fetching and computing wind forecast benchmarks',
  minHeight = '320px',
}) => {
  return (
    <div
      className="state-container loading-state"
      style={{ minHeight }}
      role="status"
      aria-live="polite"
    >
      <div className="spinner-wrapper">
        <Loader2 className="spinner-icon" size={36} />
      </div>
      <h3 className="state-title">{message}</h3>
      {description && <p className="state-desc">{description}</p>}
      <div className="skeleton-preview">
        <div className="skeleton-bar" style={{ width: '60%' }} />
        <div className="skeleton-bar" style={{ width: '85%' }} />
        <div className="skeleton-bar" style={{ width: '40%' }} />
      </div>
    </div>
  )
}
