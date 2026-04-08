import { useState, useEffect } from 'react'
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom'
import { ReviewViewer } from './ReviewViewer'
import { PaymentModal } from './PaymentModal'
import { ConfirmModal } from './ConfirmModal'
import { api } from '../api'
import type { Paper } from '../types'
import './ReviewPage.css'

interface ReviewState {
  title: string
  content: string
  papers: Paper[]
  recordId?: number
  isPublic?: boolean
  isPaid?: boolean
}

type TabType = 'content' | 'references'

export function ReviewPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const taskId = searchParams.get('task_id') || ''
  const state = location.state as ReviewState | null

  // 通过 taskId 加载的数据
  const [taskData, setTaskData] = useState<{
    title: string
    content: string
    papers: Paper[]
    recordId?: number
    isPublic: boolean
    isPaid: boolean
  } | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState<TabType>('content')
  const [showPayModal, setShowPayModal] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [unlockMode, setUnlockMode] = useState(false)
  const [showCreditConfirmModal, setShowCreditConfirmModal] = useState(false)
  const [credits, setCredits] = useState<number>(0)
  const [freeCredits, setFreeCredits] = useState<number>(0)

  // 计算文档显示状态（优先使用 API 返回的 taskData，fallback 到 state）
  const isPublicDocument = taskData?.isPublic ?? false
  const isPaidDocument = taskData?.isPaid ?? state?.isPaid ?? false
  const shouldShowWatermark = !isPublicDocument && !isPaidDocument
  const canExportDirectly = isPublicDocument || isPaidDocument

  // 加载用户额度
  useEffect(() => {
    api.getCredits().then(data => {
      setCredits(data.credits)
      setFreeCredits(data.free_credits)
    }).catch(() => {})
  }, [])

  // 如果 URL 中有 taskId，从后端加载完整数据（确保 isPaid/isPublic 正确）
  useEffect(() => {
    if (taskId) {
      setLoading(true)
      api.getTaskReview(taskId)
        .then(res => {
          if (res.success && res.data) {
            setTaskData({
              title: res.data.topic,
              content: res.data.review,
              papers: res.data.papers || [],
              recordId: res.data.record_id,
              isPublic: res.data.is_public,
              isPaid: res.data.is_paid,
            })
          } else {
            setError('综述不存在或尚未完成')
          }
        })
        .catch(err => {
          setError('加载失败：' + (err.response?.data?.detail || err.message))
        })
        .finally(() => setLoading(false))
    } else if (!state) {
      // 没有 taskId 也没有 state，回到首页
      navigate('/')
    }
  }, [taskId, state])

  // 确定使用哪个数据源
  const reviewData = state || taskData

  if (error) {
    return (
      <div className="review-page">
        <div className="review-page-header">
          <button className="back-button" onClick={() => navigate(-1)}>← 返回</button>
        </div>
        <div style={{ textAlign: 'center', padding: '4rem', color: '#666' }}>{error}</div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="review-page">
        <div className="review-page-header">
          <button className="back-button" onClick={() => navigate(-1)}>← 返回</button>
        </div>
        <div style={{ textAlign: 'center', padding: '4rem', color: '#666' }}>加载中...</div>
      </div>
    )
  }

  if (!reviewData || !reviewData.content) {
    // taskId 场景下，数据还在加载中或加载失败（error 已在上面处理）
    if (taskId) {
      return (
        <div className="review-page">
          <div className="review-page-header">
            <button className="back-button" onClick={() => navigate(-1)}>← 返回</button>
          </div>
          <div style={{ textAlign: 'center', padding: '4rem', color: '#666' }}>
            {loading ? '加载中...' : '综述数据为空'}
          </div>
        </div>
      )
    }
    navigate('/')
    return null
  }

  const handleBack = () => {
    navigate(-1)
  }

  const handleRegenerate = () => {
    sessionStorage.setItem('pending_topic', reviewData.title)
    navigate('/')
  }


  const doExport = async () => {
    if (!reviewData.recordId) {
      alert('该综述暂不支持导出')
      return
    }
    setExporting(true)
    try {
      const token = localStorage.getItem('auth_token')
      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      if (token) headers.Authorization = `Bearer ${token}`
      const response = await fetch('/api/records/export', {
        method: 'POST',
        headers,
        body: JSON.stringify({ record_id: reviewData.recordId })
      })
      if (!response.ok) throw new Error('导出失败')
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const filename = reviewData.title.replace(/[\/\\:]/g, '-')
      a.download = `${filename}.docx`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      alert('导出失败，请稍后重试')
      console.error(err)
    } finally {
      setExporting(false)
    }
  }

  const handleConfirmUseCredit = async () => {
    if (!reviewData.recordId) return

    setShowCreditConfirmModal(false)
    setExporting(true)

    try {
      const result = await api.unlockRecordWithCredit(reviewData.recordId)
      if (result.success) {
        // 刷新额度
        const creditsData = await api.getCredits()
        setCredits(creditsData.credits)
        setFreeCredits(creditsData.free_credits)

        // 刷新任务数据（is_paid 状态已更新）
        if (taskId) {
          api.getTaskReview(taskId).then(res => {
            if (res.success && res.data) {
              setTaskData({
                title: res.data.topic,
                content: res.data.review,
                papers: res.data.papers || [],
                recordId: res.data.record_id,
                isPublic: res.data.is_public,
                isPaid: res.data.is_paid,
              })
            }
          }).catch(() => {})
        }

        // 直接导出
        await doExport()
      } else {
        alert(result.message || '解锁失败，请稍后重试')
      }
    } catch (err) {
      console.error('解锁失败:', err)
      alert('解锁失败，请稍后重试')
    } finally {
      setExporting(false)
    }
  }

  const handleExportWord = async () => {
    // 公开文档或已付费文档，直接导出
    if (canExportDirectly) {
      await doExport()
      return
    }

    // 免费生成的综述，检查是否有付费额度
    if (credits > 0) {
      // 有额度，弹出确认框
      setShowCreditConfirmModal(true)
      return
    }

    // 没有额度，弹出单次解锁支付弹窗
    setUnlockMode(true)
    setShowPayModal(true)
  }

  return (
    <div className="review-page">
      <div className="review-page-header">
        <button className="back-button" onClick={handleBack}>
          ← 返回
        </button>
        <div className="review-segmented-tabs">
          <button
            className={`segmented-tab ${activeTab === 'content' ? 'active' : ''}`}
            onClick={() => setActiveTab('content')}
          >
            正文
          </button>
          <button
            className={`segmented-tab ${activeTab === 'references' ? 'active' : ''}`}
            onClick={() => setActiveTab('references')}
          >
            参考文献
          </button>
        </div>
        <div className="header-actions">
          <button className="regenerate-button" onClick={handleRegenerate}>
            重新生成
          </button>

          <button className={`export-button export-word-btn ${!canExportDirectly ? 'export-word-premium' : ''}`} onClick={handleExportWord} disabled={exporting}>
            {exporting ? '导出中...' :
             canExportDirectly ? '导出 Word' :
             '🔒 解锁导出 (29.8元)'}
          </button>
        </div>
      </div>
      {activeTab === 'content' && (
        <h2 className="review-inline-title">{reviewData.title}</h2>
      )}
      {activeTab === 'content' ? (
        <ReviewViewer
          title={reviewData.title}
          content={reviewData.content}
          papers={[]}
          hasPurchased={!shouldShowWatermark}
        />
      ) : (
        reviewData.papers.length > 0 ? (
          <div className="review-references" style={{ maxWidth: 960, margin: '0 auto', padding: '2rem' }}>
            <h2>参考文献</h2>
            <p className="references-summary">
              共 {reviewData.papers.length} 篇文献
              {(() => {
                const currentYear = new Date().getFullYear()
                const recentCount = reviewData.papers.filter(p => p.year >= currentYear - 5).length
                const englishCount = reviewData.papers.filter(p => p.is_english).length
                const total = reviewData.papers.length
                const parts = []
                if (total > 0) {
                  parts.push(`近5年 ${Math.round(recentCount / total * 100)}%`)
                  parts.push(`英文 ${Math.round(englishCount / total * 100)}%`)
                }
                return parts.length > 0 ? ` · ${parts.join(' · ')}` : ''
              })()}
            </p>
            <div className="references-notice">
              <span className="notice-icon">💡</span>
              <span className="notice-text">
                点击文献标题或右侧平台图标，可在第三方平台验证文献真实性
              </span>
            </div>
            <ol className="references-list">
              {reviewData.papers.map((paper, index) => {
                const searchQuery = encodeURIComponent(paper.title)
                const verificationLinks = [
                  { name: 'Google Scholar', url: `https://scholar.google.com/scholar?q=${searchQuery}`, icon: '🔬', color: '#4285f4' },
                  { name: '百度学术', url: `https://xueshu.baidu.com/s?wd=${searchQuery}`, icon: '🎓', color: '#2932e1' },
                  ...(paper.doi ? [{ name: 'DOI', url: `https://doi.org/${paper.doi}`, icon: '🔗', color: '#7f8c8d' }] : [])
                ]
                return (
                  <li key={paper.id} className="reference-item">
                    <div className="reference-header">
                      <span className="ref-number">{index + 1}.</span>
                      <div className="ref-verification">
                        {verificationLinks.map((link) => (
                          <a
                            key={link.name}
                            href={link.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="verification-link"
                            title={`在 ${link.name} 中验证`}
                            style={{ '--link-color': link.color } as any}
                          >
                            <span className="link-icon">{link.icon}</span>
                            <span className="link-name">{link.name}</span>
                          </a>
                        ))}
                      </div>
                    </div>
                    <div className="ref-content">
                      <a
                        href={verificationLinks[0]?.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="ref-title-link"
                        title="点击在第三方平台查看"
                      >
                        {paper.title}
                      </a>
                      <div className="ref-meta">
                        <span className="ref-authors">{paper.authors.join(', ')}</span>
                        <span className="ref-year"> ({paper.year})</span>
                      </div>
                    </div>
                  </li>
                )
              })}
            </ol>
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '4rem', color: '#666' }}>
            暂无参考文献
          </div>
        )
      )}
      {showPayModal && unlockMode && (
        <PaymentModal
          onClose={() => {
            setShowPayModal(false)
            setUnlockMode(false)
          }}
          onPaymentSuccess={async () => {
            setShowPayModal(false)
            setUnlockMode(false)
            // 刷新任务数据（is_paid 状态已更新）
            if (taskId) {
              api.getTaskReview(taskId).then(res => {
                if (res.success && res.data) {
                  setTaskData({
                    title: res.data.topic,
                    content: res.data.review,
                    papers: res.data.papers || [],
                    recordId: res.data.record_id,
                    isPublic: res.data.is_public,
                    isPaid: res.data.is_paid,
                  })
                }
              }).catch(() => {})
            }
          }}
          planType="unlock"
          recordId={reviewData.recordId}
        />
      )}
      {showPayModal && !unlockMode && (
        <PaymentModal
          onClose={() => setShowPayModal(false)}
          onPaymentSuccess={async () => {
            setShowPayModal(false)
          }}
          planType="single"
        />
      )}

      {/* 使用额度确认弹窗 */}
      {showCreditConfirmModal && (
        <ConfirmModal
          title="使用套餐额度解锁"
          message={`您有 ${credits} 个付费额度。\n是否使用 1 个额度解锁此综述并导出 Word？`}
          confirmText="使用额度解锁"
          cancelText="取消"
          onConfirm={handleConfirmUseCredit}
          onCancel={() => setShowCreditConfirmModal(false)}
          type="warning"
        />
      )}
    </div>
  )
}
