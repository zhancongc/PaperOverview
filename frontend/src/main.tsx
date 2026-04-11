import React, { useState, useEffect } from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate, useSearchParams } from 'react-router-dom'
import App from './App'
import { SimpleApp } from './components/SimpleApp'
import { ReviewPage } from './components/ReviewPage'
import { ProfilePage } from './components/ProfilePage'
import { DavidPage } from './components/DavidPage'
import ErrorBoundary from './ErrorBoundary'
import { api } from './api'
import './index.css'

function BackToTop() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const onScroll = () => setVisible(window.scrollY > 300)
    window.addEventListener('scroll', onScroll)
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <button
      className="back-to-top"
      style={{ opacity: visible ? 1 : 0, pointerEvents: visible ? 'auto' : 'none' }}
      onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
    >
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <path d="M10 4L4 10h4v6h4v-6h4L10 4z" fill="currentColor"/>
      </svg>
    </button>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <ErrorBoundary>
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<SimpleApp autoShowLogin />} />
        <Route path="/" element={<SimpleApp />} />
        <Route path="/profile" element={
          <ProtectedRoute>
            <ProfilePage />
          </ProtectedRoute>
        } />
        <Route path="/review" element={
          <ReviewRoute>
            <ReviewPage />
          </ReviewRoute>
        } />
        <Route path="/david" element={
          <DavidRoute>
            <DavidPage />
          </DavidRoute>
        } />
        <Route path="/jade" element={
          <JadeRoute>
            <App />
          </JadeRoute>
        } />
      </Routes>
      <BackToTop />
    </BrowserRouter>
  </ErrorBoundary>,
)

// 受保护的路由组件（用于需要登录的页面）
function ProtectedRoute({ children }: { children: React.ReactElement }) {
  const token = localStorage.getItem('auth_token')
  if (!token) {
    return <Navigate to="/login" replace state={{ from: { pathname: window.location.pathname } }} />
  }
  return <>{children}</>
}

// Review 路由守卫（案例白名单免登录，其余需登录）
function ReviewRoute({ children }: { children: React.ReactElement }) {
  const [searchParams] = useSearchParams()
  const taskId = searchParams.get('task_id')
  const [demoIds, setDemoIds] = useState<Set<string> | null>(null)

  useEffect(() => {
    fetch('/api/health')
      .then(res => res.json())
      .then(data => {
        const ids = (data.demo_task_ids || []) as string[]
        setDemoIds(new Set(ids))
      })
      .catch(() => setDemoIds(new Set()))
  }, [])

  // 等待白名单加载
  if (demoIds === null) return null

  // 案例展示，免登录
  if (taskId && demoIds.has(taskId)) {
    return children
  }

  // 其余需要登录
  const token = localStorage.getItem('auth_token')
  if (!token) {
    return <Navigate to="/login" replace state={{ from: { pathname: window.location.pathname + window.location.search } }} />
  }

  return children
}

// Jade 路由守卫（白名单用户才能访问）
function JadeRoute({ children }: { children: React.ReactElement }) {
  const [checking, setChecking] = useState(true)
  const [allowed, setAllowed] = useState(false)

  useEffect(() => {
    api.checkJadeAccess().then(data => {
      setAllowed(data.allowed)
      setChecking(false)
    }).catch(() => {
      setAllowed(false)
      setChecking(false)
    })
  }, [])

  if (checking) return null
  if (!allowed) return <Navigate to="/" replace />
  return children
}

// David 路由守卫（只有管理员才能访问）
function DavidRoute({ children }: { children: React.ReactElement }) {
  const [checking, setChecking] = useState(true)
  const [allowed, setAllowed] = useState(false)

  useEffect(() => {
    // 检查用户是否有权限访问
    const token = localStorage.getItem('auth_token')
    if (!token) {
      setChecking(false)
      return
    }

    // 这里可以添加权限检查逻辑
    // 暂时只检查是否登录
    setAllowed(true)
    setChecking(false)
  }, [])

  if (checking) return null
  if (!allowed) return <Navigate to="/login" replace />
  return children
}
