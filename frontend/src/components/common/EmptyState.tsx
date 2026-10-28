import React from 'react'
import { Inbox } from 'lucide-react'

interface EmptyStateProps {
  title?: string
  description?: string
  actionLabel?: string
  onAction?: () => void
  minHeight?: string | number
  icon?: React.ReactNode
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = 'No records found',
  description = 'No half-hourly intervals match the selected filters or cutoff period.',
  actionLabel,
  onAction,
  minHeight = '320px',
  icon,
}) => {
  return (
    <div className="state-container empty-state" style={{ minHeight }}>
      <div className="state-icon-wrapper empty-icon">
        {icon || <Inbox size={38} />}
      </div>
      <h3 className="state-title">{title}</h3>
      <p className="state-desc">{description}</p>
      {actionLabel && onAction && (
        <button
          type="button"
          onClick={onAction}
          className="btn btn-secondary state-action-btn"
        >
          {actionLabel}
        </button>
      )}
    </div>
  )
}
