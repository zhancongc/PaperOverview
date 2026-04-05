import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import App from './App'
import { SimpleApp } from './components/SimpleApp'
import { ReviewPage } from './components/ReviewPage'
import { LoginPage } from './components/LoginPage'
import ErrorBoundary from './ErrorBoundary'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <ErrorBoundary>
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<SimpleApp />} />
        <Route path="/review" element={
          <ProtectedRoute>
            <ReviewPage />
          </ProtectedRoute>
        } />
        <Route path="/review/:taskId" element={<ReviewPage />} />
        <Route path="/jade" element={<App />} />
      </Routes>
    </BrowserRouter>
  </ErrorBoundary>,
)

// 受保护的路由组件（用于需要登录的页面）
function ProtectedRoute({ children }: { children: React.ReactElement }) {
  const token = localStorage.getItem('auth_token')
  if (!token) {
    return <Navigate to="/login" replace state={{ from: { pathname: window.location.pathname } }} />
  }
  return children
}
