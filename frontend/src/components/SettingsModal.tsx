/**
 * 设置弹窗组件
 */
import { useState } from 'react'

interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
  targetCount: number
  recentYearsRatio: number
  englishRatio: number
  searchYears: number
  maxSearchQueries: number
  onTargetCountChange: (value: number) => void
  onRecentYearsRatioChange: (value: number) => void
  onEnglishRatioChange: (value: number) => void
  onSearchYearsChange: (value: number) => void
  onMaxSearchQueriesChange: (value: number) => void
  disabled: boolean
}

export function SettingsModal({
  isOpen,
  onClose,
  targetCount,
  recentYearsRatio,
  englishRatio,
  searchYears,
  maxSearchQueries,
  onTargetCountChange,
  onRecentYearsRatioChange,
  onEnglishRatioChange,
  onSearchYearsChange,
  onMaxSearchQueriesChange,
  disabled
}: SettingsModalProps) {
  const [showAdvanced, setShowAdvanced] = useState(false)

  if (!isOpen) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>⚙️ 生成参数配置</h2>
          <button className="modal-close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="modal-body">
          <div className="config-grid">
            {/* 基本配置 */}
            <div className="config-item">
              <label>
                目标文献数量
                <span className="config-value">{targetCount}</span>
              </label>
              <input
                type="range"
                min="10"
                max="100"
                step="10"
                value={targetCount}
                onChange={(e) => onTargetCountChange(parseInt(e.target.value))}
                disabled={disabled}
                className="config-slider"
              />
              <div className="config-range-labels">
                <span>10</span>
                <span>100</span>
              </div>
            </div>

            <div className="config-item">
              <label>
                近5年文献占比
                <span className="config-value">{(recentYearsRatio * 100).toFixed(0)}%</span>
              </label>
              <input
                type="range"
                min="0.5"
                max="1.0"
                step="0.1"
                value={recentYearsRatio}
                onChange={(e) => onRecentYearsRatioChange(parseFloat(e.target.value))}
                disabled={disabled}
                className="config-slider"
              />
              <div className="config-range-labels">
                <span>50%</span>
                <span>100%</span>
              </div>
              <small className="config-hint">要求：不低于50%</small>
            </div>

            <div className="config-item">
              <label>
                英文文献占比
                <span className="config-value">{(englishRatio * 100).toFixed(0)}%</span>
              </label>
              <input
                type="range"
                min="0.3"
                max="0.7"
                step="0.1"
                value={englishRatio}
                onChange={(e) => onEnglishRatioChange(parseFloat(e.target.value))}
                disabled={disabled}
                className="config-slider"
              />
              <div className="config-range-labels">
                <span>30%</span>
                <span>70%</span>
              </div>
              <small className="config-hint">要求：30%-70%之间</small>
            </div>
          </div>

          {/* 高级配置 */}
          <div className="config-advanced-toggle">
            <button
              className="toggle-advanced-btn"
              onClick={() => setShowAdvanced(!showAdvanced)}
            >
              {showAdvanced ? '▼ 收起高级配置' : '▶ 高级配置'}
            </button>
          </div>

          {showAdvanced && (
            <div className="config-advanced">
              <div className="config-item">
                <label>
                  搜索年份范围
                  <span className="config-value">{searchYears} 年</span>
                </label>
                <input
                  type="range"
                  min="5"
                  max="30"
                  step="5"
                  value={searchYears}
                  onChange={(e) => onSearchYearsChange(parseInt(e.target.value))}
                  disabled={disabled}
                  className="config-slider"
                />
                <div className="config-range-labels">
                  <span>5年</span>
                  <span>30年</span>
                </div>
                <small className="config-hint">搜索最近N年发表的文献</small>
              </div>

              <div className="config-item">
                <label>
                  最多搜索查询数
                  <span className="config-value">{maxSearchQueries} 个</span>
                </label>
                <input
                  type="range"
                  min="1"
                  max="20"
                  step="1"
                  value={maxSearchQueries}
                  onChange={(e) => onMaxSearchQueriesChange(parseInt(e.target.value))}
                  disabled={disabled}
                  className="config-slider"
                />
                <div className="config-range-labels">
                  <span>1</span>
                  <span>20</span>
                </div>
                <small className="config-hint">最多使用多少个搜索查询</small>
              </div>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="modal-close-btn-primary" onClick={onClose}>完成</button>
        </div>
      </div>
    </div>
  )
}
