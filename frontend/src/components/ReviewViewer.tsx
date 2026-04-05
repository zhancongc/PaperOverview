import { useState, useEffect, useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
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
}

export function ReviewViewer({ title, content, papers = [] }: ReviewViewerProps) {
  const [toc, setToc] = useState<TableOfContents[]>([])
  const [activeId, setActiveId] = useState<string>('')

  // 解析 Markdown 生成目录
  useEffect(() => {
    const lines = content.split('\n')
    const headings: Array<{ id: string; text: string; level: number }> = []

    lines.forEach((line, index) => {
      const match = line.match(/^(#{1,3})\s+(.+)$/)
      if (match) {
        const level = match[1].length
        const text = match[2].trim()
        const id = `heading-${index}`
        headings.push({ id, text, level })
      }
    })

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

        // 找到合适的父节点
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
  }, [content])

  // 监听滚动，高亮当前章节
  useEffect(() => {
    const handleScroll = () => {
      const headings = document.querySelectorAll('[id^="heading-"]')
      const scrollPosition = window.scrollY + 100

      let currentId = ''
      headings.forEach(heading => {
        const element = heading as HTMLElement
        if (element.offsetTop <= scrollPosition) {
          currentId = element.id
        }
      })

      setActiveId(currentId)
    }

    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  // 渲染目录项
  const renderTocItem = (item: TableOfContents) => (
    <li key={item.id} className={`toc-item toc-level-${item.level} ${activeId === item.id ? 'active' : ''}`}>
      <a
        href={`#${item.id}`}
        onClick={(e) => {
          e.preventDefault()
          const element = document.getElementById(item.id)
          if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'start' })
          }
        }}
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
  const getVerificationLinks = (paper: any, index: number) => {
    const links = []

    // 构建搜索查询
    const searchQuery = encodeURIComponent(paper.title)
    const yearQuery = paper.year ? `&as_ylo=${paper.year - 2}&as_yhi=${paper.year + 2}` : ''

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

    // Semantic Scholar（如果有 url）
    if (paper.url) {
      links.push({
        name: 'Semantic Scholar',
        url: paper.url,
        icon: '📚',
        color: '#1a73e8'
      })
    } else {
      links.push({
        name: 'Semantic Scholar',
        url: `https://www.semanticscholar.org/search?q=${searchQuery}`,
        icon: '📚',
        color: '#1a73e8'
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

  // 自定义 Markdown 渲染器，添加 id 到标题
  const components = useMemo(() => ({
    h1: ({ children, ...props }: any) => {
      const text = children?.toString() || ''
      const id = text.toLowerCase().replace(/\s+/g, '-')
      return <h1 id={id} {...props}>{children}</h1>
    },
    h2: ({ children, ...props }: any) => {
      const text = children?.toString() || ''
      const id = text.toLowerCase().replace(/\s+/g, '-')
      return <h2 id={id} {...props}>{children}</h2>
    },
    h3: ({ children, ...props }: any) => {
      const text = children?.toString() || ''
      const id = text.toLowerCase().replace(/\s+/g, '-')
      return <h3 id={id} {...props}>{children}</h3>
    }
  }), [])

  return (
    <div className="review-viewer">
      <div className="review-content-wrapper">
        {/* 侧边栏目录 */}
        <aside className="review-sidebar">
          <div className="toc-header">目录</div>
          <ul className="toc-list">
            {toc.map(renderTocItem)}
          </ul>
        </aside>

        {/* 正文内容 */}
        <main className="review-main">
          <div className="review-body">
            <ReactMarkdown components={components}>
              {content}
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
                          href={verificationLinks.find(l => l.name === 'Semantic Scholar')?.url || verificationLinks[0].url}
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
