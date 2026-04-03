/**
 * 处理日志面板组件
 */
interface LogsPanelProps {
  logs: string[]
  framework?: any
  allPapersCount?: number
  filteredPapersCount?: number
  statistics?: any
}

export function LogsPanel({ logs, framework, allPapersCount, filteredPapersCount, statistics }: LogsPanelProps) {
  if (!logs || logs.length === 0) {
    return (
      <div className="logs-placeholder">
        <p>暂无日志</p>
        <p className="hint">点击"查找文献"或"生成综述"按钮后，此处将显示处理过程的详细日志。</p>
      </div>
    )
  }

  return (
    <div className="logs-panel">
      <div className="logs-header">
        <h3>📋 处理日志</h3>
        <div className="logs-summary">
          {allPapersCount !== undefined && (
            <span className="summary-item">搜索到: {allPapersCount} 篇</span>
          )}
          {filteredPapersCount !== undefined && (
            <span className="summary-item">筛选后: {filteredPapersCount} 篇</span>
          )}
        </div>
      </div>

      <div className="logs-content">
        {logs.map((log, index) => {
          // 判断日志类型以设置样式
          let className = 'log-line'
          if (log.includes('[阶段')) {
            className += ' log-stage'
          } else if (log.includes('[错误]') || log.includes('失败')) {
            className += ' log-error'
          } else if (log.includes('完成') || log.includes('✓')) {
            className += ' log-success'
          } else if (log.includes('警告') || log.includes('○')) {
            className += ' log-warning'
          }

          return (
            <div key={index} className={className}>
              {log}
            </div>
          )
        })}
      </div>

      {/* 统计信息 */}
      {statistics && (
        <div className="logs-statistics">
          <h4>统计信息</h4>
          <div className="stats-grid">
            <div className="stat-item">
              <span className="stat-label">总文献数：</span>
              <span className="stat-value">{statistics.total}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">近5年文献：</span>
              <span className="stat-value">{statistics.recent_count} ({(statistics.recent_ratio * 100).toFixed(1)}%)</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">英文文献：</span>
              <span className="stat-value">{statistics.english_count} ({(statistics.english_ratio * 100).toFixed(1)}%)</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">总被引次数：</span>
              <span className="stat-value">{statistics.total_citations}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">平均被引：</span>
              <span className="stat-value">{statistics.avg_citations.toFixed(1)}</span>
            </div>
          </div>
        </div>
      )}

      {/* 综述框架信息 */}
      {framework && framework.outline && (
        <div className="logs-framework">
          <h4>综述框架</h4>
          <div className="framework-content">
            <p><strong>结构类型：</strong>{framework.outline.structure || '通用结构'}</p>
            {framework.outline.body_sections && (
              <div className="framework-sections">
                <strong>主体章节：</strong>
                <ul>
                  {framework.outline.body_sections.map((section: any, idx: number) => (
                    <li key={idx}>
                      {section.title}
                      {section.search_keywords && (
                        <span className="keywords">（关键词: {section.search_keywords.join(', ')}）</span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
