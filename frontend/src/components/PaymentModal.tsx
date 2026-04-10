import { useState, useEffect, useRef, useCallback } from 'react'
import { api } from '../api'
import './PaymentModal.css'

interface PaymentModalProps {
  onClose: () => void
  onPaymentSuccess: (addedCredits?: number) => void
  planType: string
  recordId?: number  // 用于 unlock 模式
}

// 单次解锁的固定配置
const UNLOCK_PLAN = {
  type: 'unlock',
  name: '单次解锁',
  price: 29.8,
  credits: 0,
  features: [
    '解锁当前综述 Word 导出权限',
    '无水印 Word 文档',
  ],
}

const IS_DEV = window.location.hostname === 'localhost' ||
  window.location.hostname === '127.0.0.1'

export function PaymentModal({ onClose, onPaymentSuccess, planType, recordId }: PaymentModalProps) {
  const [, setLoading] = useState(false)
  const [orderNo, setOrderNo] = useState('')
  const [payUrl, setPayUrl] = useState('')
  const [error, setError] = useState('')
  const [paymentStatus, setPaymentStatus] = useState<'idle' | 'creating' | 'waiting' | 'paid' | 'failed'>('idle')
  const [amount, setAmount] = useState(0)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const [plans, setPlans] = useState<any[]>([])

  // 获取套餐数据
  useEffect(() => {
    api.getSubscriptionPlans().then(data => {
      setPlans(data.plans)
    }).catch(err => {
      console.error('获取套餐失败:', err)
    })
  }, [])

  // 单次解锁使用固定配置，其他套餐从 API 获取
  const plan = planType === 'unlock'
    ? UNLOCK_PLAN
    : plans.find(p => p.type === planType) || { ...UNLOCK_PLAN, name: '未知套餐', price: 0, credits: 0, features: [] }

  // Esc 关闭弹窗
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [onClose])

  // 轮询支付状态
  useEffect(() => {
    if (!orderNo || paymentStatus === 'paid') return

    pollingRef.current = setInterval(async () => {
      try {
        const result = await api.querySubscription(orderNo)
        if (result.status === 'paid') {
          setPaymentStatus('paid')
          if (pollingRef.current) clearInterval(pollingRef.current)
          onPaymentSuccess(plan.credits)
        }
      } catch {
        // 忽略轮询错误，继续轮询
      }
    }, 3000)

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current)
    }
  }, [orderNo, paymentStatus, onPaymentSuccess])

  // 开发环境：5秒后自动触发模拟支付
  useEffect(() => {
    if (!IS_DEV || !payUrl || paymentStatus !== 'waiting' || planType !== 'unlock') return

    const timer = setTimeout(async () => {
      try {
        // 调用模拟支付URL（DevAlipayService返回的回调URL）
        await fetch(payUrl)
        // 轮询会检测到支付成功
      } catch (err) {
        console.error('模拟支付失败:', err)
      }
    }, 5000)

    return () => clearTimeout(timer)
  }, [IS_DEV, payUrl, paymentStatus, planType])

  // 创建订单
  const createPayment = useCallback(async () => {
    setLoading(true)
    setError('')
    setPaymentStatus('creating')

    try {
      if (planType === 'unlock' && recordId) {
        // 单次解锁模式
        const result = await api.unlockRecord(recordId)
        if (result.already_unlocked) {
          // 已经解锁，直接成功
          setPaymentStatus('paid')
          onPaymentSuccess(0)
          return
        }
        setOrderNo(result.order_no || '')
        setPayUrl(result.pay_url || '')
        setAmount(29.8)
        // 统一进入等待状态，开发环境5秒后自动触发支付
        setPaymentStatus('waiting')
      } else {
        // 套餐购买模式
        const result = await api.createSubscription(planType)
        setOrderNo(result.order_no)
        setPayUrl(result.pay_url)
        setAmount(result.amount)
        setPaymentStatus('waiting')
      }
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || '创建订单失败，请稍后重试'
      setError(msg)
      setPaymentStatus('failed')
    } finally {
      setLoading(false)
    }
  }, [planType, recordId, onPaymentSuccess])

  // 自动创建订单
  useEffect(() => {
    createPayment()
  }, [createPayment])

  // 开发环境模拟支付
  const handleDevPay = () => {
    if (payUrl) {
      window.location.href = payUrl
    }
  }

  // 关闭弹窗前清理轮询
  const handleClose = () => {
    if (pollingRef.current) clearInterval(pollingRef.current)
    onClose()
  }

  return (
    <div className="payment-modal-overlay" onClick={handleClose}>
      <div className="payment-modal" onClick={e => e.stopPropagation()}>
        <button className="payment-modal-close" onClick={handleClose}>&times;</button>

        {/* 头部：套餐信息 */}
        <div className="payment-modal-header">
          <span className="payment-modal-icon">💳</span>
          <h2 className="payment-modal-title">购买 {plan.name}</h2>
          <p className="payment-modal-price">
            <span className="amount">¥{plan.price}</span>
          </p>
          <p className="payment-modal-credits">{plan.credits} 篇综述生成额度</p>
          <ul className="payment-modal-features">
            {plan.features.map((f: string, i: number) => (
              <li key={i}>✓ {f}</li>
            ))}
          </ul>
        </div>

        {/* 支付区域 */}
        <div className="payment-modal-body">
          {paymentStatus === 'creating' && (
            <div className="payment-modal-loading">
              <div className="payment-spinner"></div>
              <p>正在创建订单...</p>
            </div>
          )}

          {paymentStatus === 'waiting' && payUrl && (
            <div className="payment-modal-payment">
              {IS_DEV ? (
                <div className="payment-modal-devpay">
                  <p className="payment-dev-hint">
                    🔧 开发环境 · {planType === 'unlock' ? '5秒后自动完成支付' : '模拟支付'}
                  </p>
                  <p className="payment-dev-order">订单号：{orderNo}</p>
                  {planType !== 'unlock' && (
                    <button className="payment-modal-btn" onClick={handleDevPay}>
                      模拟支付（¥{amount}）
                    </button>
                  )}
                  <div className="payment-modal-polling">
                    <div className="payment-spinner small"></div>
                    <p>{planType === 'unlock' ? '正在自动支付...' : '等待支付结果...'}</p>
                  </div>
                </div>
              ) : (
                <div className="payment-modal-payurl">
                  <p className="payment-pay-hint">请点击下方按钮跳转到支付宝完成支付</p>
                  <p className="payment-order-info">订单号：{orderNo} · 金额：¥{amount}</p>
                  <a
                    href={payUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="payment-modal-btn primary"
                  >
                    立即支付
                  </a>
                  <div className="payment-modal-polling">
                    <div className="payment-spinner small"></div>
                    <p>支付完成后将自动确认...</p>
                  </div>
                </div>
              )}
              <button className="payment-cancel-btn" onClick={handleClose}>
                取消支付
              </button>
            </div>
          )}

          {paymentStatus === 'paid' && (
            <div className="payment-modal-success">
              <span className="payment-success-icon">✓</span>
              <h3>支付成功</h3>
              <p>{plan.type === 'unlock' ? '已解锁该综述 Word 导出权限' : `已获得 ${plan.credits} 篇综述生成额度`}</p>
              <button className="payment-modal-btn" onClick={handleClose}>完成</button>
            </div>
          )}

          {paymentStatus === 'failed' && error && (
            <div className="payment-modal-error">
              <p className="payment-error-text">{error}</p>
              <button className="payment-modal-btn" onClick={createPayment}>重试</button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
