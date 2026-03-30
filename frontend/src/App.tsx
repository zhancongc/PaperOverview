import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { api } from './api'
import type {
  Paper,
  Statistics,
  ReviewRecord,
  TopicClassification,
  ReviewFramework,
  CircleSummary,
  GapAnalysis
} from './types'
import './App.css'

function App() {
  const [topic, setTopic] = useState('')
  const [loading, setLoading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [review, setReview] = useState('')
  const [papers, setPapers] = useState<Paper[]>([])
  const [statistics, setStatistics] = useState<Statistics | null>(null)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState<'review' | 'papers' | 'history' | 'analysis'>('review')
  const [currentRecordId, setCurrentRecordId] = useState<number | null>(null)

  // 分析数据
  const [classification, setClassification] = useState<TopicClassification | null>(null)
  const [framework, setFramework] = useState<ReviewFramework | null>(null)
  const [frameworkType, setFrameworkType] = useState<string>('')

  // 历史记录
  const [records, setRecords] = useState<ReviewRecord[]>([])
  const [loadingHistory, setLoadingHistory] = useState(false)

  // 加载历史记录
  useEffect(() => {
    loadRecords()
  }, [])

  const loadRecords = async () => {
    setLoadingHistory(true)
    try {
      const response = await api.getRecords()
      if (response.success) {
        setRecords(response.records)
      }
    } catch (err) {
      console.error('加载历史记录失败:', err)
    } finally {
      setLoadingHistory(false)
    }
  }

  const handleAnalyze = async () => {
    if (!topic.trim()) {
      setError('请输入论文题目')
      return
    }

    setAnalyzing(true)
    setError('')
    setActiveTab('analysis')
    setClassification(null)
    setFramework(null)

    try {
      const response = await api.smartAnalyze(topic)
      console.log('[App] Smart analyze response:', response)
      if (response.success && response.data) {
        const data = response.data
        console.log('[App] Analysis data:', data)

        setFrameworkType(data.framework_type || '')

        if (data.analysis) {
          console.log('[App] Setting classification:', data.analysis)
          setClassification(data.analysis as unknown as TopicClassification)
        }

        if (data.review_framework) {
          console.log('[App] Setting framework:', data.review_framework)
          setFramework(data.review_framework)
        }
      }
    } catch (err) {
      setError('分析失败，请检查后端服务')
      console.error('[App] Analyze error:', err)
    } finally {
      setAnalyzing(false)
    }
  }

  const handleGenerate = async () => {
    if (!topic.trim()) {
      setError('请输入论文题目')
      return
    }

    setLoading(true)
    setError('')
    setReview('')
    setPapers([])
    setStatistics(null)
    setActiveTab('review')

    try {
      // 使用智能生成接口（会基于分析结果进行聚焦搜索）
      const response = await api.smartGenerate(topic)

      if (response.success && response.data) {
        setReview(response.data.review)
        setPapers(response.data.papers)
        setStatistics(response.data.statistics)
        if (response.data.id) {
          setCurrentRecordId(response.data.id)
        }
        loadRecords()
      } else {
        setError(response.message)
      }
    } catch (err) {
      setError('生成失败，请检查后端服务是否正常运行')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleLoadRecord = async (id: number) => {
    try {
      const response = await api.getRecord(id)
      if (response.success && response.record) {
        const record = response.record
        setTopic(record.topic)
        setReview(record.review)
        setPapers(record.papers)
        setStatistics(record.statistics)
        setCurrentRecordId(record.id)
        setActiveTab('review')
      }
    } catch (err) {
      setError('加载记录失败')
      console.error(err)
    }
  }

  const handleDeleteRecord = async (id: number, event: React.MouseEvent) => {
    event.stopPropagation()
    if (!confirm('确定删除这条记录吗？')) return

    try {
      await api.deleteRecord(id)
      setRecords(records.filter(r => r.id !== id))
    } catch (err) {
      console.error('删除失败:', err)
    }
  }

  const handleExportDocx = async () => {
    if (!review || !statistics) {
      setError('请先生成综述')
      return
    }

    try {
      const blob = await api.exportReview(topic, review, papers, statistics)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${topic.replace(/[\/\\:]/g, '-')}.docx`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      setError('导出失败')
      console.error('导出失败:', err)
    }
  }

  const handleExportRecord = async (id: number, event: React.MouseEvent) => {
    event.stopPropagation()
    try {
      const blob = await api.exportRecord(id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const record = records.find(r => r.id === id)
      const filename = record ? record.topic.replace(/[\/\\:]/g, '-') : 'review'
      a.download = `${filename}.docx`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      setError('导出失败')
      console.error('导出失败:', err)
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getFrameworkIcon = (structure: string) => {
    if (structure.includes('三圈')) return '🔀'
    if (structure.includes('金字塔')) return '🔺'
    if (structure.includes('溯源')) return '📚'
    if (structure.includes('问题')) return '❓'
    return '📄'
  }

  const getTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      'application': '#667eea',
      'evaluation': '#f5576c',
      'theoretical': '#4facfe',
      'empirical': '#43e97b',
      'general': '#999'
    }
    return colors[type] || '#999'
  }

  return (
    <div className="app">
      <header className="header">
        <h1>论文综述生成器</h1>
        <p>智能识别题目类型，自动构建匹配的文献体系与综述框架</p>
      </header>

      <main className="main">
        <div className="input-section">
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="请输入论文题目，例如：制造型企业质量管理成熟度评价研究"
            className="topic-input"
            onKeyDown={(e) => e.key === 'Enter' && handleGenerate()}
            disabled={loading || analyzing}
          />
          <button
            onClick={handleAnalyze}
            disabled={analyzing || loading || !topic.trim()}
            className="analyze-btn"
          >
            {analyzing ? '分析中...' : '🔍 智能分析'}
          </button>
          <button
            onClick={handleGenerate}
            disabled={loading || analyzing || !topic.trim()}
            className="generate-btn"
          >
            {loading ? '生成中...' : '✨ 生成综述'}
          </button>
          {review && statistics && (
            <button
              onClick={handleExportDocx}
              className="export-btn"
            >
              📥 导出Word
            </button>
          )}
        </div>

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {(loading || analyzing) && (
          <div className="loading">
            <div className="spinner"></div>
            <p>{analyzing ? '正在分析题目类型...' : '正在检索文献并生成综述，请稍候...'}</p>
          </div>
        )}

        {statistics && (
          <div className="statistics">
            <div className="stat-item">
              <span className="stat-label">文献总数</span>
              <span className="stat-value">{statistics.total}篇</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">近5年</span>
              <span className="stat-value">{(statistics.recent_ratio * 100).toFixed(0)}%</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">英文文献</span>
              <span className="stat-value">{(statistics.english_ratio * 100).toFixed(0)}%</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">总被引量</span>
              <span className="stat-value">{statistics.total_citations}</span>
            </div>
          </div>
        )}

        {(review || classification || records.length > 0) && (
          <div className="results">
            <div className="tabs">
              {classification && (
                <button
                  className={`tab ${activeTab === 'analysis' ? 'active' : ''}`}
                  onClick={() => setActiveTab('analysis')}
                >
                  分析框架
                </button>
              )}
              <button
                className={`tab ${activeTab === 'review' ? 'active' : ''}`}
                onClick={() => setActiveTab('review')}
                disabled={!review}
              >
                文献综述
              </button>
              <button
                className={`tab ${activeTab === 'papers' ? 'active' : ''}`}
                onClick={() => setActiveTab('papers')}
                disabled={!review}
              >
                参考文献列表 {papers.length > 0 && `(${papers.length})`}
              </button>
              <button
                className={`tab ${activeTab === 'history' ? 'active' : ''}`}
                onClick={() => setActiveTab('history')}
              >
                历史记录 {records.length > 0 && `(${records.length})`}
              </button>
            </div>

            <div className="tab-content">
              {activeTab === 'analysis' && classification ? (
                <div className="analysis-content">
                  {/* 题目分类 */}
                  <div className="analysis-section">
                    <h2>📋 题目分类</h2>
                    <div className="classification-card">
                      <div
                        className="type-badge"
                        style={{ backgroundColor: getTypeColor(classification.type || 'general') }}
                      >
                        {classification.type_name || '未知类型'}
                      </div>
                      <p className="classification-reason">{classification.classification_reason || ''}</p>
                    </div>
                  </div>

                  {/* 框架信息 */}
                  {framework && (
                    <div className="analysis-section">
                      <h2>
                        {getFrameworkIcon(framework.structure || '')} {framework.structure || '框架'}框架
                      </h2>
                      <p className="framework-description">{framework.description || ''}</p>

                      <div className="framework-sections">
                        {(framework.sections || []).map((section: any, index: number) => (
                          <div key={index} className="framework-section-item">
                            <h4>{section.title}</h4>
                            <p className="section-desc">{section.description}</p>
                            <ul className="section-points">
                              {(section.key_points || []).map((point: string, i: number) => (
                                <li key={i}>{point}</li>
                              ))}
                            </ul>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 检索策略 */}
                  {classification.search_queries && classification.search_queries.length > 0 && (
                    <div className="analysis-section">
                      <h2>🔍 文献检索策略</h2>
                      <div className="search-queries">
                        {classification.search_queries.map((query: any, index: number) => (
                          <div key={index} className="query-item">
                            <span className="query-section">{query.section}</span>
                            <span className="query-text">{query.query}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : activeTab === 'history' ? (
                <div className="history-content">
                  {loadingHistory ? (
                    <div className="loading-small">加载中...</div>
                  ) : records.length === 0 ? (
                    <div className="empty-state">暂无历史记录</div>
                  ) : (
                    <div className="records-list">
                      {records.map(record => (
                        <div
                          key={record.id}
                          className="record-item"
                          onClick={() => handleLoadRecord(record.id)}
                        >
                          <div className="record-header">
                            <h3 className="record-topic">{record.topic}</h3>
                            <div className="record-actions">
                              <button
                                className="export-btn"
                                onClick={(e) => handleExportRecord(record.id, e)}
                              >
                                📥 导出
                              </button>
                              <button
                                className="delete-btn"
                                onClick={(e) => handleDeleteRecord(record.id, e)}
                              >
                                删除
                              </button>
                            </div>
                          </div>
                          <div className="record-meta">
                            <span className="record-date">{formatDate(record.created_at)}</span>
                            <span className="record-papers">{record.statistics?.total || 0} 篇文献</span>
                            <span className={`record-status ${record.status}`}>
                              {record.status === 'success' ? '成功' : '失败'}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : activeTab === 'review' && review ? (
                <div className="review-content">
                  <ReactMarkdown>{review}</ReactMarkdown>
                </div>
              ) : activeTab === 'papers' && papers.length > 0 ? (
                <div className="papers-list">
                  {papers.map((paper, index) => (
                    <div key={paper.id} className="paper-item">
                      <div className="paper-number">[{index + 1}]</div>
                      <div className="paper-info">
                        <h3 className="paper-title">{paper.title}</h3>
                        <div className="paper-meta">
                          <span className="paper-authors">
                            {paper.authors.slice(0, 3).join(', ')}
                            {paper.authors.length > 3 && ' 等'}
                          </span>
                          <span className="paper-year">{paper.year}</span>
                          <span className="paper-citations">
                            被引 {paper.cited_by_count} 次
                          </span>
                          {paper.is_english && <span className="paper-lang">英文</span>}
                        </div>
                        {paper.doi && (
                          <a
                            href={`https://doi.org/${paper.doi}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="paper-doi"
                          >
                            DOI: {paper.doi}
                          </a>
                        )}
                        {paper.concepts.length > 0 && (
                          <div className="paper-concepts">
                            {paper.concepts.map((concept) => (
                              <span key={concept} className="concept-tag">
                                {concept}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-state">
                  {classification ? '点击「生成综述」开始生成' : '请先分析题目或直接生成综述'}
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
