/**
 * 配置面板组件
 */
import { useState } from 'react'

interface ConfigPanelProps {
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

export function ConfigPanel({
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
}: ConfigPanelProps) {
  const [showAdvanced, setShowAdvanced] = useState(false)

  return (
    <div className="config-panel">
      <div className="config-header">
        <h3>⚙️ 生成参数配置</h3>
        <button
          className="toggle-advanced-btn"
          onClick={() => setShowAdvanced(!showAdvanced)}
        >
          {showAdvanced ? '▼ 收起高级配置' : '▶ 高级配置'}
        </button>
      </div>

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
            min="0.1"
            max="1.0"
            step="0.1"
            value={recentYearsRatio}
            onChange={(e) => onRecentYearsRatioChange(parseFloat(e.target.value))}
            disabled={disabled}
            className="config-slider"
          />
          <div className="config-range-labels">
            <span>10%</span>
            <span>100%</span>
          </div>
        </div>

        <div className="config-item">
          <label>
            英文文献占比
            <span className="config-value">{(englishRatio * 100).toFixed(0)}%</span>
          </label>
          <input
            type="range"
            min="0.1"
            max="1.0"
            step="0.1"
            value={englishRatio}
            onChange={(e) => onEnglishRatioChange(parseFloat(e.target.value))}
            disabled={disabled}
            className="config-slider"
          />
          <div className="config-range-labels">
            <span>10%</span>
            <span>100%</span>
          </div>
        </div>
      </div>

      {/* 高级配置 */}
      {showAdvanced && (
        <div className="config-advanced">
          <h4>高级配置</h4>

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
  )
}
