import React from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import {
  Activity,
  Calendar,
  Clock,
  RotateCcw,
  Sparkles,
  Target,
  Wind,
} from 'lucide-react'
import { useFilters } from '../../context'
import { useHealth } from '../../hooks/useQueries'

export const AppLayout: React.FC = () => {
  const location = useLocation()
  const { data: healthData, isError: isHealthError } = useHealth()
  const {
    startDate,
    endDate,
    cutoff,
    deliveryDate,
    datasetBounds,
    setStartDate,
    setEndDate,
    setCutoff,
    setDeliveryDate,
    setDateRange,
    resetFilters,
  } = useFilters()

  const isDecisionPage = location.pathname.includes('/decision')

  const handlePresetFullMonth = () => {
    setDateRange('2026-01-02', '2026-02-01')
  }

  const handlePresetFirstWeek = () => {
    setDateRange('2026-01-02', '2026-01-08')
  }

  return (
    <div className="app-shell">
      {/* Top Header & Navigation */}
      <header className="app-header">
        <div className="header-container">
          <div className="brand-section">
            <div className="brand-icon-wrapper">
              <Wind className="brand-icon" size={24} />
            </div>
            <div>
              <div className="brand-title">Gridbricks</div>
              <div className="brand-subtitle">
                GB Wind Generation Forecast Benchmark
              </div>
            </div>
          </div>

          <nav className="nav-tabs" aria-label="Main Navigation">
            <NavLink
              to="/decision"
              className={({ isActive }) =>
                `nav-tab ${isActive ? 'nav-tab-active' : ''}`
              }
            >
              <Target size={18} className="nav-icon" />
              <span>Decision</span>
            </NavLink>
            <NavLink
              to="/accuracy"
              className={({ isActive }) =>
                `nav-tab ${isActive ? 'nav-tab-active' : ''}`
              }
            >
              <Activity size={18} className="nav-icon" />
              <span>Accuracy</span>
            </NavLink>
          </nav>

          <div className="system-status">
            <div
              className={`status-indicator ${
                isHealthError
                  ? 'status-offline'
                  : healthData?.status === 'ok'
                    ? 'status-online'
                    : 'status-checking'
              }`}
            />
            <span className="status-label">
              {isHealthError
                ? 'Backend Offline'
                : healthData?.status === 'ok'
                  ? `API v${healthData.version}`
                  : 'Connecting...'}
            </span>
          </div>
        </div>
      </header>

      {/* Global Filter Bar */}
      <section className="filter-bar" aria-label="Forecast Controls">
        <div className="filter-container">
          <div className="filter-group">
            {isDecisionPage ? (
              <div className="filter-item">
                <label htmlFor="delivery-date-input" className="filter-label">
                  <Calendar size={14} className="filter-icon" />
                  <span>Delivery Day (Day D)</span>
                </label>
                <input
                  id="delivery-date-input"
                  type="date"
                  min={datasetBounds.minDate}
                  max={datasetBounds.maxDate}
                  value={deliveryDate}
                  onChange={(e) => setDeliveryDate(e.target.value)}
                  className="filter-input"
                />
              </div>
            ) : (
              <>
                <div className="filter-item">
                  <label htmlFor="start-date-input" className="filter-label">
                    <Calendar size={14} className="filter-icon" />
                    <span>Start Date</span>
                  </label>
                  <input
                    id="start-date-input"
                    type="date"
                    min={datasetBounds.minDate}
                    max={datasetBounds.maxDate}
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="filter-input"
                  />
                </div>

                <div className="filter-item">
                  <label htmlFor="end-date-input" className="filter-label">
                    <Calendar size={14} className="filter-icon" />
                    <span>End Date</span>
                  </label>
                  <input
                    id="end-date-input"
                    type="date"
                    min={datasetBounds.minDate}
                    max={datasetBounds.maxDate}
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="filter-input"
                  />
                </div>
              </>
            )}

            <div className="filter-item">
              <label htmlFor="cutoff-input" className="filter-label">
                <Clock size={14} className="filter-icon" />
                <span>Day D-1 Cutoff (UK Time)</span>
              </label>
              <div className="cutoff-select-wrapper">
                <select
                  id="cutoff-input"
                  value={cutoff}
                  onChange={(e) => setCutoff(e.target.value)}
                  className="filter-select"
                >
                  <option value="09:00">09:00 (Trading Standard)</option>
                  <option value="12:00">12:00 (Midday)</option>
                  <option value="17:00">17:00 (Evening Peak)</option>
                  <option value="23:00">23:00 (End of Day D-1)</option>
                </select>
              </div>
            </div>
          </div>

          <div className="filter-actions">
            {!isDecisionPage && (
              <>
                <button
                  type="button"
                  onClick={handlePresetFullMonth}
                  className="preset-btn"
                  title="January 2026 Purchase Window (2 Jan - 1 Feb)"
                >
                  <Sparkles size={13} />
                  <span>Jan Scope</span>
                </button>
                <button
                  type="button"
                  onClick={handlePresetFirstWeek}
                  className="preset-btn"
                  title="First 7 delivery days"
                >
                  <span>Week 1</span>
                </button>
              </>
            )}
            <button
              type="button"
              onClick={resetFilters}
              className="preset-btn reset-btn"
              title="Reset to default settings"
            >
              <RotateCcw size={13} />
              <span>Reset</span>
            </button>
          </div>
        </div>
      </section>

      {/* Main Page Content */}
      <main className="main-content">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <div className="footer-container">
          <p>
            Data source: Elexon BMRS (<code>FUELHH WIND</code> & <code>WINDFOR</code>). Internal timestamps processed in timezone-aware UTC.
          </p>
        </div>
      </footer>
    </div>
  )
}
