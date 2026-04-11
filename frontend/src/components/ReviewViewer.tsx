import { useState, useEffect, useMemo, useRef, useCallback, Fragment } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { CitationMarker } from './CitationTooltip'
import './ReviewViewer.css'

interface TableOfContents {
  id: string
  text: string
  level: number
  children: TableOfContents[]
}

interface ReviewViewerProps {
  title: string
  content: string
  papers?: Array<{
    id: string
    title: string
    authors: string[]
    year: number
    doi?: string
    url?: string
  }>
  hasPurchased?: boolean
  onTocUpdate?: (toc: TableOfContents[]) => void
  onRequestUnlock?: () => void
}

export function ReviewViewer({ content, papers = [], hasPurchased = false, onTocUpdate, onRequestUnlock }: ReviewViewerProps) {
  const [toc, setToc] = useState<TableOfContents[]>([])
  const [activeId, setActiveId] = useState<string>('')
  useRef<HTMLElement>(null)
  const isClickScrolling = useRef(false)

  // 渲染带引用标记的文本
  const renderTextWithCitations = useCallback((text: any): any => {
    // 处理 null/undefined
    if (text === null || text === undefined) {
      return text
    }

    // 如果是数组，递归处理每个元素
    if (Array.isArray(text)) {
      return text.map((item, i) => (
        <Fragment key={i}>{renderTextWithCitations(item)}</Fragment>
      ))
    }

    // 如果是对象（React 元素），递归处理其 children
    if (typeof text === 'object' && text !== null) {
      // 如果已经是 React 元素，直接返回（避免重复处理）
      // 简单检查：是否有 $$typeof 和 type 属性
      if (text.$$typeof && text.type) {
        return text
      }
      return text
    }

    // 处理字符串
    if (typeof text !== 'string') {
      return text
    }

    // 清理：去掉引用标记前面不必要的逗号和空格（如 ", [1]" -> "[1]"）
    let cleanedText = text.replace(/,\s*(?=\[\d+\])/g, ' ')

    // 清理嵌套的方括号格式：[[11],[14]] -> [11][14] -> 后续会合并为 [11, 14]
    // 匹配 [[开头，]] 结尾，中间是 [数字],[数字]... 格式
    cleanedText = cleanedText.replace(/\[\[([\d,\[\]\s]+)\]\]/g, (_, content) => {
      // content 如 "[11],[14]" 或 "[11],[14],[15]"
      // 去掉外层方括号后变成 [11],[14]，后续步骤会处理
      return content
    })

    // 检测并排序连续的引用标记
    // 匹配连续的 [数字] 引用，如 [5][8][4]
    const consecutiveCitationsPattern = /(\[\d+\]\s*){2,}/g
    cleanedText = cleanedText.replace(consecutiveCitationsPattern, (match) => {
      // 提取所有引用数字
      const citations = match.match(/\[(\d+)\]/g)
      if (citations) {
        const numbers = citations.map(c => parseInt(c.replace(/[\[\]]/g, '')))
        // 排序
        numbers.sort((a, b) => a - b)
        // 重新组合为 [1, 2, 3] 格式
        return `[${numbers.join(', ')}]`
      }
      return match
    })

    // 匹配 [数字] 或 [数字, 数字, ...] 格式的引用
    // 使用捕获组保留分隔符
    const parts = cleanedText.split(/(\[\d+(?:,\s*\d+)*\])/g)

    return parts.map((part, index) => {
      // 跳过空字符串
      if (part === '' || part === ' ') {
        return null
      }

      // 检查是否是引用标记
      const match = part.match(/\[(\d+(?:,\s*\d+)*)\]/)
      if (match) {
        const indices = match[1].split(',').map((s) => parseInt(s.trim()))
        // 如果是单个引用
        if (indices.length === 1) {
          const citationIndex = indices[0] - 1
          const paper = papers[citationIndex]
          console.log(`[ReviewViewer] Single citation [${indices[0]}]`, { citationIndex, paper, papersLength: papers.length })
          return <CitationMarker key={`${index}-${indices[0]}`} index={indices[0]} paper={paper} />
        }
        // 如果是多个引用 [1,2,3]，分别渲染
        return (
          <span key={index}>
            {indices.map((idx, i) => {
              const citationIndex = idx - 1
              const paper = papers[citationIndex]
              console.log(`[ReviewViewer] Multi citation [${idx}]`, { citationIndex, paper, papersLength: papers.length })
              return (
                <Fragment key={`${index}-${i}-${idx}`}>
                  {i > 0 && ', '}
                  <CitationMarker index={idx} paper={paper} />
                </Fragment>
              )
            })}
          </span>
        )
      }
      return part
    }).filter(Boolean)
  }, [papers])

  // 生成标题 ID（与 Markdown 渲染器保持一致）
  const headingIdMap = useRef<Map<string, string>>(new Map())

  // 统一的 id 生成函数
  const makeId = (text: string) => text.toLowerCase().replace(/[^\w\u4e00-\u9fff]+/g, '-').replace(/^-|-$/g, '')

  // 统一的文本清洗：去掉 Markdown 格式标记
  const stripMd = (text: string) => text.replace(/\*\*/g, '').replace(/\*/g, '').replace(/__/g, '').replace(/_/g, '').trim()

  // 从 React children 中递归提取纯文本
  const extractText = (children: any): string => {
    if (typeof children === 'string') return stripMd(children)
    if (typeof children === 'number') return String(children)
    if (Array.isArray(children)) return children.map(extractText).join('')
    if (children?.props?.children) return extractText(children.props.children)
    return ''
  }

  // 预处理 content：把没有 # 前缀但以 **数字.数字** 开头的粗体行转为 #### 标题
  const processedContent = useMemo(() => {
    return content.split('\n').map(line => {
      if (line.match(/^\*\*\d+\.\d+/) && !line.startsWith('#')) {
        return '#### ' + line
      }
      return line
    }).join('\n')
  }, [content])

  // 解析 Markdown 生成目录
  useEffect(() => {
    const lines = processedContent.split('\n')
    const headings: Array<{ id: string; text: string; level: number }> = []
    const idCount: Record<string, number> = {}

    lines.forEach((line) => {
      const match = line.match(/^(#{1,4})\s+(.+)$/)
      if (match) {
        const level = match[1].length
        const rawText = stripMd(match[2])
        const baseId = makeId(rawText)
        idCount[baseId] = (idCount[baseId] || 0) + 1
        const id = idCount[baseId] > 1 ? `${baseId}-${idCount[baseId]}` : baseId

        headings.push({ id, text: rawText, level })
        headingIdMap.current.set(rawText, id)
      }
    })

    // 标准化标题级别：让最高级标题从 level 1 开始
    if (headings.length > 0) {
      const minLevel = Math.min(...headings.map(h => h.level))
      headings.forEach(h => { h.level = h.level - minLevel + 1 })
    }

    // 构建嵌套的目录结构
    const buildTocTree = (items: Array<{ id: string; text: string; level: number }>): TableOfContents[] => {
      const result: TableOfContents[] = []
      const stack: Array<{ node: TableOfContents; level: number }> = []

      items.forEach(item => {
        const node: TableOfContents = {
          id: item.id,
          text: item.text,
          level: item.level,
          children: []
        }

        while (stack.length > 0 && stack[stack.length - 1].level >= item.level) {
          stack.pop()
        }

        if (stack.length === 0) {
          result.push(node)
        } else {
          stack[stack.length - 1].node.children.push(node)
        }

        stack.push({ node, level: item.level })
      })

      return result
    }

    setToc(buildTocTree(headings))
  }, [processedContent])

  // 通知父组件 TOC 更新
  useEffect(() => {
    if (onTocUpdate && toc.length > 0) {
      onTocUpdate(toc)
    }
  }, [toc, onTocUpdate])

  // 监听滚动，高亮当前章节
  useEffect(() => {
    const handleScroll = () => {
      if (isClickScrolling.current) return

      const headings = document.querySelectorAll('.review-body h1[id], .review-body h2[id], .review-body h3[id], .review-body h4[id]')
      const scrollPosition = window.scrollY + 100

      let currentId = ''
      headings.forEach(heading => {
        const element = heading as HTMLElement
        if (element.offsetTop <= scrollPosition) {
          currentId = element.id
        }
      })

      if (currentId !== activeId) {
        setActiveId(currentId)
      }
    }

    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [activeId])

  // 点击目录项滚动到对应标题
  const handleTocClick = useCallback((id: string) => (e: any) => {
    e.preventDefault()
    const element = document.getElementById(id) as HTMLElement
    if (!element) return

    isClickScrolling.current = true
    setActiveId(id)

    element.scrollIntoView({ behavior: 'smooth', block: 'start' })

    window.scrollTo({ top: element.offsetTop - 80, behavior: 'smooth' })

    setTimeout(() => {
      isClickScrolling.current = false
    }, 800)
  }, [])

  // 渲染目录项
  const renderTocItem = (item: TableOfContents) => (
    <li key={item.id} className={`toc-item toc-level-${item.level} ${activeId === item.id ? 'active' : ''}`}>
      <a
        href={`#${item.id}`}
        onClick={handleTocClick(item.id)}
      >
        {item.text}
      </a>
      {item.children.length > 0 && (
        <ul className="toc-children">
          {item.children.map(renderTocItem)}
        </ul>
      )}
    </li>
  )

  // 自定义 Markdown 渲染器，添加 id 到标题（与目录 ID 保持一致）
  const components = useMemo(() => ({
    h1: ({ children, ...props }: any) => {
      const text = extractText(children)
      const id = headingIdMap.current.get(text) || makeId(text)
      return <h1 id={id} {...props}>{children}</h1>
    },
    h2: ({ children, ...props }: any) => {
      const text = extractText(children)
      const id = headingIdMap.current.get(text) || makeId(text)
      return <h2 id={id} {...props}>{children}</h2>
    },
    h3: ({ children, ...props }: any) => {
      const text = extractText(children)
      const id = headingIdMap.current.get(text) || makeId(text)
      return <h3 id={id} {...props}>{children}</h3>
    },
    h4: ({ children, ...props }: any) => {
      const text = extractText(children)
      const id = headingIdMap.current.get(text) || makeId(text)
      return <h4 id={id} {...props}>{children}</h4>
    },
    // 自定义段落渲染，处理引用标记
    p: ({ children, ...props }: any) => {
      return (
        <p {...props}>
          {Array.isArray(children)
            ? children.map((child, i) => <Fragment key={i}>{renderTextWithCitations(child)}</Fragment>)
            : renderTextWithCitations(children)
          }
        </p>
      )
    },
    // 列表项也处理引用标记
    li: ({ children, ...props }: any) => {
      return (
        <li {...props}>
          {Array.isArray(children)
            ? children.map((child, i) => <Fragment key={i}>{renderTextWithCitations(child)}</Fragment>)
            : renderTextWithCitations(children)
          }
        </li>
      )
    },
    // 表格单元格也处理引用标记
    td: ({ children, ...props }: any) => {
      return (
        <td {...props}>
          {Array.isArray(children)
            ? children.map((child, i) => <Fragment key={i}>{renderTextWithCitations(child)}</Fragment>)
            : renderTextWithCitations(children)
          }
        </td>
      )
    },
    // 表格标题单元格也处理引用标记
    th: ({ children, ...props }: any) => {
      return (
        <th {...props}>
          {Array.isArray(children)
            ? children.map((child, i) => <Fragment key={i}>{renderTextWithCitations(child)}</Fragment>)
            : renderTextWithCitations(children)
          }
        </th>
      )
    },
    // 粗体文本也处理引用标记
    strong: ({ children, ...props }: any) => {
      return (
        <strong {...props}>
          {Array.isArray(children)
            ? children.map((child, i) => <Fragment key={i}>{renderTextWithCitations(child)}</Fragment>)
            : renderTextWithCitations(children)
          }
        </strong>
      )
    },
    // 斜体文本也处理引用标记
    em: ({ children, ...props }: any) => {
      return (
        <em {...props}>
          {Array.isArray(children)
            ? children.map((child, i) => <Fragment key={i}>{renderTextWithCitations(child)}</Fragment>)
            : renderTextWithCitations(children)
          }
        </em>
      )
    }
  }), [headingIdMap, makeId, renderTextWithCitations])

  return (
    <div className={`review-viewer ${!hasPurchased ? 'review-protected' : ''}`}>
      <div className="review-content-wrapper">
        {/* 侧边栏目录 */}
        <aside className="review-sidebar">
          <div className="toc-header">目录</div>
          <ul className="toc-list">
            {toc.map(renderTocItem)}
          </ul>
        </aside>

        {/* 正文内容 */}
        <main className="review-main"
          onContextMenu={(e) => !hasPurchased && e.preventDefault()}
          onCopy={(e) => !hasPurchased && e.preventDefault()}
          onCut={(e) => !hasPurchased && e.preventDefault()}
        >
          {!hasPurchased && (
            <div className="review-watermark" onClick={onRequestUnlock} style={onRequestUnlock ? { cursor: 'pointer' } : undefined}>
              <span className="watermark-text">AutoOverview 预览版</span>
              <span className="watermark-subtext">购买后解锁无水印 Word 导出</span>
            </div>
          )}
          <div className="review-body">
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
              {processedContent}
            </ReactMarkdown>
          </div>
        </main>
      </div>
    </div>
  )
}
