import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { getLocalUserInfo, isLoggedIn } from '../authApi'
import { PaymentModal } from './PaymentModal'
import type { ReviewRecord } from '../types'
import './ProfilePage.css'

export function ProfilePage() {
  const navigate = useNavigate()
  const [records, setRecords] = useState<ReviewRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [userInfo, setUserInfo] = useState<any>(null)
  const [credits, setCredits] = useState<number>(0)
  const [freeCredits, setFreeCredits] = useState<number>(0)
  const [showPayModal, setShowPayModal] = useState(false)
  const [pendingExportRecordId, setPendingExportRecordId] = useState<number | null>(null)
  const [exportingId, setExportingId] = useState<number | null>(null)
  const [unlockMode, setUnlockMode] = useState(false)  // true=单次解锁, false=购买套餐

  useEffect(() => {
    if (!isLoggedIn()) {
      navigate('/login')
      return
    }
    setUserInfo(getLocalUserInfo())
    loadRecords()
    api.getCredits().then(data => {
      setCredits(data.credits)
      setFreeCredits(data.free_credits)
    }).catch(() => {})
  }, [])

  const loadRecords = async () => {
    setLoading(true)
    try {
      const response = await api.getRecords()
      if (response.success) {
        setRecords(response.records)
      }
    } catch (err) {
      console.error('加载历史记录失败:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleViewRecord = (record: ReviewRecord) => {
    if (record.status === 'processing' || record.status === 'failed') {
      // 生成中或失败的任务，引导重新生成
      sessionStorage.setItem('pending_topic', record.topic)
      navigate('/')
      return
    }
    if (record.task_id) {
      navigate(`/review?task_id=${record.task_id}`)
    } else if (record.id) {
      navigate('/review', {
        state: {
          title: record.topic,
          content: record.review,
          papers: record.papers,
          recordId: record.id,
          isPaid: record.is_paid ?? false,
        }
      })
    }
  }

  const handleExportRecord = async (id: number, event: React.MouseEvent) => {
    event.stopPropagation()
    const record = records.find(r => r.id === id)
    if (!record) return

    // 已付费生成的综述，直接导出
    if (record.is_paid) {
      setExportingId(id)
      try {
        const blob = await api.exportReview(id)
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        const filename = record.topic.replace(/[\/\\:]/g, '-')
        a.download = `${filename}.docx`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
      } catch (err) {
        console.error('导出失败:', err)
        alert('导出失败，请稍后重试')
      } finally {
        setExportingId(null)
      }
      return
    }

    // 免费生成的综述，弹出单次解锁支付弹窗
    setUnlockMode(true)
    setPendingExportRecordId(id)
    setShowPayModal(true)
  }

  const handleLogout = () => {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user_info')
    navigate('/')
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
    <div className="profile-page">
      {/* 顶部导航栏 */}
      <nav className="profile-nav">
        <div className="nav-logo" onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>
          <span className="logo-icon">📚</span>
          <span className="logo-text">AutoOverview</span>
        </div>
        <div className="nav-actions">
          <button className="nav-btn nav-btn-home" onClick={() => navigate('/')}>
            首页
          </button>
          <button className="nav-btn nav-btn-logout" onClick={handleLogout}>
            退出登录
          </button>
        </div>
      </nav>

      <div className="profile-container">
        {/* 用户信息区域 */}
        <div className="profile-header">
          <div className="user-avatar-large">👤</div>
          <div className="user-info-section">
            <h1 className="user-name">{userInfo?.nickname || '用户'}</h1>
            <p className="user-email">{userInfo?.email || ''}</p>
          </div>
        </div>

        {/* 统计信息 */}
        <div className="profile-stats">
          <div className="stat-card">
            <div className="stat-number">{records.length}</div>
            <div className="stat-label">综述数量</div>
          </div>
          <div className="stat-card stat-card-free">
            <div className="stat-number">{freeCredits}</div>
            <div className="stat-label">免费额度</div>
          </div>
          <div className="stat-card stat-card-paid">
            <div className="stat-number">{credits - freeCredits}</div>
            <div className="stat-label">套餐额度</div>
          </div>
        </div>

        {/* 历史记录列表 */}
        <div className="profile-history">
          <h2 className="history-title">📖 我的综述</h2>

          {loading ? (
            <div className="history-loading">
              <div className="spinner"></div>
              <p>加载历史记录中...</p>
            </div>
          ) : records.length === 0 ? (
            <div className="history-empty">
              <div className="empty-icon">📝</div>
              <p className="empty-title">还没有生成过综述</p>
              <p className="empty-desc">输入研究主题，AI 为您自动搜索文献并生成专业综述</p>
              <button className="empty-button" onClick={() => navigate('/')}>
                去生成第一篇综述
              </button>
            </div>
          ) : (
            <div className="records-list">
              {records.map((record) => (
                <div
                  key={record.id}
                  className={`record-item ${record.status === 'processing' || record.status === 'failed' ? 'record-item-disabled' : ''}`}
                  onClick={() => handleViewRecord(record)}
                >
                  <div className="record-main">
                    <div className="record-top">
                      <h3 className="record-topic">{record.topic}</h3>
                      <div className="record-status-badge">
                        {record.status === 'success' ? (
                          <span className="status-success">✓ 完成</span>
                        ) : record.status === 'failed' ? (
                          <span className="status-failed">✗ 失败 · 点击重新生成</span>
                        ) : (
                          <span className="status-processing">⏳ 进行中</span>
                        )}
                      </div>
                      {record.status === 'success' && (
                        <button
                          className={`export-button export-word-btn ${!record.is_paid ? 'export-word-premium' : ''}`}
                          onClick={(e) => handleExportRecord(record.id, e)}
                          disabled={exportingId === record.id}
                        >
                          {exportingId === record.id ? '导出中...' :
                           record.is_paid ? '导出 Word' :
                           '🔒 解锁导出 (29.8元)'}
                        </button>
                      )}
                    </div>
                    <div className="record-info">
                      <span className="record-time">{formatDate(record.created_at)}</span>
                      {record.statistics && (
                        <div className="record-stats-inline">
                          <span>📄 {record.statistics.total || 0} 篇文献</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 页脚 */}
      <footer className="profile-footer">
        <div className="footer-content">
          <p className="footer-copyright">© 2026 AutoOverview. All rights reserved.</p>
          <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer" className="footer-icp">
            沪ICP备2023018158号-4
          </a>
        </div>
      </footer>

      {/* 支付弹窗 */}
      {showPayModal && unlockMode && pendingExportRecordId !== null && (
        <PaymentModal
          onClose={() => {
            setShowPayModal(false)
            setUnlockMode(false)
            setPendingExportRecordId(null)
          }}
          onPaymentSuccess={async () => {
            setShowPayModal(false)
            setUnlockMode(false)
            // 刷新记录列表
            await loadRecords()
            // 继续导出
            if (pendingExportRecordId !== null) {
              handleExportRecord(pendingExportRecordId, { stopPropagation: () => {} } as React.MouseEvent)
              setPendingExportRecordId(null)
            }
          }}
          planType="unlock"
          recordId={pendingExportRecordId}
        />
      )}
      {showPayModal && !unlockMode && (
        <PaymentModal
          onClose={() => {
            setShowPayModal(false)
            setPendingExportRecordId(null)
          }}
          onPaymentSuccess={async () => {
            setShowPayModal(false)
            // 刷新用户状态和记录列表
            const creditsData = await api.getCredits()
            setCredits(creditsData.credits)
            setFreeCredits(creditsData.free_credits)
            await loadRecords()
            // 如果有待导出的记录，继续导出
            if (pendingExportRecordId !== null) {
              handleExportRecord(pendingExportRecordId, { stopPropagation: () => {} } as React.MouseEvent)
              setPendingExportRecordId(null)
            }
          }}
          planType="single"
        />
      )}
    </div>
  )
}
