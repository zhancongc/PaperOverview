import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { isLoggedIn as checkLoggedIn, getLocalUserInfo, authApi } from '../authApi'
import { LoginModal } from './LoginModal'
import './SimpleApp.css'

interface TaskProgress {
  step: string
  message: string
}

export function SimpleApp() {
  const navigate = useNavigate()
  const [topic, setTopic] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [progress, setProgress] = useState<TaskProgress | null>(null)
  const [error, setError] = useState('')
  const [showLoginModal, setShowLoginModal] = useState(false)
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [userInfo, setUserInfo] = useState<any>(null)

  // 检查登录状态
  useEffect(() => {
    const loggedIn = checkLoggedIn()
    setIsLoggedIn(loggedIn)
    if (loggedIn) {
      setUserInfo(getLocalUserInfo())
    }
  }, [])

  // 恢复之前的主题并自动生成
  useEffect(() => {
    const pendingTopic = sessionStorage.getItem('pending_topic')
    if (pendingTopic && checkLoggedIn()) {
      sessionStorage.removeItem('pending_topic')
      setTopic(pendingTopic)
      setTimeout(() => {
        handleGenerate()
      }, 500)
    }
  }, [isLoggedIn])

  const handleGenerate = async () => {
    if (!topic.trim()) {
      setError('请输入研究主题')
      return
    }

    // 检查是否登录
    if (!checkLoggedIn()) {
      setShowLoginModal(true)
      return
    }

    setIsGenerating(true)
    setProgress({ step: 'init', message: '正在提交任务...' })
    setError('')

    try {
      // 提交任务
      const submitResponse = await api.submitReviewTask(topic, {
        targetCount: 50,
        recentYearsRatio: 0.5,
        englishRatio: 0.3,
        searchYears: 10,
        maxSearchQueries: 8
      })

      if (!submitResponse.success || !submitResponse.data?.task_id) {
        setError(submitResponse.message || '任务提交失败')
        setIsGenerating(false)
        return
      }

      const taskId = submitResponse.data.task_id

      // 轮询任务状态
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await api.getTaskStatus(taskId)

          if (!statusResponse.success) {
            setError('查询任务状态失败')
            setIsGenerating(false)
            clearInterval(pollInterval)
            return
          }

          const taskInfo = statusResponse.data

          // 更新进度
          if (taskInfo.progress) {
            setProgress({
              step: taskInfo.progress.step,
              message: taskInfo.progress.message
            })
          }

          // 检查是否完成
          if (taskInfo.status === 'completed' && taskInfo.result) {
            clearInterval(pollInterval)
            setProgress({ step: 'completed', message: '生成完成！正在跳转...' })

            const data = taskInfo.result

            // 跳转到综述展示页面
            setTimeout(() => {
              navigate('/review', {
                state: {
                  title: topic,
                  content: data.review,
                  papers: data.papers || [],
                  recordId: data.id
                }
              })
            }, 500)

          } else if (taskInfo.status === 'failed') {
            clearInterval(pollInterval)
            setError(taskInfo.error || '任务执行失败')
            setIsGenerating(false)
          }
        } catch (err) {
          clearInterval(pollInterval)
          setError('查询任务状态出错')
          setIsGenerating(false)
          console.error(err)
        }
      }, 2000)

    } catch (err) {
      setError('提交任务失败，请检查后端服务是否正常运行')
      setIsGenerating(false)
      console.error(err)
    }
  }

  const handleLoginSuccess = () => {
    const loggedIn = checkLoggedIn()
    setIsLoggedIn(loggedIn)
    if (loggedIn) {
      setUserInfo(getLocalUserInfo())
    }
    setShowLoginModal(false)
  }

  const handleLogout = () => {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user_info')
    setIsLoggedIn(false)
    setUserInfo(null)
  }

  const getProgressPercentage = () => {
    if (!progress) return 0
    switch (progress.step) {
      case 'init': return 5
      case 'waiting': return 5
      case 'generating_outline': return 15
      case 'analyzing': return 20
      case 'optimizing_keywords': return 25
      case 'searching': return 40
      case 'filtering': return 60
      case 'topic_relevance_check': return 65
      case 'generating': return 80
      case 'validating': return 90
      case 'completed': return 100
      default: return 5
    }
  }

  return (
    <div className="simple-home">
      {/* 顶部导航栏 */}
      <nav className="home-nav">
        <div className="nav-logo">
          <span className="logo-icon">📚</span>
          <span className="logo-text">PaperOverview</span>
        </div>
        <div className="nav-actions">
          {isLoggedIn ? (
            <div className="user-menu">
              <button className="user-info" onClick={() => navigate('/review')}>
                <span className="user-avatar">👤</span>
                <span className="user-name">{userInfo?.nickname || '用户'}</span>
              </button>
              <button className="nav-btn nav-btn-logout" onClick={handleLogout}>
                退出
              </button>
            </div>
          ) : (
            <div className="auth-buttons">
              <button className="nav-btn nav-btn-login" onClick={() => setShowLoginModal(true)}>
                登录
              </button>
              <button
                className="nav-btn nav-btn-register"
                onClick={() => setShowLoginModal(true)}
              >
                注册
              </button>
            </div>
          )}
        </div>
      </nav>

      {/* 主内容区 */}
      <div className="home-container">
        {/* Hero 区域 */}
        <div className="home-hero-wrapper">
          <div className="home-hero">
            <span className="hero-accent">学术研究 · 高效利器</span>
            <h1 className="home-title">
              AI 论文<span className="highlight">综述生成器</span>
            </h1>
            <p className="home-subtitle">
              输入研究主题，一键生成专业文献综述。让 AI 助您在学术道路上更进一步。
            </p>
          </div>

          {/* 右侧视觉装饰 */}
          <div className="hero-visual">
            <div className="visual-card">
              <div className="visual-icon-large">🔬</div>
              <div className="visual-stats">
                <div className="visual-stat">
                  <span className="visual-stat-number">权威</span>
                  <span className="visual-stat-label">- 学术期刊</span>
                </div>
                <div className="visual-stat">
                  <span className="visual-stat-number">海量</span>
                  <span className="visual-stat-label">- 论文数据</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 输入区域 */}
        <div className="home-input-section">
          <div className="input-section-header">
            <h2 className="input-section-title">一键生成论文综述</h2>
            <p className="input-section-subtitle">输入研究主题，AI 为您生成专业文献综述</p>
          </div>

          <input
            type="text"
            className="home-input"
            placeholder="请输入您的研究主题，例如：深度学习在图像识别中的应用"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !isGenerating && handleGenerate()}
            disabled={isGenerating}
          />

          <button
            className="home-button"
            onClick={handleGenerate}
            disabled={isGenerating || !topic.trim()}
          >
            {isGenerating ? '生成中...' : '生成综述'}
          </button>

          {error && (
            <div className="home-error">
              {error}
            </div>
          )}

          {isGenerating && progress && (
            <div className="home-progress">
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${getProgressPercentage()}%` }}
                />
              </div>
              <div className="progress-message">{progress.message}</div>
            </div>
          )}
        </div>

        {/* 竞品对比 */}
        <div className="comparison-section">
          <h2 className="comparison-title">为什么选择 PaperOverview？</h2>
          <div className="comparison-grid">
            <div className="comparison-card">
              <div className="comparison-card-header">
                <span className="comparison-icon">🤖</span>
                <h3 className="comparison-card-title">免费大模型</h3>
              </div>
              <ul className="comparison-list">
                <li className="comparison-item negative">❌ 缺乏真实论文数据支撑</li>
                <li className="comparison-item negative">❌ 无法获取最新研究进展</li>
                <li className="comparison-item negative">❌ 可能编造引用文献</li>
              </ul>
            </div>

            <div className="comparison-card">
              <div className="comparison-card-header">
                <span className="comparison-icon">🔧</span>
                <h3 className="comparison-card-title">Elicit / Scite / Paperpal</h3>
              </div>
              <ul className="comparison-list">
                <li className="comparison-item negative">❌ 功能单一，仅辅助工具</li>
                <li className="comparison-item negative">❌ 无法生成完整综述</li>
                <li className="comparison-item negative">❌ 使用门槛高</li>
              </ul>
            </div>

            <div className="comparison-card highlight">
              <div className="comparison-card-header">
                <span className="comparison-icon">📄</span>
                <h3 className="comparison-card-title">PaperOverview</h3>
              </div>
              <ul className="comparison-list">
                <li className="comparison-item positive">✅ 海量真实学术期刊数据源</li>
                <li className="comparison-item positive">✅ 2分钟遍历文献，5分钟生成综述</li>
                <li className="comparison-item positive">✅ 学术规范，精准引用</li>
              </ul>
            </div>

            <div className="comparison-card">
              <div className="comparison-card-header">
                <span className="comparison-icon">👤</span>
                <h3 className="comparison-card-title">第三方人工服务</h3>
              </div>
              <ul className="comparison-list">
                <li className="comparison-item negative">❌ 价格昂贵，质量参差不齐</li>
                <li className="comparison-item negative">❌ 耗时数天至数周</li>
                <li className="comparison-item negative">❌ 存在学术合规风险</li>
              </ul>
            </div>

            <div className="comparison-card">
              <div className="comparison-card-header">
                <span className="comparison-icon">📖</span>
                <h3 className="comparison-card-title">知网研学 / 自己写</h3>
              </div>
              <ul className="comparison-list">
                <li className="comparison-item negative">❌ 耗时数周甚至数月</li>
                <li className="comparison-item negative">❌ 查找文献效率低</li>
                <li className="comparison-item negative">❌ 难以全面覆盖前沿</li>
              </ul>
            </div>
          </div>
        </div>

        {/* 特性展示 */}
        <div className="home-features">
          <div className="feature-item">
            <span className="feature-icon">📚</span>
            <div>
              <h3 className="feature-title">海量真实数据</h3>
              <p className="feature-desc">海量、真实、最新的论文数据，帮您掌握前沿进展</p>
            </div>
          </div>
          <div className="feature-item">
            <span className="feature-icon">⚡</span>
            <div>
              <h3 className="feature-title">极速效率</h3>
              <p className="feature-desc">2分钟遍历相关文献，5分钟生成专业综述</p>
            </div>
          </div>
          <div className="feature-item">
            <span className="feature-icon">🎯</span>
            <div>
              <h3 className="feature-title">专业规范</h3>
              <p className="feature-desc">学术规范的综述结构，精准引用权威文献</p>
            </div>
          </div>
        </div>
      </div>

      {/* 页脚 */}
      <footer className="home-footer">
        <div className="footer-content">
          <p className="footer-copyright">© 2026 PaperOverview. All rights reserved.</p>
          <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer" className="footer-icp">
            沪ICP备2023018158号-4
          </a>
        </div>
      </footer>

      {/* 登录模态框 */}
      {showLoginModal && (
        <LoginModal
          onClose={() => setShowLoginModal(false)}
          onLoginSuccess={handleLoginSuccess}
          pendingTopic={topic}
        />
      )}
    </div>
  )
}
