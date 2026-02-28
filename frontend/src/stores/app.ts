// stores/app.ts
import { defineStore } from 'pinia';
import { jobApi } from '@/api/jobApi';

export const useAppStore = defineStore('app', {
  state: () => ({
    userInfo: null as any,
    token: null as string | null,
    systemStats: {
      totalJobs: 0,
      totalSkills: 0,
      totalCities: 0,
      avgResponseTime: 0
    },
    loading: false,
    theme: 'dark' as 'dark' | 'light',
    // 全局技能列表缓存，避免重复请求
    skillsList: [] as string[],
    skillsLoaded: false,
  }),

  getters: {
    isLoggedIn: (state) => !!state.token,
    userName: (state) => state.userInfo?.username || state.userInfo?.name || '用户',
    userId: (state) => state.userInfo?.id || null,
    getSystemStats: (state) => state.systemStats,
    isLoading: (state) => state.loading
  },

  actions: {
    setLoading(status: boolean) {
      this.loading = status;
    },

    setSystemStats(stats: { totalJobs?: number; totalSkills?: number; totalCities?: number; avgResponseTime?: number }) {
      this.systemStats = { ...this.systemStats, ...stats };
    },

    setTheme(theme: 'dark' | 'light') {
      this.theme = theme;
    },

    login(token: string, user: any) {
      this.token = token;
      this.userInfo = user;
      localStorage.setItem('token', token);
      localStorage.setItem('userInfo', JSON.stringify(user));
    },

    logout() {
      this.token = null;
      this.userInfo = null;
      localStorage.removeItem('token');
      localStorage.removeItem('userInfo');
    },

    // 预加载技能列表（全局只请求一次）
    async preloadSkills() {
      if (this.skillsLoaded) return;
      try {
        const res = await jobApi.getSkillGraph({ limit: 500, min_demand: 0, edge_limit: 0 });
        if (res.data?.nodes?.length) {
          const names: string[] = res.data.nodes
            .map((n: any) => n.name || n.skill || n.id || '')
            .filter(Boolean)
            .sort();
          this.skillsList = [...new Set(names)] as string[];
          this.skillsLoaded = true;
        }
      } catch {
        // 静默失败，组件会使用兜底数据
      }
    },

    // 从localStorage恢复登录状态
    restoreAuth() {
      const token = localStorage.getItem('token');
      const userInfo = localStorage.getItem('userInfo');
      if (token) {
        this.token = token;
        this.userInfo = userInfo ? JSON.parse(userInfo) : null;
      }
    }
  }
});
