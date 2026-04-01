/**
 * 搜索查询面板组件
 * 展示关键词拆分和搜索结果
 */
import { useState } from 'react'
import { SearchQueryResult, Paper } from '../types'

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
  const [showAllPapers, setShowAllPapers] = useState(false)

  if (!searchQueries || searchQueries.length === 0) {
    return (
      <div className="search-queries-placeholder">
        <p>请先生成综述以查看搜索查询信息</p>
      </div>
    )
  }

  // 计算总搜索到的论文数（去重前）
  const totalSearched = searchQueries.reduce((sum, q) => sum + q.papers.length, 0)

  // 收集所有论文（去重）
  const allPapersMap = new Map<string, Paper>()
  searchQueries.forEach(queryResult => {
    queryResult.papers.forEach(paper => {
      if (!allPapersMap.has(paper.id)) {
        allPapersMap.set(paper.id, paper)
      }
    })
  })
  const allPapers = Array.from(allPapersMap.values()).sort((a, b) => {
    // 按相关性得分降序排序
    const scoreA = a.relevance_score || 0
    const scoreB = b.relevance_score || 0
    return scoreB - scoreA
  })

  // 按相关性分组
  const highRelevance = allPapers.filter(p => (p.relevance_score || 0) >= 70)
  const mediumRelevance = allPapers.filter(p => (p.relevance_score || 0) >= 40 && (p.relevance_score || 0) < 70)
  const lowRelevance = allPapers.filter(p => (p.relevance_score || 0) < 40)

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

      {/* 所有文献卡片 */}
      <AllPapersCard
        allPapers={allPapers}
        highRelevance={highRelevance}
        mediumRelevance={mediumRelevance}
        lowRelevance={lowRelevance}
        showAllPapers={showAllPapers}
        onToggle={() => setShowAllPapers(!showAllPapers)}
      />

      {/* 搜索查询列表 */}
      <div className="search-queries-list">
        {searchQueries.map((queryResult, index) => (
          <SearchQueryCard key={index} queryResult={queryResult} index={index} />
        ))}
      </div>
    </div>
  )
}

interface AllPapersCardProps {
  allPapers: Paper[]
  highRelevance: Paper[]
  mediumRelevance: Paper[]
  lowRelevance: Paper[]
  showAllPapers: boolean
  onToggle: () => void
}

function AllPapersCard({
  allPapers,
  highRelevance,
  mediumRelevance,
  lowRelevance,
  showAllPapers,
  onToggle
}: AllPapersCardProps) {
  const citedCount = allPapers.filter(p => p.cited).length
  const uncitedCount = allPapers.length - citedCount

  return (
    <div className="all-papers-card">
      <div className="card-header" onClick={onToggle}>
        <h3>📚 所有文献列表</h3>
        <button className="toggle-button">
          {showAllPapers ? '▼ 收起' : '▶ 展开'}
        </button>
      </div>

      <div className="card-stats">
        <span className="stat-badge total">总计 {allPapers.length} 篇</span>
        <span className="stat-badge cited">✓ 已引用 {citedCount} 篇</span>
        <span className="stat-badge uncited">未引用 {uncitedCount} 篇</span>
      </div>

      {showAllPapers && (
        <div className="all-papers-content">
          {/* 高相关性 */}
          {highRelevance.length > 0 && (
            <div className="relevance-group high">
              <h4>🔥 高相关性 (70+分) - {highRelevance.length} 篇</h4>
              <PapersList papers={highRelevance} limit={20} />
            </div>
          )}

          {/* 中等相关性 */}
          {mediumRelevance.length > 0 && (
            <div className="relevance-group medium">
              <h4>⭐ 中等相关性 (40-70分) - {mediumRelevance.length} 篇</h4>
              <PapersList papers={mediumRelevance} limit={15} />
            </div>
          )}

          {/* 低相关性 */}
          {lowRelevance.length > 0 && (
            <div className="relevance-group low">
              <h4>📄 低相关性 (&lt;40分) - {lowRelevance.length} 篇</h4>
              <PapersList papers={lowRelevance} limit={10} />
            </div>
          )}
        </div>
      )}
    </div>
  )
}

interface PapersListProps {
  papers: Paper[]
  limit?: number
}

function PapersList({ papers, limit }: PapersListProps) {
  const displayPapers = limit ? papers.slice(0, limit) : papers
  const remainingCount = limit && papers.length > limit ? papers.length - limit : 0

  return (
    <div className="papers-list">
      {displayPapers.map((paper, index) => (
        <div key={paper.id} className={`paper-item ${paper.cited ? 'cited' : 'uncited'}`}>
          <div className="paper-item-header">
            <span className="paper-number">[{index + 1}]</span>
            <span className={`paper-score ${getScoreClass(paper.relevance_score || 0)}`}>
              {paper.relevance_score || 0}分
            </span>
            <span className={`paper-status ${paper.cited ? 'status-cited' : 'status-uncited'}`}>
              {paper.cited ? '✓ 已引用' : '未引用'}
            </span>
          </div>
          <div className="paper-title">{paper.title}</div>
          <div className="paper-meta">
            <span>{paper.authors?.slice(0, 2).join(', ')}</span>
            {paper.authors && paper.authors.length > 2 && <span> 等</span>}
            <span className="paper-year">({paper.year})</span>
            <span className="paper-citations">
              被引 {paper.cited_by_count || 0} 次
            </span>
          </div>
        </div>
      ))}
      {remainingCount > 0 && (
        <div className="papers-list-more">
          还有 {remainingCount} 篇文献...
        </div>
      )}
    </div>
  )
}

function getScoreClass(score: number): string {
  if (score >= 70) return 'score-high'
  if (score >= 40) return 'score-medium'
  return 'score-low'
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
