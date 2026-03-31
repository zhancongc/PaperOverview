/**
 * 历史记录列表组件
 */
import { ReviewRecord } from '../types'

interface HistoryListProps {
  records: ReviewRecord[]
  loading: boolean
  onLoadRecord: (id: number) => void
  onDeleteRecord: (id: number) => void
  onExportRecord: (id: number, event: React.MouseEvent) => Promise<void>
}

export function HistoryList({ records, loading, onLoadRecord, onDeleteRecord, onExportRecord }: HistoryListProps) {
  const handleDelete = (id: number, event: React.MouseEvent) => {
    event.stopPropagation()
    if (confirm('确定要删除这条记录吗？')) {
      onDeleteRecord(id)
    }
  }

  const handleExport = async (id: number, event: React.MouseEvent) => {
    event.stopPropagation()
    await onExportRecord(id, event)
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

  if (loading) {
    return (
      <div className="history-loading">
        <div className="spinner"></div>
        <p>加载历史记录中...</p>
      </div>
    )
  }

  if (!records || records.length === 0) {
    return (
      <div className="history-placeholder">
        <p>暂无历史记录</p>
      </div>
    )
  }

  return (
    <div className="history-list">
      <div className="history-header">
        <h3>📖 历史记录 ({records.length} 条)</h3>
      </div>

      <div className="records-grid">
        {records.map((record) => (
          <div
            key={record.id}
            className="record-card"
            onClick={() => onLoadRecord(record.id)}
          >
            <div className="record-header">
              <h4 className="record-title">{record.topic}</h4>
              <div className="record-actions">
                <button
                  onClick={handleExport.bind(null, record.id)}
                  className="record-export-btn"
                  title="导出Word"
                >
                  📥
                </button>
                <button
                  onClick={handleDelete.bind(null, record.id)}
                  className="record-delete-btn"
                  title="删除"
                >
                  🗑
                </button>
              </div>
            </div>

            <div className="record-meta">
              <span className={`record-status record-status-${record.status}`}>
                {record.status === 'success' ? '✓ 完成' : record.status === 'failed' ? '✗ 失败' : '⏳ 进行中'}
              </span>
              <span className="record-date">{formatDate(record.created_at)}</span>
            </div>

            {record.statistics && (
              <div className="record-stats">
                <span>文献: {record.statistics.total || 0} 篇</span>
                <span>英文: {Math.round((record.statistics.english_ratio || 0) * 100)}%</span>
                <span>近5年: {Math.round((record.statistics.recent_ratio || 0) * 100)}%</span>
              </div>
            )}

            {record.error_message && (
              <div className="record-error">
                {record.error_message}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
