import { useState, useEffect } from 'react'
import { api } from './api'
import type {
  Paper,
  Statistics,
  ReviewRecord,
  TopicClassification,
  TabType
} from './types'
import { TopicInput } from './components/TopicInput'
import { ConfigPanel } from './components/ConfigPanel'
import { TabNavigation } from './components/TabNavigation'
import { AnalysisPanel } from './components/AnalysisPanel'
import { ReviewPanel } from './components/ReviewPanel'
import { PapersList } from './components/PapersList'
import { HistoryList } from './components/HistoryList'
import { SearchQueriesPanel } from './components/SearchQueriesPanel'
import { LogsPanel } from './components/LogsPanel'
import './App.css'

function App() {
  const [topic, setTopic] = useState('')
  const [loading, setLoading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [searchingPapers, setSearchingPapers] = useState(false)
  const [review, setReview] = useState('')
  const [papers, setPapers] = useState<Paper[]>([])
  const [allPapers, setAllPapers] = useState<Paper[]>([])  // 所有搜索到的文献
  const [statistics, setStatistics] = useState<Statistics | null>(null)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState<TabType>('review')
  const [currentRecordId, setCurrentRecordId] = useState<number | null>(null)

  // 异步任务状态
  const [taskId, setTaskId] = useState<string | null>(null)
  const [taskProgress, setTaskProgress] = useState('')
  const [taskStatus, setTaskStatus] = useState<'idle' | 'polling' | 'completed' | 'failed'>('idle')

  // 查找文献结果
  const [searchPapersLogs, setSearchPapersLogs] = useState<string[]>([])
  const [searchPapersResult, setSearchPapersResult] = useState<any>(null)

  // 配置参数
  const [targetCount, setTargetCount] = useState(50)
  const [recentYearsRatio, setRecentYearsRatio] = useState(0.5)
  const [englishRatio, setEnglishRatio] = useState(0.3)
  const [searchYears, setSearchYears] = useState(10)
  const [maxSearchQueries, setMaxSearchQueries] = useState(8)

  // 分析数据
  const [classification, setClassification] = useState<TopicClassification | null>(null)
  const [frameworkType, setFrameworkType] = useState<string>('')

  // 搜索查询结果
  const [searchQueries, setSearchQueries] = useState<any[]>([])

  // 历史记录
  const [records, setRecords] = useState<ReviewRecord[]>([])
  const [loadingHistory, setLoadingHistory] = useState(false)

  // 加载历史记录
  useEffect(() => {
    loadRecords()
  }, [])

  const loadRecords = async () => {
    setLoadingHistory(true)
    try {
      const response = await api.getRecords()
      if (response.success) {
        setRecords(response.records)
      }
    } catch (err) {
      console.error('加载历史记录失败:', err)
    } finally {
      setLoadingHistory(false)
    }
  }

  const handleAnalyze = async () => {
    if (!topic.trim()) {
      setError('请输入论文题目')
      return
    }

    setAnalyzing(true)
    setError('')
    setActiveTab('analysis')
    setClassification(null)

    try {
      const response = await api.smartAnalyze(topic)
      if (response.success && response.data) {
        const data = response.data
        setFrameworkType(data.framework_type || '')

        if (data.analysis) {
          setClassification(data.analysis)
          // 保存搜索查询
          if (data.analysis.search_queries) {
            setSearchQueries(data.analysis.search_queries.map((q: any) => ({
              ...q,
              papers: [],
              citedCount: 0
            })))
          }
        }
      }
    } catch (err) {
      setError('分析失败，请检查后端服务')
      console.error('Analyze error:', err)
    } finally {
      setAnalyzing(false)
    }
  }

  const handleSearchPapers = async () => {
    if (!topic.trim()) {
      setError('请输入论文题目')
      return
    }

    setSearchingPapers(true)
    setError('')
    setActiveTab('logs')
    setSearchPapersLogs([])
    setSearchPapersResult(null)
    setAllPapers([])
    setPapers([])

    try {
      const response = await api.searchPapersOnly(topic, {
        targetCount,
        recentYearsRatio,
        englishRatio,
        searchYears,
        maxSearchQueries
      })

      if (response.success && response.data) {
        const data = response.data

        // 保存日志
        if (data.logs) {
          setSearchPapersLogs(data.logs)
        }

        // 保存结果
        setSearchPapersResult(data)

        // 更新文献列表
        if (data.all_papers) {
          setAllPapers(data.all_papers)
        }
        if (data.filtered_papers) {
          setPapers(data.filtered_papers)
        }

        // 更新统计信息
        if (data.statistics) {
          setStatistics(data.statistics)
        }

        // 更新搜索查询结果
        if (data.search_queries_results) {
          setSearchQueries(data.search_queries_results)
        }

        // 保存框架信息
        if (data.framework) {
          setFrameworkType(data.framework.outline?.structure || '通用结构')
        }

        // 切换到文献列表标签页
        setActiveTab('papers')
      }
    } catch (err) {
      setError('查找文献失败，请检查后端服务')
      console.error('Search papers error:', err)
    } finally {
      setSearchingPapers(false)
    }
  }

  const handleGenerate = async () => {
    if (!topic.trim()) {
      setError('请输入论文题目')
      return
    }

    setLoading(true)
    setError('')
    setActiveTab('review')
    setReview('')
    setPapers([])
    setStatistics(null)
    setTaskStatus('polling')
    setTaskProgress('正在提交任务...')

    try {
      // 1. 提交任务
      const submitResponse = await api.submitReviewTask(topic, {
        targetCount,
        recentYearsRatio,
        englishRatio,
        searchYears,
        maxSearchQueries
      })

      if (!submitResponse.success || !submitResponse.data?.task_id) {
        setError(submitResponse.message || '任务提交失败')
        setTaskStatus('failed')
        setLoading(false)
        return
      }

      const currentTaskId = submitResponse.data.task_id
      setTaskId(currentTaskId)

      // 2. 轮询任务状态
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await api.getTaskStatus(currentTaskId)

          if (!statusResponse.success) {
            setError('查询任务状态失败')
            setTaskStatus('failed')
            clearInterval(pollInterval)
            setLoading(false)
            return
          }

          const taskInfo = statusResponse.data

          // 更新进度
          if (taskInfo.progress?.message) {
            setTaskProgress(taskInfo.progress.message)
          } else {
            setTaskProgress(`任务状态: ${taskInfo.status}`)
          }

          // 检查是否完成
          if (taskInfo.status === 'completed' && taskInfo.result) {
            clearInterval(pollInterval)
            setTaskStatus('completed')

            const data = taskInfo.result
            setReview(data.review)
            setPapers(data.papers)
            setStatistics(data.statistics)

            if (data.id) {
              setCurrentRecordId(data.id)
            }

            // 更新搜索查询的被引用论文数量
            if (data.search_queries_results) {
              setSearchQueries(data.search_queries_results)
            }

            loadRecords()
            setLoading(false)
          } else if (taskInfo.status === 'failed') {
            clearInterval(pollInterval)
            setTaskStatus('failed')
            setError(taskInfo.error || '任务执行失败')
            setLoading(false)
          }
        } catch (err) {
          clearInterval(pollInterval)
          setTaskStatus('failed')
          setError('查询任务状态出错')
          setLoading(false)
          console.error(err)
        }
      }, 20000) // 每20秒轮询一次

    } catch (err) {
      setTaskStatus('failed')
      setError('提交任务失败，请检查后端服务是否正常运行')
      console.error(err)
      setLoading(false)
    }
  }

  const handleExportRecord = async (id: number, event: React.MouseEvent) => {
    event.stopPropagation()
    try {
      const blob = await api.exportReview(id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const record = records.find(r => r.id === id)
      const filename = record ? record.topic.replace(/[\/\\:]/g, '-') : 'review'
      a.download = `${filename}.docx`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      setError('导出失败')
      console.error('Export error:', err)
    }
  }

  const handleDeleteRecord = async (id: number) => {
    try {
      await api.deleteRecord(id)
      setRecords(records.filter(r => r.id !== id))
    } catch (err) {
      console.error('Delete failed:', err)
    }
  }

  const handleLoadRecord = async (id: number) => {
    try {
      const response = await api.getRecord(id)
      if (response.success && response.record) {
        const record = response.record
        setTopic(record.topic)
        setReview(record.review)
        setPapers(record.papers)
        setStatistics(record.statistics)
        setCurrentRecordId(record.id)
        setActiveTab('review')
      }
    } catch (err) {
      setError('加载记录失败')
      console.error(err)
    }
  }

  const handleExportCurrent = async () => {
    if (!currentRecordId) {
      setError('没有可导出的综述')
      return
    }
    await handleExportRecord(currentRecordId, { stopPropagation: () => {} } as React.MouseEvent)
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>📚 论文综述生成器</h1>
        <p className="subtitle">基于AI的智能文献综述生成工具</p>
      </header>

      <main className="app-main">
        <ConfigPanel
          targetCount={targetCount}
          recentYearsRatio={recentYearsRatio}
          englishRatio={englishRatio}
          searchYears={searchYears}
          maxSearchQueries={maxSearchQueries}
          onTargetCountChange={setTargetCount}
          onRecentYearsRatioChange={setRecentYearsRatio}
          onEnglishRatioChange={setEnglishRatio}
          onSearchYearsChange={setSearchYears}
          onMaxSearchQueriesChange={setMaxSearchQueries}
          disabled={loading || analyzing}
        />
        <TopicInput
          value={topic}
          onChange={setTopic}
          onAnalyze={handleAnalyze}
          onSearchPapers={handleSearchPapers}
          onGenerate={handleGenerate}
          loading={loading}
          analyzing={analyzing}
          searchingPapers={searchingPapers}
          showExportButton={!!review}
          onExport={handleExportCurrent}
          error={error}
        />

        <TabNavigation activeTab={activeTab} onTabChange={setActiveTab} />

        <div className="tab-content">
          {activeTab === 'review' && (
            <ReviewPanel review={review} statistics={statistics} />
          )}

          {activeTab === 'papers' && (
            <PapersList papers={papers} />
          )}

          {activeTab === 'search' && (
            <SearchQueriesPanel
              searchQueries={searchQueries}
              allPapersCount={papers.length}
              citedPapersCount={statistics?.total || 0}
            />
          )}

          {activeTab === 'logs' && (
            <LogsPanel
              logs={searchPapersLogs}
              framework={searchPapersResult?.framework}
              allPapersCount={allPapers.length}
              filteredPapersCount={papers.length}
              statistics={statistics}
            />
          )}

          {activeTab === 'analysis' && (
            <AnalysisPanel
              classification={classification}
              frameworkType={frameworkType}
            />
          )}

          {activeTab === 'history' && (
            <HistoryList
              records={records}
              loading={loadingHistory}
              onLoadRecord={handleLoadRecord}
              onDeleteRecord={handleDeleteRecord}
              onExportRecord={handleExportRecord}
            />
          )}
        </div>
      </main>

      <footer className="app-footer">
        <p>© 2024 论文综述生成器 | 基于 FastAPI + React 构建</p>
      </footer>
    </div>
  )
}

export default App
