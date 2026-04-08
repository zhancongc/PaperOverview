import { useEffect } from 'react'
import './ConfirmModal.css'

interface ConfirmModalProps {
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  onConfirm: () => void
  onCancel: () => void
  type?: 'info' | 'warning' | 'danger'
}

export function ConfirmModal({
  title,
  message,
  confirmText = '确认',
  cancelText = '取消',
  onConfirm,
  onCancel,
  type = 'info'
}: ConfirmModalProps) {
  // Esc 关闭弹窗
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCancel()
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [onCancel])

  const getIcon = () => {
    switch (type) {
      case 'warning':
        return '⚠️'
      case 'danger':
        return '🔒'
      default:
        return '💡'
    }
  }

  const getConfirmButtonClass = () => {
    switch (type) {
      case 'danger':
        return 'confirm-modal-btn confirm-modal-btn-danger'
      case 'warning':
        return 'confirm-modal-btn confirm-modal-btn-warning'
      default:
        return 'confirm-modal-btn confirm-modal-btn-primary'
    }
  }

  return (
    <div className="confirm-modal-overlay" onClick={onCancel}>
      <div className="confirm-modal" onClick={e => e.stopPropagation()}>
        <button className="confirm-modal-close" onClick={onCancel}>&times;</button>

        <div className="confirm-modal-header">
          <span className="confirm-modal-icon">{getIcon()}</span>
          <h2 className="confirm-modal-title">{title}</h2>
        </div>

        <div className="confirm-modal-body">
          <p className="confirm-modal-message">{message}</p>
        </div>

        <div className="confirm-modal-footer">
          <button className="confirm-modal-btn confirm-modal-btn-cancel" onClick={onCancel}>
            {cancelText}
          </button>
          <button className={getConfirmButtonClass()} onClick={onConfirm}>
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  )
}
