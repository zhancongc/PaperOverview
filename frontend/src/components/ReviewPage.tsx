import { useState, useEffect } from 'react'
import { useNavigate, useLocation, useParams } from 'react-router-dom'
import { ReviewViewer } from './ReviewViewer'
import { api } from '../api'
import type { Paper } from '../types'
import './ReviewPage.css'

interface ReviewState {
  title: string
  content: string
  papers: Paper[]
  recordId?: number
}

export function ReviewPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { taskId } = useParams<{ taskId: string }>()
  const state = location.state as ReviewState | null

  // 通过 taskId 加载的数据
  const [taskData, setTaskData] = useState<{
    title: string
    content: string
    papers: Paper[]
    recordId?: number
  } | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // 如果 URL 中有 taskId，从后端加载
  useEffect(() => {
    if (taskId && !state) {
      setLoading(true)
      api.getTaskReview(taskId)
        .then(res => {
          if (res.success && res.data) {
            setTaskData({
              title: res.data.topic,
              content: res.data.review,
              papers: res.data.papers || [],
            })
          } else {
            setError('综述不存在或尚未完成')
          }
        })
        .catch(err => {
          setError('加载失败：' + (err.response?.data?.detail || err.message))
        })
        .finally(() => setLoading(false))
    }
  }, [taskId, state])

  // 确定使用哪个数据源
  const reviewData = state || taskData

  if (error) {
    return (
      <div className="review-page">
        <div className="review-page-header">
          <button className="back-button" onClick={() => navigate('/')}>← 返回首页</button>
        </div>
        <div style={{ textAlign: 'center', padding: '4rem', color: '#666' }}>{error}</div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="review-page">
        <div className="review-page-header">
          <button className="back-button" onClick={() => navigate('/')}>← 返回首页</button>
        </div>
        <div style={{ textAlign: 'center', padding: '4rem', color: '#666' }}>加载中...</div>
      </div>
    )
  }

  if (!reviewData || !reviewData.content) {
    navigate('/')
    return null
  }

  const handleBack = () => {
    navigate('/')
  }

  const handleExport = async () => {
    if (!reviewData.recordId) {
      alert('该综述暂不支持导出')
      return
    }

    try {
      const response = await fetch('/api/records/export', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ record_id: reviewData.recordId })
      })

      if (!response.ok) {
        throw new Error('导出失败')
      }

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
    }
  }

  return (
    <div className="review-page">
      <div className="review-page-header">
        <button className="back-button" onClick={handleBack}>
          ← 返回首页
        </button>
        <h1 className="review-page-title">{reviewData.title}</h1>
        <button className="export-button" onClick={handleExport}>
          导出 Word
        </button>
      </div>
      <ReviewViewer
        title={reviewData.title}
        content={reviewData.content}
        papers={reviewData.papers}
      />
    </div>
  )
}
