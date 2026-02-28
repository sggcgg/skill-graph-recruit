// api/jobApi.ts
import apiClient from './index';
import { aiService } from '@/utils/request';

export interface Job {
  id: string;
  title: string;
  company: string;
  city: string;
  salary_min: number;
  salary_max: number;
  salary_range: string;
  experience: string;
  education: string;
  skills: string[];
  document: string;
  similarity?: number;
  match_count?: number;
  total_skills?: number;
  source?: string;
  date_posted?: string;
}

export interface RagSearchRequest {
  query: string;
  top_k?: number;
  city?: string;
}

export interface RagSearchResponse {
  count: number;
  retrieved_jobs: Job[];
  summary?: string;
}

export interface SkillGapRequest {
  user_skills: string[];
  target_position: string;
  city?: string;
}

export interface SkillGapResponse {
  user_skills: string[];
  target_position: string;
  target_jobs: Job[];
  analysis: string;
}

export interface JobRecommendRequest {
  user_skills: string[];
  top_k?: number;
}

export interface JobRecommendResponse {
  count: number;
  retrieved_jobs: Job[];
}

export interface ChatMessage {
  message: string;
  session_id: string;
}

export interface ChatResponse {
  success: boolean;
  data: {
    response: string;
    session_id: string;
    rag_trace?: any;
    agent_steps?: any;
  };
}

export interface StatsResponse {
  success: boolean;
  data: {
    rag?: {
      total_jobs?: number;
      total_skills?: number;
    };
    neo4j?: {
      jobs?: number;
      skills?: number;
      total_nodes?: number;
      total_relationships?: number;
    };
  };
}

export interface GraphSearchRequest {
  query: string;
  top_k?: number;
  city?: string;
}

export interface GraphSearchResponse {
  success: boolean;
  data: {
    jobs: Array<{
      job_id: string;
      title: string;
      city: string;
      company: string;
      salary_range: string;
      matched_skills: string[];
      match_count: number;
      source: 'graph' | 'vector';
    }>;
    count: number;
    query: string;
    matched_skills: string[];
    graph_hits: number;
    vector_hits: number;
  };
}

export interface GraphRecommendRequest {
  user_skills: string[];
  top_k?: number;
  city?: string;
}

export interface GraphRecommendResponse {
  success: boolean;
  data: {
    jobs: Array<{
      job_id: string;
      title: string;
      city?: string;
      company?: string;
      salary_range: string;
      matched_skills: string[];
      match_count: number;
      match_type: 'precise' | 'expanded';
    }>;
    count: number;
    precise_count: number;
    expanded_count: number;
    related_skills: string[];
  };
}

export interface GraphGapAnalysisRequest {
  user_skills: string[];
  target_position: string;
  city?: string;
}

export interface GraphGapAnalysisResponse {
  success: boolean;
  data: {
    target_position: string;
    user_skills: string[];
    required_skills: string[];
    matched_skills: string[];
    missing_skills: string[];
    match_rate: number;
    learning_path: Array<{
      skill: string;
      owned_prerequisites: string[];
      needed_prerequisites: string[];
      ready_to_learn: boolean;
    }>;
    sample_jobs?: Array<{
      title: string;
      city?: string;
      salary_range?: string;
    }>;
  };
}

export interface GraphTrendResponse {
  success: boolean;
  data: {
    hot_skills: Array<{
      skill: string;
      category: string;
      demand_count: number;
      hot_score: number;
    }>;
    category_distribution: Array<{
      category: string;
      skill_count: number;
      total_demand: number;
    }>;
    skill_combos: Array<{
      skill1: string;
      skill2: string;
      co_count: number;
    }>;
    high_salary_skills: Array<{
      skill: string;
      avg_salary_k: number;
      job_count: number;
    }>;
  };
}

export const jobApi = {
  // RAG语义搜索
  searchJobs: (params: RagSearchRequest) => {
    return apiClient.post<RagSearchResponse>('/api/rag/search', params);
  },

  // 技能差距分析
  analyzeSkillGap: (params: SkillGapRequest) => {
    return apiClient.post<SkillGapResponse>('/api/skill/gap-analysis', params);
  },

  // 岗位推荐
  recommendJobs: (params: JobRecommendRequest) => {
    return apiClient.post<JobRecommendResponse>('/api/job/recommend', params);
  },

  // Agent对话
  chat: (params: ChatMessage) => {
    return aiService.post<ChatResponse>('/api/agent/chat', params);
  },

  // 系统统计
  getStats: () => {
    return apiClient.get<StatsResponse>('/api/stats');
  },

  // 健康检查
  healthCheck: () => {
    return apiClient.get('/api/health');
  },

  // 图谱增强搜索（基于Neo4j）
  graphSearch: (params: GraphSearchRequest) => {
    return apiClient.post<GraphSearchResponse>('/api/search', params);
  },

  // 图谱增强推荐（基于Neo4j）
  graphRecommend: (params: GraphRecommendRequest) => {
    return apiClient.post<GraphRecommendResponse>('/api/recommend', params);
  },

  // 图谱增强技能差距分析（基于Neo4j）
  graphGapAnalysis: (params: GraphGapAnalysisRequest) => {
    return apiClient.post<GraphGapAnalysisResponse>('/api/gap-analysis', params);
  },

  // 图谱增强市场趋势（基于Neo4j）
  getTrend: () => {
    return apiClient.get<GraphTrendResponse>('/api/trend');
  },

  getSkillGraph: (params?: { limit?: number; min_demand?: number; edge_limit?: number }) => {
    return apiClient.get<any>('/api/graph', { params });
  }
};