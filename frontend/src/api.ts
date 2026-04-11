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

// API 基础地址配置
// 开发环境：使用本地代理
// 生产环境：指向上海服务器（统一后端）
const getApiBase = () => {
  if (import.meta.env.DEV) {
    return '/api';  // 开发环境使用 Vite 代理
  }

  // 生产环境：根据部署位置判断
  // 如果部署在纽约服务器（plainkit.top），则指向上海服务器
  // 如果部署在上海服务器（snappicker.com），则使用相对路径
  const hostname = window.location.hostname;

  if (hostname.includes('plainkit.top')) {
    // 纽约前端：指向上海后端
    return 'https://autooverview.snappicker.com/api';
  }

  // 上海前端：使用相对路径（同服务器）
  return '/api';
};

const API_BASE = getApiBase();

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
      language?: string;
      targetCount?: number;
      recentYearsRatio?: number;
      englishRatio?: number;
      searchYears?: number;
      maxSearchQueries?: number;
    } = {}
  ): Promise<TaskSubmitResponse> {
    const token = localStorage.getItem('auth_token');
    const headers: Record<string, string> = {};
    if (token) headers.Authorization = `Bearer ${token}`;
    const response = await axios.post(`${API_BASE}/smart-generate`, {
      topic,
      research_direction_id: options.researchDirectionId ?? '',
      language: options.language ?? 'zh',
      target_count: options.targetCount ?? 50,
      recent_years_ratio: options.recentYearsRatio ?? 0.5,
      english_ratio: options.englishRatio ?? 0.3,
      search_years: options.searchYears ?? 10,
      max_search_queries: options.maxSearchQueries ?? 8
    }, { headers });
    return response.data;
  },

  // 查找文献（不生成综述）
  async searchPapersOnly(
    topic: string,
    options: {
      targetCount?: number;
      searchYears?: number;
    } = {}
  ): Promise<{ success: boolean; message: string; data: any }> {
    const response = await axios.post(`${API_BASE}/search-papers-only`, {
      topic,
      target_count: options.targetCount ?? 50,
      search_years: options.searchYears ?? 10
    });
    return response.data;
  },

  // 获取任务状态
  async getTaskStatus(taskId: string): Promise<{ success: boolean; data: TaskInfo }> {
    const token = localStorage.getItem('auth_token');
    const headers: Record<string, string> = {};
    if (token) headers.Authorization = `Bearer ${token}`;
    const response = await axios.get(`${API_BASE}/tasks/${taskId}`, { headers });
    return response.data;
  },

  // 通过 task_id 获取综述结果
  async getTaskReview(taskId: string, format: string = 'ieee'): Promise<{ success: boolean; data: {
    task_id: string;
    topic: string;
    review: string;
    papers: any[];
    cited_papers_count: number;
    created_at: string;
    statistics: any;
    record_id?: number;
    is_public: boolean;
    is_paid: boolean;
  } }> {
    const token = localStorage.getItem('auth_token');
    const headers: Record<string, string> = {};
    if (token) headers.Authorization = `Bearer ${token}`;
    const response = await axios.get(`${API_BASE}/tasks/${taskId}/review`, {
      headers,
      params: { format }
    });
    return response.data;
  },

  // 通过 record_id 获取综述结果（支持引用格式切换）
  async getRecordReview(recordId: number, format: string = 'ieee'): Promise<{ success: boolean; data: {
    task_id: string | null;
    topic: string;
    review: string;
    papers: any[];
    cited_papers_count: number;
    created_at: string;
    statistics: any;
    record_id: number;
    is_public: boolean;
    is_paid: boolean;
  } }> {
    const token = localStorage.getItem('auth_token');
    const headers: Record<string, string> = {};
    if (token) headers.Authorization = `Bearer ${token}`;
    const response = await axios.get(`${API_BASE}/records/${recordId}/review`, {
      headers,
      params: { format }
    });
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
    const token = localStorage.getItem('auth_token');
    const headers: Record<string, string> = {};
    if (token) headers.Authorization = `Bearer ${token}`;
    const response = await axios.get(`${API_BASE}/records`, {
      params: { skip, limit },
      headers
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
    const token = localStorage.getItem('auth_token');
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers.Authorization = `Bearer ${token}`;

    const response = await axios.post(`${API_BASE}/records/export`, {
      record_id: recordId
    }, {
      responseType: 'blob',
      headers
    });
    return response.data;
  },

  // 单次解锁综述（29.8元）
  async unlockRecord(recordId: number): Promise<{ success: boolean; message: string; order_no?: string; pay_url?: string; already_unlocked?: boolean }> {
    const token = localStorage.getItem('auth_token');
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers.Authorization = `Bearer ${token}`;

    const response = await axios.post(`${API_BASE}/records/unlock`, {
      record_id: recordId
    }, {
      headers
    });
    return response.data;
  },

  // 使用额度解锁综述（扣除1个付费额度）
  async unlockRecordWithCredit(recordId: number): Promise<{ success: boolean; message: string }> {
    const token = localStorage.getItem('auth_token');
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers.Authorization = `Bearer ${token}`;

    const response = await axios.post(`${API_BASE}/records/unlock-with-credit`, {
      record_id: recordId
    }, {
      headers
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
  },

  // ==================== 订阅/支付 API ====================

  async getSubscriptionPlans(): Promise<{ plans: Array<{
    type: string;
    name: string;
    price: number;
    duration_days: number;
    recommended?: boolean;
    features: string[];
  }> }> {
    const response = await axios.get(`${API_BASE}/subscription/plans`);
    return response.data;
  },

  async createSubscription(planType: string): Promise<{
    order_no: string;
    pay_url: string;
    amount: number;
  }> {
    const token = localStorage.getItem('auth_token');
    const response = await axios.post(`${API_BASE}/subscription/create`, {
      plan_type: planType
    }, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  },

  async querySubscription(orderNo: string): Promise<{
    status: string;
    payment_time?: string;
    expires_at?: string;
  }> {
    const token = localStorage.getItem('auth_token');
    const response = await axios.get(`${API_BASE}/subscription/query/${orderNo}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  },

  async getMembershipInfo(): Promise<{
    membership_type: string;
    expires_at?: string;
    days_remaining?: number;
  }> {
    const token = localStorage.getItem('auth_token');
    const response = await axios.get(`${API_BASE}/subscription/membership`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  },

  async getCredits(): Promise<{ credits: number; free_credits: number; has_purchased: boolean }> {
    const token = localStorage.getItem('auth_token');
    const headers: Record<string, string> = {};
    if (token) headers.Authorization = `Bearer ${token}`;
    const response = await axios.get(`${API_BASE}/usage/credits`, { headers });
    return response.data;
  },

  async checkJadeAccess(): Promise<{ allowed: boolean }> {
    const token = localStorage.getItem('auth_token');
    const headers: Record<string, string> = {};
    if (token) headers.Authorization = `Bearer ${token}`;
    const response = await axios.get(`${API_BASE}/jade/access`, { headers });
    return response.data;
  },

  async getActiveTask(): Promise<{ active: boolean; task_id?: string; topic?: string; status?: string }> {
    const token = localStorage.getItem('auth_token');
    const headers: Record<string, string> = {};
    if (token) headers.Authorization = `Bearer ${token}`;
    const response = await axios.get(`${API_BASE}/tasks/active`, { headers });
    return response.data;
  },

  // ==================== Paddle Payment API (International) ====================

  async getPaddlePlans(): Promise<{ plans: Record<string, {
    name: string;
    price: number;
    credits: number;
    currency: string;
  }> }> {
    const response = await axios.get(`${API_BASE}/paddle/plans`);
    return response.data;
  },

  async createPaddleSubscription(planType: string): Promise<{
    order_no: string;
    checkout_url: string;
    amount: number;
    currency: string;
  }> {
    const token = localStorage.getItem('auth_token');
    const response = await axios.post(`${API_BASE}/paddle/create`, {
      plan_type: planType
    }, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  },

  async queryPaddleSubscription(orderNo: string): Promise<{
    status: string;
    payment_time?: string;
    amount: number;
    currency: string;
  }> {
    const token = localStorage.getItem('auth_token');
    const response = await axios.get(`${API_BASE}/paddle/query/${orderNo}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  },
};
