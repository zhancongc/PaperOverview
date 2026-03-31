/**
 * 文献列表组件
 */
import { Paper } from '../types'

interface PapersListProps {
  papers: Paper[]
}

export function PapersList({ papers }: PapersListProps) {
  if (!papers || papers.length === 0) {
    return (
      <div className="papers-placeholder">
        <p>暂无文献数据</p>
      </div>
    )
  }

  return (
    <div className="papers-list">
      <div className="papers-header">
        <h3>📚 文献列表 ({papers.length} 篇)</h3>
      </div>

      <div className="papers-grid">
        {papers.map((paper, index) => (
          <div key={paper.id || index} className="paper-card">
            <div className="paper-number">[{index + 1}]</div>
            <div className="paper-title">
              <a
                href={paper.doi ? `https://doi.org/${paper.doi}` : '#'}
                target="_blank"
                rel="noopener noreferrer"
                className="paper-link"
              >
                {paper.title}
              </a>
            </div>
            <div className="paper-meta">
              <span className="paper-year">{paper.year}</span>
              {paper.is_english !== undefined && (
                <span className={`paper-lang ${paper.is_english ? 'en' : 'cn'}`}>
                  {paper.is_english ? 'EN' : 'CN'}
                </span>
              )}
              {paper.cited_by_count !== undefined && (
                <span className="paper-citations">
                  被引: {paper.cited_by_count}
                </span>
              )}
            </div>
            {paper.abstract && (
              <div className="paper-abstract">
                {paper.abstract.length > 200
                  ? paper.abstract.substring(0, 200) + '...'
                  : paper.abstract
                }
              </div>
            )}
            {paper.authors && paper.authors.length > 0 && (
              <div className="paper-authors">
                作者: {paper.authors.slice(0, 3).join(', ')}
                {paper.authors.length > 3 && ' 等'}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
