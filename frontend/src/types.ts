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
  };
}

export interface RecordsResponse {
  success: boolean;
  count: number;
  records: ReviewRecord[];
}
