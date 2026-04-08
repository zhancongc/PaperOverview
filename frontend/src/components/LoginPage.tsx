import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { authApi } from '../authApi'
import './LoginPage.css'

type LoginTab = 'password' | 'code'

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  void ((location.state as any)?.from?.pathname || '/')

  const [tab, setTab] = useState<LoginTab>('password')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [nickname, setNickname] = useState('')
  const [isRegister, setIsRegister] = useState(false)

  const [loading, setLoading] = useState(false)
  const [sendingCode, setSendingCode] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [countdown, setCountdown] = useState(0)

  // 发送验证码
  const handleSendCode = async () => {
    if (!email.trim()) {
      setError('请输入邮箱')
      return
    }

    setSendingCode(true)
    setError('')
    setMessage('')

    try {
      const response = await authApi.sendCode(email, tab === 'code' ? 'login' : 'register')
      if (response.success) {
        setMessage(response.message)
        // 开始倒计时
        let count = 60
        setCountdown(count)
        const timer = setInterval(() => {
          count--
          setCountdown(count)
          if (count <= 0) {
            clearInterval(timer)
          }
        }, 1000)
      } else {
        setError(response.message)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || '发送失败，请稍后重试')
    } finally {
      setSendingCode(false)
    }
  }

  // 处理登录/注册
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setMessage('')

    if (!email.trim()) {
      setError('请输入邮箱')
      return
    }

    setLoading(true)

    try {
      if (tab === 'password') {
        if (isRegister) {
          // 密码注册
          const response = await authApi.register(email, password, nickname || undefined)
          if (response.success) {
            setMessage('注册成功！请登录')
            setIsRegister(false)
            setPassword('')
          } else {
            setError(response.message)
          }
        } else {
          // 密码登录
          const data = await authApi.login(email, password)
          // 保存 token
          localStorage.setItem('auth_token', data.access_token)
          localStorage.setItem('user_info', JSON.stringify(data.user))

          // 跳转回首页（如果有 pending_topic 会自动提示）
          navigate('/', { replace: true })
        }
      } else {
        // 验证码登录
        if (!code.trim()) {
          setError('请输入验证码')
          setLoading(false)
          return
        }
        const data = await authApi.loginWithCode(email, code)
        // 保存 token
        localStorage.setItem('auth_token', data.access_token)
        localStorage.setItem('user_info', JSON.stringify(data.user))

        // 跳转回首页（如果有 pending_topic 会自动提示）
        navigate('/', { replace: true })
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || '操作失败，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-header">
          <h1 className="login-title">登录</h1>
          <p className="login-subtitle">欢迎使用 AutoOverview</p>
        </div>

        {/* Tab 切换 */}
        <div className="login-tabs">
          <button
            className={`tab-button ${tab === 'password' ? 'active' : ''}`}
            onClick={() => {
              setTab('password')
              setIsRegister(false)
              setError('')
              setMessage('')
            }}
          >
            密码登录
          </button>
          <button
            className={`tab-button ${tab === 'code' ? 'active' : ''}`}
            onClick={() => {
              setTab('code')
              setIsRegister(false)
              setError('')
              setMessage('')
            }}
          >
            验证码登录
          </button>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          {/* 邮箱输入 */}
          <div className="form-group">
            <label htmlFor="email">邮箱</label>
            <input
              id="email"
              type="email"
              className="form-input"
              placeholder="请输入邮箱"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
            />
          </div>

          {tab === 'password' ? (
            <>
              {/* 密码输入 */}
              <div className="form-group">
                <label htmlFor="password">
                  {isRegister ? '设置密码' : '密码'}
                </label>
                <input
                  id="password"
                  type="password"
                  className="form-input"
                  placeholder={isRegister ? '至少8位，包含大小写字母和数字' : '请输入密码'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                />
              </div>

              {/* 注册时的昵称输入 */}
              {isRegister && (
                <div className="form-group">
                  <label htmlFor="nickname">昵称（可选）</label>
                  <input
                    id="nickname"
                    type="text"
                    className="form-input"
                    placeholder="请输入昵称"
                    value={nickname}
                    onChange={(e) => setNickname(e.target.value)}
                    disabled={loading}
                  />
                </div>
              )}

              {/* 登录/注册切换 */}
              {!loading && (
                <div className="form-footer">
                  {isRegister ? (
                    <span>
                      已有账号？
                      <button
                        type="button"
                        className="link-button"
                        onClick={() => {
                          setIsRegister(false)
                          setError('')
                          setMessage('')
                        }}
                      >
                        立即登录
                      </button>
                    </span>
                  ) : (
                    <span>
                      还没有账号？
                      <button
                        type="button"
                        className="link-button"
                        onClick={() => {
                          setIsRegister(true)
                          setError('')
                          setMessage('')
                        }}
                      >
                        注册账号
                      </button>
                    </span>
                  )}
                </div>
              )}
            </>
          ) : (
            <>
              {/* 验证码输入 */}
              <div className="form-group">
                <label htmlFor="code">验证码</label>
                <div className="code-input-group">
                  <input
                    id="code"
                    type="text"
                    className="form-input code-input"
                    placeholder="请输入6位验证码"
                    value={code}
                    onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    disabled={loading}
                    maxLength={6}
                  />
                  <button
                    type="button"
                    className="send-code-button"
                    onClick={handleSendCode}
                    disabled={sendingCode || countdown > 0 || loading}
                  >
                    {countdown > 0 ? `${countdown}秒后重试` : sendingCode ? '发送中...' : '发送验证码'}
                  </button>
                </div>
              </div>
            </>
          )}

          {/* 错误提示 */}
          {error && (
            <div className="form-error">
              {error}
            </div>
          )}

          {/* 成功提示 */}
          {message && (
            <div className="form-success">
              {message}
            </div>
          )}

          {/* 提交按钮 */}
          <button
            type="submit"
            className="submit-button"
            disabled={loading}
          >
            {loading ? '处理中...' : isRegister ? '注册' : '登录'}
          </button>
        </form>
      </div>
    </div>
  )
}
