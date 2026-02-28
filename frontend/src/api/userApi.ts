// api/userApi.ts
import apiClient from './index';

export interface UserProfile {
  id?: string;
  name: string;
  email: string;
  phone: string;
  city: string;
  position: string;
}

export interface UserResume {
  id?: string;
  userId?: string;
  name: string;
  school: string;
  major: string;
  degree: string;
  skills: string[];
  expect_cities?: string[];
  expectCities?: string[];
  expect_salary_min?: number;
  expect_salary_max?: number;
  expectSalary?: number;
  work_experience?: string;
  projects?: string;
}

export interface AddSkillRequest {
  user_id: number;
  skill_name: string;
  proficiency_level: number;
  years_of_experience?: number;
}

export interface UserSkill {
  skill_name: string;
  proficiency_level: number;
  years_of_experience?: number;
  description?: string;
}

export interface AddFavoriteRequest {
  user_id: number;
  job_id: string;
  title: string;
  company: string;
  salary_range?: string;
  city?: string;
  skills?: string[];
}

export interface FavoriteJob {
  id: string;
  userId?: string;
  jobId: string;
  title: string;
  company: string;
  salary_range: string;
  city: string;
  skills: string[];
  createdAt?: string;
}

export interface MatchReport {
  id: string;
  userId?: string;
  title: string;
  date: string;
  summary: string;
  matchRate: number;
}

export interface UserSettings {
  notifications: boolean;
  emailSubscription: boolean;
  theme: 'light' | 'dark' | 'auto';
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  token: string;
  user: {
    id: string;
    username: string;
    email: string;
  };
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

export const userApi = {
  // 用户登录
  login: (credentials: LoginRequest) => {
    return apiClient.post<LoginResponse>('/api/auth/login', credentials);
  },

  // 用户注册
  register: (userData: RegisterRequest) => {
    return apiClient.post<LoginResponse>('/api/auth/register', userData);
  },

  // 获取用户信息
  getProfile: () => {
    return apiClient.get<UserProfile>('/api/user/profile');
  },

  // 更新用户信息
  updateProfile: (profile: UserProfile) => {
    return apiClient.put<UserProfile>('/api/user/profile', profile);
  },

  // 获取用户简历
  getResume: () => {
    return apiClient.get<UserResume>('/api/user/resume');
  },

  // 更新用户简历
  updateResume: (resume: UserResume) => {
    return apiClient.put<UserResume>('/api/user/resume', resume);
  },

  // 获取用户技能列表
  getUserSkills: () => {
    return apiClient.get<any>('/api/user/skills');
  },

  // 添加单个技能（POST，匹配后端API）
  addSkill: (skill: AddSkillRequest) => {
    return apiClient.post<any>('/api/user/skills', skill);
  },

  // 更新单个技能熟练度（PUT，匹配后端API）
  updateSkill: (skillName: string, data: { proficiency_level: number; years_of_experience?: number }) => {
    return apiClient.put<any>(`/api/user/skills/${encodeURIComponent(skillName)}`, data);
  },

  // 删除单个技能
  deleteSkill: (skillName: string) => {
    return apiClient.delete<any>(`/api/user/skills/${encodeURIComponent(skillName)}`);
  },

  // 获取收藏岗位
  getFavorites: () => {
    return apiClient.get<FavoriteJob[]>('/api/user/favorites');
  },

  // 添加收藏岗位（需传递完整job信息）
  addFavorite: (job: AddFavoriteRequest) => {
    return apiClient.post('/api/user/favorites', job);
  },

  // 删除收藏岗位
  removeFavorite: (jobId: string) => {
    return apiClient.delete(`/api/user/favorites/${jobId}`);
  },

  // 获取匹配报告
  getMatchReports: () => {
    return apiClient.get<MatchReport[]>('/api/user/reports');
  },

  // 获取用户设置
  getSettings: () => {
    return apiClient.get<UserSettings>('/api/user/settings');
  },

  // 更新用户设置
  updateSettings: (settings: UserSettings) => {
    return apiClient.put<UserSettings>('/api/user/settings', settings);
  },

  // 刷新令牌
  refreshToken: () => {
    return apiClient.post('/api/auth/refresh');
  },

  // 用户登出
  logout: () => {
    return apiClient.post('/api/auth/logout');
  }
};