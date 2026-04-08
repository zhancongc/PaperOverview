import { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
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
}

export function ReviewViewer({ content, papers = [], hasPurchased = false }: ReviewViewerProps) {
  const [toc, setToc] = useState<TableOfContents[]>([])
  const [activeId, setActiveId] = useState<string>('')
  useRef<HTMLElement>(null)
  const isClickScrolling = useRef(false)

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
  const handleTocClick = useCallback((id: string) => (e: React.MouseEvent) => {
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

  // 生成第三方平台验证链接
  const getVerificationLinks = (paper: any, _index: number) => {
    const links = []

    // 构建搜索查询
    const searchQuery = encodeURIComponent(paper.title)
    void (paper.year ? `&as_ylo=${paper.year - 2}&as_yhi=${paper.year + 2}` : '')

    // Google Scholar
    links.push({
      name: 'Google Scholar',
      url: `https://scholar.google.com/scholar?q=${searchQuery}`,
      icon: '🔬',
      color: '#4285f4'
    })

    // 百度学术
    links.push({
      name: '百度学术',
      url: `https://xueshu.baidu.com/s?wd=${searchQuery}`,
      icon: '🎓',
      color: '#2932e1'
    })

    // 学术搜索验证
    if (paper.url) {
      links.push({
        name: '查看原文',
        url: paper.url,
        icon: '📄',
        color: '#1a73e8'
      })
    }
    if (paper.doi) {
      links.push({
        name: 'DOI',
        url: `https://doi.org/${paper.doi}`,
        icon: '🔗',
        color: '#7f8c8d'
      })
    }

    // DOI
    if (paper.doi) {
      links.push({
        name: 'DOI',
        url: `https://doi.org/${paper.doi}`,
        icon: '🔗',
        color: '#7f8c8d'
      })
    }

    return links
  }

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
    }
  }), [])

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
            <div className="review-watermark">
              <span className="watermark-text">AutoOverview 预览版</span>
              <span className="watermark-subtext">购买后解锁无水印 Word 导出</span>
            </div>
          )}
          <div className="review-body">
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
              {processedContent}
            </ReactMarkdown>
          </div>

          {/* 参考文献 */}
          {papers.length > 0 && (
            <div className="review-references">
              <h2>参考文献</h2>
              <ol className="references-list">
                {papers.map((paper, index) => {
                  const verificationLinks = getVerificationLinks(paper, index)
                  return (
                    <li key={paper.id} className="reference-item">
                      <div className="reference-header">
                        <span className="ref-number">{index + 1}.</span>
                        <div className="ref-verification">
                          {verificationLinks.map((link) => (
                            <a
                              key={link.name}
                              href={link.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="verification-link"
                              title={`在 ${link.name} 中验证`}
                              style={{ '--link-color': link.color } as any}
                            >
                              <span className="link-icon">{link.icon}</span>
                              <span className="link-name">{link.name}</span>
                            </a>
                          ))}
                        </div>
                      </div>
                      <div className="ref-content">
                        <a
                          href={verificationLinks[0]?.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="ref-title-link"
                          title="点击在第三方平台查看"
                        >
                          {paper.title}
                        </a>
                        <div className="ref-meta">
                          <span className="ref-authors">{paper.authors.join(', ')}</span>
                          <span className="ref-year"> ({paper.year})</span>
                        </div>
                      </div>
                    </li>
                  )
                })}
              </ol>
              <div className="references-notice">
                <span className="notice-icon">💡</span>
                <span className="notice-text">
                  点击文献标题或右侧平台图标，可在第三方平台验证文献真实性
                </span>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
