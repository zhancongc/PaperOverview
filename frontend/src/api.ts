import axios from 'axios';
import type {
  GenerateResponse,
  RecordsResponse,
  ReviewRecord,
  ThreeCirclesResponse,
  ClassifyTopicResponse,
  SmartAnalyzeResponse
} from './types';

const API_BASE = '/api';

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

  // 健康检查
  async checkHealth(): Promise<{ status: string; deepseek_configured: boolean }> {
    const response = await axios.get(`${API_BASE}/health`);
    return response.data;
  }
};
