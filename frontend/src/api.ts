import axios from 'axios';
import type {
  GenerateResponse,
  RecordsResponse,
  ReviewRecord,
  ThreeCirclesResponse,
  ClassifyTopicResponse,
  SmartAnalyzeResponse,
  ResearchDirectionsResponse
} from './types';

const API_BASE = '/api';

// 异步任务类型
export interface TaskSubmitResponse {
  success: boolean;
  message: string;
  data?: {
    task_id: string;
    topic: string;
    status: string;
    poll_url: string;
  };
}

export interface TaskInfo {
  task_id: string;
  topic: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
  progress?: {
    step: string;
    message: string;
  };
  result?: any;
  has_result: boolean;
}

export const api = {
  // 智能分析（推荐）
  async smartAnalyze(topic: string): Promise<SmartAnalyzeResponse> {
    const response = await axios.post(`${API_BASE}/smart-analyze`, { topic });
    return response.data;
  },

  // 题目分类
  async classifyTopic(topic: string): Promise<ClassifyTopicResponse> {
    const response = await axios.post(`${API_BASE}/classify-topic`, { topic });
    return response.data;
  },

  // 普通综述生成
  async generateReview(
    topic: string,
    options: {
      targetCount?: number;
      recentYearsRatio?: number;
      englishRatio?: number;
    } = {}
  ): Promise<GenerateResponse> {
    const response = await axios.post(`${API_BASE}/generate`, {
      topic,
      target_count: options.targetCount ?? 50,
      recent_years_ratio: options.recentYearsRatio ?? 0.5,
      english_ratio: options.englishRatio ?? 0.3
    });
    return response.data;
  },

  // 智能生成综述（异步模式）
  async submitReviewTask(
    topic: string,
    options: {
      researchDirectionId?: string;
      targetCount?: number;
      recentYearsRatio?: number;
      englishRatio?: number;
      searchYears?: number;
      maxSearchQueries?: number;
    } = {}
  ): Promise<TaskSubmitResponse> {
    const response = await axios.post(`${API_BASE}/smart-generate`, {
      topic,
      research_direction_id: options.researchDirectionId ?? '',
      target_count: options.targetCount ?? 50,
      recent_years_ratio: options.recentYearsRatio ?? 0.5,
      english_ratio: options.englishRatio ?? 0.3,
      search_years: options.searchYears ?? 10,
      max_search_queries: options.maxSearchQueries ?? 8
    });
    return response.data;
  },

  // 查找文献（不生成综述）
  async searchPapersOnly(
    topic: string,
    options: {
      researchDirectionId?: string;
      targetCount?: number;
      recentYearsRatio?: number;
      englishRatio?: number;
      searchYears?: number;
      maxSearchQueries?: number;
    } = {}
  ): Promise<{ success: boolean; message: string; data: any }> {
    const response = await axios.post(`${API_BASE}/search-papers-only`, {
      topic,
      research_direction_id: options.researchDirectionId ?? '',
      target_count: options.targetCount ?? 50,
      recent_years_ratio: options.recentYearsRatio ?? 0.5,
      english_ratio: options.englishRatio ?? 0.3,
      search_years: options.searchYears ?? 10,
      max_search_queries: options.maxSearchQueries ?? 8
    });
    return response.data;
  },

  // 获取任务状态
  async getTaskStatus(taskId: string): Promise<{ success: boolean; data: TaskInfo }> {
    const response = await axios.get(`${API_BASE}/tasks/${taskId}`);
    return response.data;
  },

  // 通过 task_id 获取综述结果
  async getTaskReview(taskId: string): Promise<{ success: boolean; data: {
    task_id: string;
    topic: string;
    review: string;
    papers: any[];
    cited_papers_count: number;
    created_at: string;
    statistics: any;
    record_id?: number;
  } }> {
    const response = await axios.get(`${API_BASE}/tasks/${taskId}/review`);
    return response.data;
  },

  // 三圈分析
  async analyzeThreeCircles(topic: string): Promise<ThreeCirclesResponse> {
    const response = await axios.post(`${API_BASE}/analyze-three-circles`, { topic });
    return response.data;
  },

  // 三圈综述生成
  async generateThreeCirclesReview(
    topic: string,
    options: {
      targetCount?: number;
      recentYearsRatio?: number;
      englishRatio?: number;
    } = {}
  ): Promise<GenerateResponse> {
    const response = await axios.post(`${API_BASE}/generate-three-circles`, {
      topic,
      target_count: options.targetCount ?? 50,
      recent_years_ratio: options.recentYearsRatio ?? 0.5,
      english_ratio: options.englishRatio ?? 0.3
    });
    return response.data;
  },

  // 历史记录
  async getRecords(skip: number = 0, limit: number = 20): Promise<RecordsResponse> {
    const response = await axios.get(`${API_BASE}/records`, {
      params: { skip, limit }
    });
    return response.data;
  },

  async getRecord(id: number): Promise<{ success: boolean; record: ReviewRecord }> {
    const response = await axios.get(`${API_BASE}/records/${id}`);
    return response.data;
  },

  async deleteRecord(id: number): Promise<{ success: boolean; message: string }> {
    const response = await axios.delete(`${API_BASE}/records/${id}`);
    return response.data;
  },

  // 导出综述为 Word
  async exportReview(recordId: number): Promise<Blob> {
    const response = await axios.post(`${API_BASE}/records/export`, {
      record_id: recordId
    }, {
      responseType: 'blob'
    });
    return response.data;
  },

  // 健康检查
  async checkHealth(): Promise<{ status: string; deepseek_configured: boolean }> {
    const response = await axios.get(`${API_BASE}/health`);
    return response.data;
  },

  // 获取研究方向列表
  async getResearchDirections(): Promise<ResearchDirectionsResponse> {
    const response = await axios.get(`${API_BASE}/research-directions`);
    return response.data;
  }
};
