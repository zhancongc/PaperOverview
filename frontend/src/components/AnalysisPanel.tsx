/**
 * 智能分析面板组件
 */
import { TopicClassification } from '../types'

interface AnalysisPanelProps {
  classification: TopicClassification | null
  frameworkType: string
}

export function AnalysisPanel({ classification, frameworkType }: AnalysisPanelProps) {
  if (!classification) {
    return (
      <div className="analysis-placeholder">
        <p>请先进行智能分析</p>
      </div>
    )
  }

  const { type_name, classification_reason, outline, search_queries } = classification

  return (
    <div className="analysis-panel">
      <div className="analysis-header">
        <h3>📊 题目类型分析</h3>
        <div className="type-badge">
          <span className="type-label">类型：</span>
          <span className="type-value">{type_name}</span>
        </div>
      </div>

      <div className="analysis-content">
        <div className="analysis-reason">
          <h4>判定依据：</h4>
          <p>{classification_reason}</p>
        </div>

        <div className="framework-info">
          <h4>综述框架：</h4>
          <p>{frameworkType === 'three-circles' ? '三圈交集式（研究对象+优化目标+方法论）' :
               frameworkType === 'pyramid' ? '金字塔式（理论基础→指标体系→方法技术→实践应用）' :
               frameworkType === 'problem-solution' ? '问题-方案式（研究问题→理论基础→影响机制）' :
               '通用结构'}
          </p>
        </div>

        {/* 显示大纲信息 */}
        {outline && (
          <div className="outline-info">
            <h4>📝 生成大纲：</h4>
            <div className="outline-sections">
              <div className="outline-section">
                <h5>引言</h5>
                <p>{outline.introduction?.focus || 'N/A'}</p>
              </div>
              {outline.body_sections && outline.body_sections.length > 0 && (
                <div className="outline-body">
                  <h5>主体章节 ({outline.body_sections.length} 个)</h5>
                  <ul>
                    {outline.body_sections.map((section, index) => (
                      <li key={index}>
                        <strong>{section.title}</strong>
                        {section.search_keywords && section.search_keywords.length > 0 && (
                          <span className="keywords-badge">
                            关键词: {section.search_keywords.join(', ')}
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 显示搜索关键词 */}
        {search_queries && search_queries.length > 0 && (
          <div className="search-queries-info">
            <h4>🔍 搜索关键词 ({search_queries.length} 个)</h4>
            <div className="keywords-list">
              {search_queries.map((query, index) => (
                <div key={index} className="keyword-item">
                  <span className="keyword-section">{query.section}</span>
                  <span className="keyword-text">{query.query}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
