import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../api'
import { isLoggedIn as checkLoggedIn, getLocalUserInfo } from '../authApi'
import { LoginModal } from './LoginModal'
import { PaymentModal } from './PaymentModal'
import { PaddlePaymentModal } from './PaddlePaymentModal'
import './SimpleApp.css'

interface TaskProgress {
  step: string
  message: string
}

export function SimpleApp({ autoShowLogin }: { autoShowLogin?: boolean } = {}) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [topic, setTopic] = useState('')
  const [language, setLanguage] = useState<'zh' | 'en'>('zh')
  const [isGenerating, setIsGenerating] = useState(false)
  const [progress, setProgress] = useState<TaskProgress | null>(null)
  const [error, setError] = useState('')
  const [showLoginModal, setShowLoginModal] = useState(false)
  const [showPaymentModal, setShowPaymentModal] = useState<string | false>(false)
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [, setActiveTaskId] = useState<string | null>(null)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [, setUserInfo] = useState<any>(null)
  const [credits, setCredits] = useState<number>(0)
  const [prevCredits, setPrevCredits] = useState<number>(0)
  const [showToast, setShowToast] = useState(false)
  const [toastMessage, setToastMessage] = useState('')
  const [plans, setPlans] = useState<any[]>([])
  const [plansLoading, setPlansLoading] = useState(true)
  const [demoCases, setDemoCases] = useState<any[]>([])
  const [casesLoading, setCasesLoading] = useState(true)

  useEffect(() => {
    const loggedIn = checkLoggedIn()
    setIsLoggedIn(loggedIn)
    // 未登录且 autoShowLogin 时自动弹出登录弹窗
    if (!loggedIn && autoShowLogin) {
      setShowLoginModal(true)
    }
    if (loggedIn) {
      setUserInfo(getLocalUserInfo())
      api.getCredits().then(data => setCredits(data.credits)).catch(err => console.error('获取额度失败:', err))
      // 检查是否有进行中的任务
      api.getActiveTask().then(data => {
        if (data.active && data.task_id) {
          setActiveTaskId(data.task_id)
          setTopic(data.topic || '')
          setIsGenerating(true)
          setProgress({ step: 'processing', message: language === 'en' ? t('home.progress.restoring') : '正在恢复任务状态...' })
          sessionStorage.setItem('active_task_id', data.task_id)
          sessionStorage.setItem('active_task_topic', data.topic || '')
          pollTask(data.task_id)
        }
      }).catch(err => console.error('获取活跃任务失败:', err))
    }

    // 获取套餐价格数据
    api.getSubscriptionPlans().then(data => {
      setPlans(data.plans)
      setPlansLoading(false)
    }).catch(err => {
      console.error('获取套餐失败:', err)
      setPlansLoading(false)
    })

    // 获取案例展示列表
    fetch('/api/cases')
      .then(res => res.json())
      .then(data => {
        if (data.success && data.data.cases) {
          setDemoCases(data.data.cases)
        }
        setCasesLoading(false)
      })
      .catch(err => {
        console.error('获取案例失败:', err)
        setCasesLoading(false)
      })
  }, [])

  const pollTask = (taskId: string) => {
    const startTime = Date.now()
    const doPoll = async () => {
      try {
        const statusResponse = await api.getTaskStatus(taskId)
        if (!statusResponse.success) {
          sessionStorage.removeItem('active_task_id')
          sessionStorage.removeItem('active_task_topic')
          setIsGenerating(false)
          setActiveTaskId(null)
          return
        }

        const taskInfo = statusResponse.data
        if (taskInfo.status === 'completed' && taskInfo.result) {
          sessionStorage.removeItem('active_task_id')
          sessionStorage.removeItem('active_task_topic')
          navigate(`/review?task_id=${taskId}`)
          return
        } else if (taskInfo.status === 'failed') {
          sessionStorage.removeItem('active_task_id')
          sessionStorage.removeItem('active_task_topic')
          setError(taskInfo.error || (language === 'en' ? t('home.errors.task_failed') : '任务执行失败'))
          setIsGenerating(false)
          setActiveTaskId(null)
          return
        }

        setProgress({ step: taskInfo.progress?.step || 'processing', message: taskInfo.progress?.message || (language === 'en' ? t('home.progress.processing') : '正在处理...') })

        // 根据已用时间调整轮询间隔
        const elapsed = Date.now() - startTime
        const elapsedMinutes = elapsed / (60 * 1000)
        let nextInterval: number
        if (elapsedMinutes < 1) {
          nextInterval = 20000
        } else if (elapsedMinutes < 3) {
          nextInterval = 15000
        } else {
          nextInterval = 10000
        }
        setTimeout(doPoll, nextInterval)
      } catch {
        sessionStorage.removeItem('active_task_id')
        sessionStorage.removeItem('active_task_topic')
        setIsGenerating(false)
        setActiveTaskId(null)
      }
    }
    setTimeout(doPoll, 5000) // 初始延迟5秒
  }

  useEffect(() => {
    const pendingTopic = sessionStorage.getItem('pending_topic')
    if (pendingTopic) {
      sessionStorage.removeItem('pending_topic')
      setTopic(pendingTopic)
    }
  }, [])

  // Esc 关闭弹窗
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (showLoginModal) setShowLoginModal(false)
        if (showPaymentModal) setShowPaymentModal(false)
        if (mobileMenuOpen) setMobileMenuOpen(false)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [showLoginModal, showPaymentModal, mobileMenuOpen])

  const handleGenerate = async () => {
    if (!topic.trim()) {
      setError('\u8BF7\u8F93\u5165\u7814\u7A76\u4E3B\u9898')
      return
    }

    if (!checkLoggedIn()) {
      setShowLoginModal(true)
      return
    }

    setIsGenerating(true)
    setProgress({ step: 'init', message: '\u6B63\u5728\u63D0\u4EA4\u4EFB\u52A1...' })
    setError('')

    try {
      const submitResponse = await api.submitReviewTask(topic, {
        language,
        targetCount: 50,
        recentYearsRatio: 0.5,
        englishRatio: 0.3,
        searchYears: 10,
        maxSearchQueries: 8
      })

      if (!submitResponse.success || !submitResponse.data?.task_id) {
        if (submitResponse.message?.includes('额度已用完')) {
          setError(submitResponse.message)
          setShowPaymentModal('single')
        } else {
          setError(submitResponse.message || '\u4EFB\u52A1\u63D0\u4EA4\u5931\u8D25')
        }
        setIsGenerating(false)
        return
      }

      const taskId = submitResponse.data.task_id
      setActiveTaskId(taskId)
      sessionStorage.setItem('active_task_id', taskId)
      sessionStorage.setItem('active_task_topic', topic)
      const startTime = Date.now()
      let pollCount = 0

      const doPoll = async () => {
        try {
          const statusResponse = await api.getTaskStatus(taskId)

          if (!statusResponse.success) {
            setError('\u67E5\u8BE2\u4EFB\u52A1\u72B6\u6001\u5931\u8D25')
            setIsGenerating(false)
            return
          }

          const taskInfo = statusResponse.data

          const elapsedMinutes = (Date.now() - startTime) / 1000 / 60
          let expectedRemainingMinutes = Math.max(0, Math.round(5 - elapsedMinutes))

          let progressMessage = taskInfo.progress?.message || '\u6B63\u5728\u5904\u7406...'
          if (expectedRemainingMinutes > 0) {
            progressMessage += `\uFF08\u9884\u671F\u8FD8\u6709${expectedRemainingMinutes}\u5206\u949F\uFF09`
          }

          setProgress({
            step: taskInfo.progress?.step || 'processing',
            message: progressMessage
          })

          if (taskInfo.status === 'completed' && taskInfo.result) {
            setProgress({ step: 'completed', message: '\u751F\u6210\u5B8C\u6210\uFF01\u6B63\u5728\u8DF3\u8F6C...' })
            sessionStorage.removeItem('active_task_id')
            sessionStorage.removeItem('active_task_topic')
            setTimeout(() => {
              navigate(`/review?task_id=${taskId}`)
            }, 500)
            return
          } else if (taskInfo.status === 'failed') {
            sessionStorage.removeItem('active_task_id')
            sessionStorage.removeItem('active_task_topic')
            setError(taskInfo.error || '\u4EFB\u52A1\u6267\u884C\u5931\u8D25')
            setIsGenerating(false)
            setActiveTaskId(null)
            return
          }

          pollCount++
          // elapsedMinutes 已在上面计算，直接使用

          // 优化轮询间隔，减少服务端压力
          let nextInterval: number
          if (elapsedMinutes < 1) {
            // 前1分钟：每20秒轮询一次
            nextInterval = 20000
          } else if (elapsedMinutes < 3) {
            // 1-3分钟：每15秒轮询一次
            nextInterval = 15000
          } else if (elapsedMinutes < 5) {
            // 3-5分钟：每10秒轮询一次
            nextInterval = 10000
          } else {
            // 5分钟后：每8秒轮询一次
            nextInterval = 8000
          }

          setTimeout(doPoll, nextInterval)
        } catch (err) {
          setError('\u67E5\u8BE2\u4EFB\u52A1\u72B6\u6001\u51FA\u9519')
          setIsGenerating(false)
          console.error(err)
        }
      }

      setTimeout(doPoll, 3000) // 初始延迟3秒，减少服务端压力
    } catch (err) {
      setError('\u63D0\u4EA4\u4EFB\u52A1\u5931\u8D25\uFF0C\u8BF7\u68C0\u67E5\u540E\u7AEF\u670D\u52A1\u662F\u5426\u6B63\u5E38\u8FD0\u884C')
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

  const handlePaymentSuccess = async (_addedCredits: number = 0) => {
    setShowPaymentModal(false)
    setUserInfo(getLocalUserInfo())
    setError('') // 清除之前的错误状态

    // 刷新额度
    try {
      const data = await api.getCredits()
      setPrevCredits(credits)
      setCredits(data.credits)

      // 显示成功提示
      setToastMessage(t('common.payment_success'))
      setShowToast(true)
      setTimeout(() => setShowToast(false), 3000)

      // 滚动到综述生成区域
      setTimeout(() => {
        const generateSection = document.getElementById('generate')
        if (generateSection) {
          generateSection.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }
      }, 500)
    } catch (err) {
      console.error('刷新额度失败', err)
    }
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
      <nav className="home-nav">
        <div className="nav-logo">
          <span className="logo-icon">📚</span>
          <span className="logo-text">AutoOverview</span>
        </div>
        <div className="nav-links">
          <a href="#generate">{t('home.nav.generate')}</a>
          <a href="#features">{t('home.nav.features')}</a>
          <a href="#process">{t('home.nav.process')}</a>
          <a href="#cases">{t('home.nav.cases')}</a>
          <a href="#pricing">{t('home.nav.pricing')}</a>
        </div>
        <div className="nav-actions">
          {isLoggedIn ? (
            <div className="user-menu">
              <button className="user-info" onClick={() => navigate('/profile')}>
                <span className="user-avatar">👤</span>
                <span className="user-name">{t('home.nav.profile')}</span>
              </button>
              <button className="nav-btn nav-btn-logout" onClick={handleLogout}>
                {t('home.nav.logout')}
              </button>
            </div>
          ) : (
            <div className="auth-buttons">
              <button
                className="nav-btn nav-btn-register"
                onClick={() => setShowLoginModal(true)}
              >
                {t('home.nav.login_register')}
              </button>
            </div>
          )}
        </div>
        <button className="mobile-menu-toggle" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
          <span className={`hamburger ${mobileMenuOpen ? 'open' : ''}`} />
        </button>
      </nav>

      {/* 移动端侧边栏遮罩 */}
      {mobileMenuOpen && (
        <div className="mobile-sidebar-overlay" onClick={() => setMobileMenuOpen(false)} />
      )}

      {/* 移动端侧边栏 */}
      <aside className={`mobile-sidebar ${mobileMenuOpen ? 'sidebar-open' : ''}`}>
        <div className="sidebar-header">
          <span className="logo-icon">📚</span>
          <span className="logo-text">AutoOverview</span>
          <button className="sidebar-close" onClick={() => setMobileMenuOpen(false)}>&times;</button>
        </div>
        <nav className="sidebar-links">
          <a href="#generate" onClick={() => setMobileMenuOpen(false)}>{t('home.nav.generate')}</a>
          <a href="#features" onClick={() => setMobileMenuOpen(false)}>{t('home.nav.features')}</a>
          <a href="#process" onClick={() => setMobileMenuOpen(false)}>{t('home.nav.process')}</a>
          <a href="#cases" onClick={() => setMobileMenuOpen(false)}>{t('home.nav.cases')}</a>
          <a href="#pricing" onClick={() => setMobileMenuOpen(false)}>{t('home.nav.pricing')}</a>
        </nav>
        <div className="sidebar-bottom">
          {isLoggedIn ? (
            <>
              <button className="sidebar-user-btn" onClick={() => { setMobileMenuOpen(false); navigate('/profile') }}>
                <span className="user-avatar">👤</span>
                <span className="user-name">{t('home.nav.profile')}</span>
              </button>
              <button className="nav-btn nav-btn-logout" onClick={() => { setMobileMenuOpen(false); handleLogout() }}>
                {t('home.nav.logout')}
              </button>
            </>
          ) : (
            <button
              className="nav-btn nav-btn-register"
              onClick={() => { setMobileMenuOpen(false); setShowLoginModal(true) }}
            >
              {t('home.nav.login_register')}
            </button>
          )}
        </div>
      </aside>

      <div className="home-container">
        <div id="generate" className="home-hero-wrapper">
          <div className="home-hero">
            <span className="hero-accent">{t('home.hero.accent')}</span>
            <h1 className="home-title">
              <span dangerouslySetInnerHTML={{ __html: t('home.hero.title') }} />
            </h1>
            <p className="home-subtitle">
              {t('home.hero.subtitle')}
            </p>
          </div>

          <div className="hero-visual">
            <div className="visual-card">
              <div className="visual-icon-large">📊</div>
              <div className="visual-stats">
                <div className="visual-stat">
                  <span className="visual-stat-number">200M+</span>
                  <span className="visual-stat-label">{t('home.stats.papers')}</span>
                </div>
                <div className="visual-stat">
                  <span className="visual-stat-number">5min</span>
                  <span className="visual-stat-label">{t('home.stats.time')}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="home-input-section">
          {isLoggedIn && <span className={`credits-badge ${prevCredits !== credits ? 'credits-updated' : ''}`}>
            {t('input.credits_remaining')} <span className="credits-number">{credits}</span>
          </span>}
          <div className="input-section-header">
            <div className="input-section-title-row">
              <h2 className="input-section-title">{t('input.title')}</h2>
            </div>
            <p className="input-section-subtitle">{t('input.subtitle')}</p>
          </div>

          <div className="language-toggle-wrapper">
            <span className="language-label">{t('input.language')}:</span>
            <div className="language-toggle">
              <button
                className={`language-option ${language === 'zh' ? 'active' : ''}`}
                onClick={() => setLanguage('zh')}
                disabled={isGenerating}
              >
                {t('input.language_zh')}
              </button>
              <button
                className={`language-option ${language === 'en' ? 'active' : ''}`}
                onClick={() => setLanguage('en')}
                disabled={isGenerating}
              >
                {t('input.language_en')}
              </button>
            </div>
            <span className="language-hint">
              {language === 'zh' ? t('input.language_hint_zh') : t('input.language_hint_en')}
            </span>
          </div>

          <input
            type="text"
            className="home-input"
            placeholder={t('input.placeholder')}
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
            {isGenerating ? t('input.button_generating') : t('input.button')}
          </button>

          {error && (
            <div className="home-error">
              <span>{error}</span>
              <button className="retry-button" onClick={handleGenerate}>{t('input.retry')}</button>
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
              <div className="progress-hint">
                {t('home.progress.hint')}
                <span className="progress-hint-link" onClick={() => navigate('/profile')}>{t('home.progress.view_profile')}</span>
              </div>
            </div>
          )}
        </div>

        <div className="social-proof-bar">
          <span className="social-proof-icon">🏆</span>
          <span className="social-proof-text" dangerouslySetInnerHTML={{ __html: t('home.social_proof.text') }} />
        </div>
        </div>
      </div>

      <section id="features" className="landing-section">
        <div className="section-inner">
          <h2 className="section-title">{t('home.features.title')}</h2>
          <div className="comparison-grid">
            <div className="comparison-card">
              <div className="comparison-card-header">
                <span className="comparison-icon">🤖</span>
                <h3 className="comparison-card-title">{t('home.comparison.free_llm.title')}</h3>
              </div>
              <ul className="comparison-list">
                <li className="comparison-item negative">{t('home.comparison.free_llm.con1')}</li>
                <li className="comparison-item negative">{t('home.comparison.free_llm.con2')}</li>
                <li className="comparison-item negative">{t('home.comparison.free_llm.con3')}</li>
              </ul>
            </div>
            <div className="comparison-card">
              <div className="comparison-card-header">
                <span className="comparison-icon">🔧</span>
                <h3 className="comparison-card-title">{t('home.comparison.tools.title')}</h3>
              </div>
              <ul className="comparison-list">
                <li className="comparison-item negative">{t('home.comparison.tools.con1')}</li>
                <li className="comparison-item negative">{t('home.comparison.tools.con2')}</li>
                <li className="comparison-item negative">{t('home.comparison.tools.con3')}</li>
              </ul>
            </div>
            <div className="comparison-card highlight">
              <div className="comparison-card-header">
                <span className="comparison-icon">📄</span>
                <h3 className="comparison-card-title">{t('home.comparison.autooverview.title')}</h3>
              </div>
              <ul className="comparison-list">
                <li className="comparison-item positive">{t('home.comparison.autooverview.pro1')}</li>
                <li className="comparison-item positive">{t('home.comparison.autooverview.pro2')}</li>
                <li className="comparison-item positive">{t('home.comparison.autooverview.pro3')}</li>
              </ul>
            </div>
            <div className="comparison-card">
              <div className="comparison-card-header">
                <span className="comparison-icon">👤</span>
                <h3 className="comparison-card-title">{t('home.comparison.services.title')}</h3>
              </div>
              <ul className="comparison-list">
                <li className="comparison-item negative">{t('home.comparison.services.con1')}</li>
                <li className="comparison-item negative">{t('home.comparison.services.con2')}</li>
                <li className="comparison-item negative">{t('home.comparison.services.con3')}</li>
              </ul>
            </div>
            <div className="comparison-card">
              <div className="comparison-card-header">
                <span className="comparison-icon">📖</span>
                <h3 className="comparison-card-title">{t('home.comparison.manual.title')}</h3>
              </div>
              <ul className="comparison-list">
                <li className="comparison-item negative">{t('home.comparison.manual.con1')}</li>
                <li className="comparison-item negative">{t('home.comparison.manual.con2')}</li>
                <li className="comparison-item negative">{t('home.comparison.manual.con3')}</li>
              </ul>
            </div>
          </div>
          <div className="home-features">
            <div className="feature-item">
              <span className="feature-icon">📚</span>
              <div>
                <h3 className="feature-title">{t('home.features.papers')}</h3>
                <p className="feature-desc">{t('home.features.papers_desc')}</p>
              </div>
            </div>
            <div className="feature-item">
              <span className="feature-icon">⚡</span>
              <div>
                <h3 className="feature-title">{t('home.features.time')}</h3>
                <p className="feature-desc">{t('home.features.time_desc')}</p>
              </div>
            </div>
            <div className="feature-item">
              <span className="feature-icon">🎯</span>
              <div>
                <h3 className="feature-title">{t('home.features.format')}</h3>
                <p className="feature-desc">{t('home.features.format_desc')}</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="landing-section comparison-section">
        <div className="section-inner">
          <h2 className="section-title">{t('home.comparison.title')}</h2>
          <div className="comparison-flow">
            <div className="comparison-flow-card comparison-flow-manual">
              <div className="comparison-flow-label">{t('home.comparison.traditional_label')}</div>
              <ul className="comparison-flow-steps">
                <li><span className="comparison-flow-step-num">{t('home.comparison.traditional_step1')}</span> {t('home.comparison.traditional_step1_desc')}</li>
                <li><span className="comparison-flow-step-num">{t('home.comparison.traditional_step2')}</span> {t('home.comparison.traditional_step2_desc')}</li>
                <li><span className="comparison-flow-step-num">{t('home.comparison.traditional_step3')}</span> {t('home.comparison.traditional_step3_desc')}</li>
                <li><span className="comparison-flow-step-num">{t('home.comparison.traditional_step4')}</span> {t('home.comparison.traditional_step4_desc')}</li>
              </ul>
              <div className="comparison-flow-result">
                <span className="comparison-flow-time">{t('home.comparison.traditional_result_time')}</span>
                <span className="comparison-flow-mood">{t('home.comparison.traditional_result_mood')}</span>
              </div>
            </div>
            <div className="comparison-flow-vs">VS</div>
            <div className="comparison-flow-card comparison-flow-auto">
              <div className="comparison-flow-label">{t('home.comparison.auto_label')}</div>
              <ul className="comparison-flow-steps">
                <li><span className="comparison-flow-step-num">{t('home.comparison.auto_step1')}</span> {t('home.comparison.auto_step1_desc')}</li>
                <li><span className="comparison-flow-step-num">{t('home.comparison.auto_step2')}</span> {t('home.comparison.auto_step2_desc')}</li>
                <li><span className="comparison-flow-step-num">{t('home.comparison.auto_step3')}</span> {t('home.comparison.auto_step3_desc')}</li>
              </ul>
              <div className="comparison-flow-result">
                <span className="comparison-flow-time">{t('home.comparison.auto_result_time')}</span>
                <span className="comparison-flow-mood">{t('home.comparison.auto_result_mood')}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="process" className="landing-section section-alt">
        <div className="section-inner">
          <h2 className="section-title">{t('home.process.title')}</h2>
          <p className="section-subtitle">{t('home.process.subtitle')}</p>
          <div className="process-steps">
            <div className="process-step">
              <div className="step-number">01</div>
              <div className="step-icon">✏️</div>
              <h3 className="step-title">{t('home.process.step1_title')}</h3>
              <p className="step-desc">{t('home.process.step1_desc')}</p>
            </div>
            <div className="process-arrow">→</div>
            <div className="process-step">
              <div className="step-number">02</div>
              <div className="step-icon">✨</div>
              <h3 className="step-title">{t('home.process.step2_title')}</h3>
              <p className="step-desc">{t('home.process.step2_desc')}</p>
            </div>
            <div className="process-arrow">→</div>
            <div className="process-step">
              <div className="step-number">03</div>
              <div className="step-icon">📄</div>
              <h3 className="step-title">{t('home.process.step3_title')}</h3>
              <p className="step-desc">{t('home.process.step3_desc')}</p>
            </div>
          </div>
        </div>
      </section>

      <section id="cases" className="landing-section">
        <div className="section-inner">
          <h2 className="section-title">{t('home.demo.title')}</h2>
          <p className="section-subtitle">{t('home.demo.subtitle')}</p>
          <div className="cases-grid">
            {casesLoading ? (
              <div className="cases-loading">{t('home.demo.loading')}</div>
            ) : demoCases.length === 0 ? (
              <div className="cases-empty">{t('home.demo.empty')}</div>
            ) : (
              demoCases.map((case_item) => (
                <div
                  key={case_item.task_id}
                  className="case-card"
                  onClick={() => navigate(`/review?task_id=${case_item.task_id}`)}
                  role="button"
                  tabIndex={0}
                >
                  <div className="case-icon">{case_item.icon}</div>
                  <h3 className="case-title">{case_item.title}</h3>
                  <p className="case-desc">{case_item.description || t('home.demo.ai_generated')}</p>
                  {case_item.tags && case_item.tags.length > 0 && (
                    <div className="case-tags">
                      {case_item.tags.map((tag: string, idx: number) => (
                        <span key={idx} className="case-tag">{tag}</span>
                      ))}
                    </div>
                  )}
                  <div className="case-action">{t('home.demo.view_details')}</div>
                </div>
              ))
            )}
          </div>
        </div>
      </section>

      <section id="pricing" className="landing-section section-alt">
        <div className="section-inner">
          <h2 className="section-title">{t('pricing.title')}</h2>
          <p className="section-subtitle">{t('pricing.note')}</p>
          {plansLoading ? (
            <div className="pricing-grid">
              <div className="pricing-card">
                <div className="pricing-price">Loading...</div>
              </div>
            </div>
          ) : (
            <div className="pricing-grid">
              {plans.map((plan) => {
                // English pricing (USD)
                const enPricing: Record<string, { price: number; original: number; name: string; button: string }> = {
                  single: { price: 5.99, original: 7.99, name: t('pricing.single.name'), button: t('pricing.buy_single') },
                  semester: { price: 29.99, original: 39.99, name: t('pricing.semester.name'), button: t('pricing.choose_semester') },
                  yearly: { price: 79.99, original: 109.99, name: t('pricing.yearly.name'), button: t('pricing.choose_yearly') }
                }
                const pricing = language === 'en' ? enPricing[plan.type] : { price: plan.price, original: 0, name: plan.name, button: '' }
                const features = language === 'en' ? (plan.type === 'single' ? t('pricing.single.features', { returnObjects: true }) :
                  plan.type === 'semester' ? t('pricing.semester.features', { returnObjects: true }) :
                  t('pricing.yearly.features', { returnObjects: true })) : plan.features

                return (
                  <div
                    key={plan.type}
                    className={`pricing-card ${plan.recommended ? 'pricing-featured' : ''}`}
                  >
                    {plan.recommended && <div className="pricing-badge">{language === 'en' ? 'Recommended' : '推荐'}</div>}
                    <h3 className="pricing-name">{pricing.name}</h3>
                    <div className="pricing-price">
                      {language === 'en' && pricing.original > 0 && (
                        <span className="pricing-original">${pricing.original}</span>
                      )}
                      {language === 'en' ? '$' : '¥'}
                      {pricing.price}
                      {language === 'en' && <span className="pricing-unit">USD</span>}
                    </div>
                    <ul className="pricing-features">
                      {Array.isArray(features) && features.map((feature: string | any, index: number) => (
                        <li key={index}>{typeof feature === 'string' ? feature : String(feature)}</li>
                      ))}
                    </ul>
                    <button
                      className="pricing-btn pricing-btn-primary"
                      onClick={() => {
                        isLoggedIn ? setShowPaymentModal(plan.type) : setShowLoginModal(true)
                      }}
                    >
                      {language === 'en' ? pricing.button : (plan.type === 'single' ? '立即购买' : plan.type === 'semester' ? '选择标准包' : '选择进阶包')}
                    </button>
                  </div>
                )
              })}
            </div>
          )}
          <p className="pricing-note">{t('pricing.note')}</p>

          <div className="testimonials">
            <div className="testimonial-card">
              <p className="testimonial-text">{t('home.testimonials.text1')}</p>
              <div className="testimonial-author">
                <span className="testimonial-avatar">🎓</span>
                <div>
                  <span className="testimonial-name">{t('home.testimonials.name1')}</span>
                  <span className="testimonial-role">{t('home.testimonials.role1')}</span>
                </div>
              </div>
            </div>
            <div className="testimonial-card">
              <p className="testimonial-text">{t('home.testimonials.text2')}</p>
              <div className="testimonial-author">
                <span className="testimonial-avatar">📚</span>
                <div>
                  <span className="testimonial-name">{t('home.testimonials.name2')}</span>
                  <span className="testimonial-role">{t('home.testimonials.role2')}</span>
                </div>
              </div>
            </div>
            <div className="testimonial-card">
              <p className="testimonial-text">{t('home.testimonials.text3')}</p>
              <div className="testimonial-author">
                <span className="testimonial-avatar">🔬</span>
                <div>
                  <span className="testimonial-name">{t('home.testimonials.name3')}</span>
                  <span className="testimonial-role">{t('home.testimonials.role3')}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <footer className="home-footer">
        <div className="footer-content">
          <p className="footer-copyright">© 2026 AutoOverview. All rights reserved.</p>
          <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer" className="footer-icp">
            沪ICP备2023018158号-4
          </a>
        </div>
      </footer>

      {showLoginModal && (
        <LoginModal
          onClose={() => setShowLoginModal(false)}
          onLoginSuccess={handleLoginSuccess}
          pendingTopic={topic}
        />
      )}

      {showPaymentModal && (
        <>
          {language === 'en' ? (
            <PaddlePaymentModal
              onClose={() => setShowPaymentModal(false)}
              onPaymentSuccess={handlePaymentSuccess}
              planType={showPaymentModal}
            />
          ) : (
            <PaymentModal
              onClose={() => setShowPaymentModal(false)}
              onPaymentSuccess={handlePaymentSuccess}
              planType={showPaymentModal}
            />
          )}
        </>
      )}

      {showToast && (
        <div className="toast toast-success">
          <span className="toast-icon">✓</span>
          <span className="toast-message">{toastMessage}</span>
        </div>
      )}
    </div>
  )
}
