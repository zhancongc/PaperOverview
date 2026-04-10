import { useMemo } from 'react'
import './CitationFormatSelector.css'

type CitationFormat = 'ieee' | 'apa' | 'mla' | 'gb_t_7714'

interface CitationFormatSelectorProps {
  currentFormat: CitationFormat
  onFormatChange: (format: CitationFormat) => void
  disabled?: boolean
}

const FORMAT_LABELS: Record<CitationFormat, string> = {
  ieee: 'IEEE',
  apa: 'APA',
  mla: 'MLA',
  gb_t_7714: 'GB/T 7714'
}

const FORMAT_DESCRIPTIONS: Record<CitationFormat, string> = {
  ieee: '工程技术领域常用格式',
  apa: '心理学、教育学等领域常用格式',
  mla: '人文学科常用格式',
  gb_t_7714: '中国国家标准引用格式'
}

export function CitationFormatSelector({
  currentFormat,
  onFormatChange,
  disabled = false
}: CitationFormatSelectorProps) {
  const formats = useMemo(() => Object.keys(FORMAT_LABELS) as CitationFormat[], [])

  return (
    <div className="citation-format-selector">
      <label className="format-label">引用格式：</label>
      <div className="format-options">
        {formats.map((format) => (
          <button
            key={format}
            className={`format-button ${currentFormat === format ? 'active' : ''}`}
            onClick={() => onFormatChange(format)}
            disabled={disabled}
            title={FORMAT_DESCRIPTIONS[format]}
          >
            {FORMAT_LABELS[format]}
          </button>
        ))}
      </div>
    </div>
  )
}
