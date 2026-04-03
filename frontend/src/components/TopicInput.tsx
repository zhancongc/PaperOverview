/**
 * 主题输入组件
 */

interface TopicInputProps {
  value: string
  onChange: (value: string) => void
  onAnalyze: () => void
  onSearchPapers: () => void
  onGenerate: () => void
  loading: boolean
  analyzing: boolean
  searchingPapers: boolean
  showExportButton: boolean
  onExport: () => void
  error: string
}

export function TopicInput({
  value,
  onChange,
  onAnalyze,
  onSearchPapers,
  onGenerate,
  loading,
  analyzing,
  searchingPapers,
  showExportButton,
  onExport,
  error
}: TopicInputProps) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      onGenerate()
    }
  }

  return (
    <div className="input-section">
      {/* 论文标题输入框独占一行 */}
      <div className="topic-input-row">
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="请输入论文题目（例如：基于QFD和FMEA的软件外包项目质量管理）"
          className="topic-input"
          disabled={loading || analyzing || searchingPapers}
        />
      </div>

      {/* 按钮放在下一行 */}
      <div className="action-buttons-row">
        <button
          onClick={onAnalyze}
          disabled={loading || analyzing || searchingPapers || !value.trim()}
          className="analyze-btn"
        >
          {analyzing ? '分析中...' : '🔍 智能分析'}
        </button>
        <button
          onClick={onSearchPapers}
          disabled={loading || analyzing || searchingPapers || !value.trim()}
          className="search-papers-btn"
        >
          {searchingPapers ? '查找中...' : '📚 查找文献'}
        </button>
        <button
          onClick={onGenerate}
          disabled={loading || analyzing || searchingPapers || !value.trim()}
          className="generate-btn"
        >
          {loading ? '生成中...' : '✨ 生成综述'}
        </button>
        {showExportButton && (
          <button
            onClick={onExport}
            className="export-btn"
          >
            📥 导出Word
          </button>
        )}
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {(loading || analyzing || searchingPapers) && (
        <div className="loading">
          <div className="spinner"></div>
          <p>
            {analyzing ? '正在分析题目类型...' :
             searchingPapers ? '正在查找文献...' :
             '正在检索文献并生成综述，请稍候...'}
          </p>
        </div>
      )}
    </div>
  )
}
