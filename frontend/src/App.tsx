import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { api } from './api'
import type { Paper, Statistics, ReviewRecord } from './types'
import './App.css'

function App() {
  const [topic, setTopic] = useState('')
  const [loading, setLoading] = useState(false)
  const [review, setReview] = useState('')
  const [papers, setPapers] = useState<Paper[]>([])
  const [statistics, setStatistics] = useState<Statistics | null>(null)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState<'review' | 'papers' | 'history'>('review')
  const [currentRecordId, setCurrentRecordId] = useState<number | null>(null)

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

  const handleGenerate = async () => {
    if (!topic.trim()) {
      setError('请输入论文主题')
      return
    }

    setLoading(true)
    setError('')
    setReview('')
    setPapers([])
    setStatistics(null)
    setActiveTab('review')

    try {
      const response = await api.generateReview(topic)

      if (response.success && response.data) {
        setReview(response.data.review)
        setPapers(response.data.papers)
        setStatistics(response.data.statistics)
        if (response.data.id) {
          setCurrentRecordId(response.data.id)
        }
        // 刷新历史记录
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

  return (
    <div className="app">
      <header className="header">
        <h1>论文综述生成器</h1>
        <p>输入论文主题，自动生成带50篇参考文献的文献综述</p>
      </header>

      <main className="main">
        <div className="input-section">
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="请输入论文主题，例如：机器学习、深度学习、大语言模型..."
            className="topic-input"
            onKeyDown={(e) => e.key === 'Enter' && handleGenerate()}
            disabled={loading}
          />
          <button
            onClick={handleGenerate}
            disabled={loading || !topic.trim()}
            className="generate-btn"
          >
            {loading ? '生成中...' : '生成综述'}
          </button>
        </div>

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {loading && (
          <div className="loading">
            <div className="spinner"></div>
            <p>正在检索文献并生成综述，请稍候...</p>
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

        {(review || records.length > 0) && (
          <div className="results">
            <div className="tabs">
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
              {activeTab === 'history' ? (
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
                            <button
                              className="delete-btn"
                              onClick={(e) => handleDeleteRecord(record.id, e)}
                            >
                              删除
                            </button>
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
                <div className="empty-state">请先生成综述</div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
