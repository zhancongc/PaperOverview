/**
 * 标签页导航组件
 */
import { TabType } from '../types'

interface TabNavigationProps {
  activeTab: TabType
  onTabChange: (tab: TabType) => void
}

export function TabNavigation({ activeTab, onTabChange }: TabNavigationProps) {
  const tabs = [
    { id: 'review' as TabType, label: '📝 综述内容', icon: '✨' },
    { id: 'papers' as TabType, label: '📚 文献列表', icon: '📚' },
    { id: 'search' as TabType, label: '🔎 搜索策略', icon: '🔎' },
    { id: 'logs' as TabType, label: '📋 处理日志', icon: '📋' },
    { id: 'analysis' as TabType, label: '🔍 智能分析', icon: '🔍' },
    { id: 'history' as TabType, label: '📖 历史记录', icon: '📖' }
  ]

  return (
    <div className="tab-navigation">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  )
}
