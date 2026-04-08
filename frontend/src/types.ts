export interface Paper {
  id: string;
  title: string;
  authors: string[];
  year: number;
  cited_by_count: number;
  is_english: boolean;
  abstract: string;
  type: string;
  doi: string;
  concepts: string[];
  relevance_score?: number;  // 相关性得分
  cited?: boolean;  // 是否被引用
  search_keywords?: string[];  // 匹配的搜索关键词列表
}

export interface Statistics {
  total: number;
  recent_count: number;
  recent_ratio: number;
  english_count: number;
  english_ratio: number;
  total_citations: number;
  avg_citations: number;
}

export interface ReviewRecord {
  id: number;
  topic: string;
  review: string;
  papers: Paper[];
  statistics: Statistics;
  target_count: number;
  recent_years_ratio: number;
  english_ratio: number;
  status: string;
  error_message?: string;
  is_paid?: boolean;
  task_id?: string;
  created_at: string;
  updated_at: string;
}

export interface GenerateResponse {
  success: boolean;
  message: string;
  data?: {
    id?: number;
    topic: string;
    review: string;
    papers: Paper[];
    statistics: Statistics;
    created_at?: string;
    // 三圈分析相关
    analysis?: ThreeCirclesAnalysis;
    framework?: ReviewFramework;
    circles?: CircleSummary[];
    gap_analysis?: GapAnalysis;
    // 框架类型
    framework_type?: string;
    // 搜索查询结果
    search_queries_results?: SearchQueryResult[];
  };
}

export interface RecordsResponse {
  success: boolean;
  count: number;
  records: ReviewRecord[];
}

// 三圈分析相关类型
export interface ThreeCirclesAnalysis {
  methodology: string;
  domain: string;
  optimization: string;
  title: string;
}

export interface CircleResult {
  circle: string;
  name: string;
  query: string;
  description: string;
  papers: Paper[];
  count: number;
}

export interface CircleSummary {
  circle: string;
  name: string;
  count: number;
}

export interface GapAnalysis {
  gap_description: string;
  research_opportunity: string;
  intersection_count: number;
  suggestions: string[];
}

export interface ReviewFramework {
  structure: string;
  description: string;
  sections: Array<{
    title: string;
    description: string;
    key_points: string[];
  }>;
}

export interface ThreeCirclesResponse {
  success: boolean;
  message: string;
  data?: {
    analysis: ThreeCirclesAnalysis;
    circles: CircleResult[];
    gap_analysis: GapAnalysis;
    review_framework: ReviewFramework;
  };
}

// 题目分类相关类型
export type TopicType = 'application' | 'evaluation' | 'theoretical' | 'empirical' | 'general';

// 标签页类型
export type TabType = 'review' | 'papers' | 'history' | 'analysis' | 'search' | 'logs';

// 搜索查询结果详情
export interface SearchQueryResult {
  query: string;
  section: string;
  papers: Array<Paper & { cited?: boolean }>;
  citedCount: number;
}

export interface TopicClassification {
  title: string;
  type: TopicType;
  type_name: string;
  classification_reason: string;
  framework: ReviewFramework;
  outline?: {
    introduction: {
      focus: string;
      key_papers: string[];
    };
    body_sections: Array<{
      title: string;
      focus: string;
      key_points: string[];
      comparison_points: string[];
      search_keywords: string[];
    }>;
    conclusion: {
      focus: string;
    };
  };
  search_queries: Array<{
    query: string;
    section: string;
  }>;
}

export interface ClassifyTopicResponse {
  success: boolean;
  message: string;
  data?: TopicClassification;
}

export interface SmartAnalyzeResponse {
  success: boolean;
  message: string;
  data?: {
    analysis?: TopicClassification;
    circles?: CircleResult[];
    review_framework?: ReviewFramework;
    framework_type: string;
  };
}

// 搜索关键词统计相关类型
export interface KeywordStat {
  keyword: string;
  matched_papers_count: number;
  paper_ids: string[];
}

export interface SearchSourcesResponse {
  success: boolean;
  data: {
    task_id: string;
    total_records: number;
    keyword_stats: KeywordStat[];
  };
}

// 研究方向相关类型
export interface ResearchDirection {
  id: string;
  name: string;
  name_en: string;
  description: string;
  keywords: string[];
  abbreviations: Record<string, string>;
  sub_directions: Record<string, string>;
}

export interface ResearchDirectionsResponse {
  success: boolean;
  data: ResearchDirection[];
}
