/**
 * 搜索查询面板组件
 * 展示关键词拆分和搜索结果
 */
import { SearchQueryResult } from '../types'

interface SearchQueriesPanelProps {
  searchQueries: SearchQueryResult[]
  allPapersCount: number
  citedPapersCount: number
}

export function SearchQueriesPanel({
  searchQueries,
  allPapersCount,
  citedPapersCount
}: SearchQueriesPanelProps) {
  if (!searchQueries || searchQueries.length === 0) {
    return (
      <div className="search-queries-placeholder">
        <p>请先生成综述以查看搜索查询信息</p>
      </div>
    )
  }

  // 计算总搜索到的论文数（去重前）
  const totalSearched = searchQueries.reduce((sum, q) => sum + q.papers.length, 0)

  return (
    <div className="search-queries-panel">
      {/* 统计概览 */}
      <div className="search-overview">
        <div className="overview-card">
          <div className="overview-label">关键词组合</div>
          <div className="overview-value">{searchQueries.length}</div>
        </div>
        <div className="overview-card">
          <div className="overview-label">搜索到文献</div>
          <div className="overview-value">{totalSearched}</div>
        </div>
        <div className="overview-card">
          <div className="overview-label">去重后文献</div>
          <div className="overview-value">{allPapersCount}</div>
        </div>
        <div className="overview-card highlighted">
          <div className="overview-label">被引用文献</div>
          <div className="overview-value">{citedPapersCount}</div>
        </div>
      </div>

      {/* 搜索查询列表 */}
      <div className="search-queries-list">
        {searchQueries.map((queryResult, index) => (
          <SearchQueryCard key={index} queryResult={queryResult} index={index} />
        ))}
      </div>
    </div>
  )
}

interface SearchQueryCardProps {
  queryResult: SearchQueryResult
  index: number
}

function SearchQueryCard({ queryResult, index }: SearchQueryCardProps) {
  const { query, section, papers, citedCount } = queryResult

  // 计算引用率
  const citationRate = papers.length > 0 ? ((citedCount / papers.length) * 100).toFixed(1) : '0.0'

  return (
    <div className="search-query-card">
      <div className="query-card-header">
        <div className="query-number">#{index + 1}</div>
        <div className="query-section-tag">{section}</div>
        <div className="query-stats">
          <span className="stat-item">
            <span className="stat-label">搜索到:</span>
            <span className="stat-value">{papers.length}</span>
          </span>
          <span className="stat-item">
            <span className="stat-label">被引用:</span>
            <span className="stat-value cited">{citedCount}</span>
          </span>
          <span className="stat-item">
            <span className="stat-label">引用率:</span>
            <span className="stat-value">{citationRate}%</span>
          </span>
        </div>
      </div>

      <div className="query-text-display">
        <span className="query-label">查询:</span>
        <code className="query-string">{query}</code>
      </div>

      {papers.length > 0 && (
        <div className="query-papers-preview">
          <details>
            <summary className="papers-preview-toggle">
              查看匹配的文献 ({papers.length} 篇)
            </summary>
            <div className="papers-preview-list">
              {papers.slice(0, 10).map((paper, paperIndex) => (
                <div key={paper.id || paperIndex} className="preview-paper-item">
                  <span className="preview-paper-number">[{paperIndex + 1}]</span>
                  <span className="preview-paper-title">{paper.title}</span>
                  <span className={`preview-paper-status ${paper.cited ? 'cited' : 'uncited'}`}>
                    {paper.cited ? '✓ 已引用' : '未引用'}
                  </span>
                </div>
              ))}
              {papers.length > 10 && (
                <div className="papers-preview-more">
                  还有 {papers.length - 10} 篇文献...
                </div>
              )}
            </div>
          </details>
        </div>
      )}
    </div>
  )
}
