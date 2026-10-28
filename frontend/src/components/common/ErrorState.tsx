import React from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'

interface ErrorStateProps {
  title?: string
  message: string
  statusCode?: number
  onRetry?: () => void
  minHeight?: string | number
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Failed to load data',
  message,
  statusCode,
  onRetry,
  minHeight = '320px',
}) => {
  return (
    <div className="state-container error-state" style={{ minHeight }} role="alert">
      <div className="state-icon-wrapper error-icon">
        <AlertCircle size={38} />
      </div>
      {statusCode && (
        <span className="badge badge-error">HTTP {statusCode}</span>
      )}
      <h3 className="state-title">{title}</h3>
      <p className="state-desc error-message">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="btn btn-primary state-retry-btn"
        >
          <RefreshCw size={16} className="btn-icon" />
          <span>Retry Request</span>
        </button>
      )}
    </div>
  )
}
