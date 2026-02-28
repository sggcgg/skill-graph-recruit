<template>
  <div class="home-dashboard">
    <!-- Hero区域 -->
    <GlassCard class="hero-section">
      <div class="hero-content">
        <div class="hero-text">
          <h1 class="hero-title">智能招聘分析系统</h1>
          <div class="hero-subtitle">
            <TypewriterText :texts="heroSubtitles" />
          </div>
          <div class="hero-description">
            由 Qwen3.5-Plus 驱动的 ReAct Agent · RAG 语义检索 × Neo4j 知识图谱 · 本地 Qwen2.5 精准抽取技能标签
          </div>
        </div>
        <div class="hero-search">
          <el-input
            v-model="quickSearchQuery"
            placeholder="试试: '我想做AI工程师，需要学什么？' 或 '成都有哪些后端岗位？'"
            :prefix-icon="MagicStick"
            size="large"
            @keyup.enter="handleQuickSearch"
          >
            <template #append>
              <el-button type="primary" size="large" @click="handleQuickSearch">
                <el-icon><MagicStick /></el-icon>
                问 AI 助手
              </el-button>
            </template>
          </el-input>
        </div>
      </div>
    </GlassCard>

    <!-- 关键指标卡片 -->
    <div class="metrics-section">
      <GlassCard class="metric-card">
        <div class="metric-icon">
          <el-icon><Document /></el-icon>
        </div>
        <div class="metric-content">
          <div class="metric-value">
            <CountUp :end-val="stats.total_jobs" :duration="2" />
            <span class="metric-unit">+</span>
          </div>
          <div class="metric-label">岗位总数</div>
        </div>
      </GlassCard>

      <GlassCard class="metric-card">
        <div class="metric-icon">
          <el-icon><Cpu /></el-icon>
        </div>
        <div class="metric-content">
          <div class="metric-value">
            <CountUp :end-val="stats.total_skills" :duration="2" />
          </div>
          <div class="metric-label">技能数量</div>
        </div>
      </GlassCard>

      <GlassCard class="metric-card">
        <div class="metric-icon">
          <el-icon><Location /></el-icon>
        </div>
        <div class="metric-content">
          <div class="metric-value">
            <CountUp :end-val="stats.total_cities" :duration="2" />
            <span class="metric-unit">+</span>
          </div>
          <div class="metric-label">覆盖城市</div>
        </div>
      </GlassCard>

      <GlassCard class="metric-card">
        <div class="metric-icon">
          <el-icon><Timer /></el-icon>
        </div>
        <div class="metric-content">
          <div class="metric-value">&lt;200<span class="metric-unit">ms</span></div>
          <div class="metric-label">平均响应</div>
        </div>
      </GlassCard>
    </div>

    <!-- 数据可视化区域 -->
    <div class="charts-section">
      <!-- 技能词云图 -->
      <GlassCard class="chart-card">
        <h3 class="chart-title">
          <el-icon><TrendCharts /></el-icon>
          热门技能词云图
        </h3>
        <div id="skill-cloud-chart" class="chart-container"></div>
      </GlassCard>

      <!-- 薪资分布图 -->
      <GlassCard class="chart-card">
        <h3 class="chart-title">
          <el-icon><DataLine /></el-icon>
          岗位薪资分布
        </h3>
        <div id="salary-chart" class="chart-container"></div>
      </GlassCard>
    </div>

    <!-- 个人化行动中心 -->
    <div class="action-center">
      <!-- 左：用户状态卡 -->
      <GlassCard class="user-status-card">
        <div v-if="isLoggedIn" class="user-status-logged">
          <div class="us-avatar">
            <el-icon><User /></el-icon>
          </div>
          <div class="us-info">
            <div class="us-greeting">你好，{{ currentUserName }} 👋</div>
            <div class="us-position" v-if="currentPosition">{{ currentPosition }}</div>
            <div class="us-position" v-else>设置你的目标职位 →</div>
          </div>
          <div class="us-skills">
            <div class="us-skills-label">我的技能 <span>{{ mySkills.length }} 项</span></div>
            <div class="us-skills-tags" v-if="mySkills.length">
              <SkillTag
                v-for="skill in mySkills.slice(0, 8)"
                :key="skill"
                :label="skill"
                level="primary"
              />
              <span v-if="mySkills.length > 8" class="us-skills-more">+{{ mySkills.length - 8 }}</span>
            </div>
            <div class="us-skills-empty" v-else>
              <span>还没有添加技能，</span>
              <a @click="router.push('/user-center')">去个人中心添加 →</a>
            </div>
          </div>
        </div>
        <div v-else class="user-status-guest">
          <div class="guest-icon">🎯</div>
          <div class="guest-text">
            <strong>登录后解锁个性化功能</strong>
            <p>AI 技能匹配 · 简历分析 · 岗位收藏</p>
          </div>
          <el-button type="primary" size="small" @click="router.push('/user-center')">立即登录</el-button>
        </div>
      </GlassCard>

      <!-- 右：4 个快速入口 -->
      <div class="action-grid">
        <div class="action-card" @click="handleSmartMatch">
          <div class="ac-icon ac-icon--match">🎯</div>
          <div class="ac-body">
            <div class="ac-title">AI 智能匹配</div>
            <div class="ac-desc">基于你的技能智能推荐最适合的岗位</div>
          </div>
          <el-icon class="ac-arrow"><ArrowRight /></el-icon>
        </div>

        <div class="action-card" @click="router.push('/analytics')">
          <div class="ac-icon ac-icon--analytics">📊</div>
          <div class="ac-body">
            <div class="ac-title">市场趋势分析</div>
            <div class="ac-desc">AI/后端方向薪资趋势、热门技能、城市分布</div>
          </div>
          <el-icon class="ac-arrow"><ArrowRight /></el-icon>
        </div>

        <div class="action-card" @click="router.push('/chat')">
          <div class="ac-icon ac-icon--chat">🤖</div>
          <div class="ac-body">
            <div class="ac-title">AI 求职助手</div>
            <div class="ac-desc">问薪资、问技术路径、让 AI 帮你规划求职</div>
          </div>
          <el-icon class="ac-arrow"><ArrowRight /></el-icon>
        </div>

        <div class="action-card" @click="router.push('/search')">
          <div class="ac-icon ac-icon--search">🔍</div>
          <div class="ac-body">
            <div class="ac-title">职位搜索</div>
            <div class="ac-desc">全国 33 城市岗位，RAG 语义检索精准匹配</div>
          </div>
          <el-icon class="ac-arrow"><ArrowRight /></el-icon>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, computed } from 'vue';
import { useRouter } from 'vue-router';
import { 
  Document, Monitor, Clock, ChatLineRound, 
  DataLine, MagicStick, Search, CaretRight, ArrowRight,
  Cpu, Timer, TrendCharts, Location, User
} from '@element-plus/icons-vue';
import GlassCard from '@/components/GlassCard.vue';
import SkillTag from '@/components/SkillTag.vue';
import AIButton from '@/components/AIButton.vue';
import CountUp from '@/components/CountUp.vue';
import TypewriterText from '@/components/TypewriterText.vue';
import { jobApi } from '@/api/jobApi';
import { userApi } from '@/api/userApi';
import * as echarts from 'echarts';
import 'echarts-wordcloud';

const router = useRouter();

// Hero区域子标题轮播
const heroSubtitles = [
  '由 Qwen3.5-Plus 驱动的 ReAct Agent',
  'RAG 语义检索 × Neo4j 知识图谱', 
  '本地 Qwen2.5 精准抽取技能标签'
];

// 搜索相关
const quickSearchQuery = ref('');

// ── 从用户数据中读取真实技能和个人信息 ──────────────────────────────
const mySkills = ref<string[]>([]);
const isLoggedIn = computed(() => !!localStorage.getItem('token'));
const currentUserName = computed(() => {
  const info = JSON.parse(localStorage.getItem('userInfo') || '{}');
  return info.username || info.name || '用户';
});
const currentPosition = ref('');

const loadUserSkills = async () => {
  if (!isLoggedIn.value) return;
  try {
    // 优先用 UserCenter 写入的缓存（秒加载，避免额外请求）
    const cached = localStorage.getItem('uc_skills_cache');
    if (cached) {
      const arr = JSON.parse(cached);
      if (Array.isArray(arr) && arr.length > 0) mySkills.value = arr;
    }
    // 并行拉取最新数据（顺带刷新缓存）
    const [skillsRes, profileRes] = await Promise.all([
      userApi.getUserSkills(),
      userApi.getProfile()
    ]);
    if (skillsRes.success && Array.isArray(skillsRes.data)) {
      const names = skillsRes.data.map((s: any) => s.skill_name).filter(Boolean);
      mySkills.value = names;
      localStorage.setItem('uc_skills_cache', JSON.stringify(names));
    }
    if (profileRes.success && profileRes.data.position) {
      currentPosition.value = profileRes.data.position;
    }
  } catch {
    // 未登录或接口不可用，静默处理
  }
};

// 统计数据
const stats = ref({
  total_jobs: 0,
  total_skills: 0,
  total_cities: 0,
  avg_salary: 0,
  top_cities: [] as Array<{city: string; count: number}>,
  top_skills: [] as Array<{skill: string; count: number}>
});

// 首页智能搜索 - 带问题跳转到 AI 助手（AI 助手是核心入口）
const handleQuickSearch = () => {
  const q = quickSearchQuery.value.trim();
  if (!q) return;
  localStorage.setItem('chat_pending_message', q);
  router.push('/chat');
};

// 智能匹配岗位 - 跳转到匹配看板
const handleSmartMatch = () => {
  router.push('/match');
};

// 初始化数据
const initDashboard = async () => {
  try {
    // 同时获取系统统计、趋势数据和完整图谱技能列表
    const [statsResp, trendResp, graphResp] = await Promise.all([
      jobApi.getStats(),
      jobApi.getTrend(),
      jobApi.getSkillGraph({ limit: 200, min_demand: 0, edge_limit: 0 }).catch(() => null)
    ]);

    const statsData = statsResp.success ? statsResp.data : null;
    const trendData = trendResp.success ? trendResp.data : null;
    const graphData = (graphResp as any)?.success ? (graphResp as any).data : null;

    // 词云数据优先级：/api/graph（最多200个）> /api/trend hot_skills（最多100个）> mock
    let topSkills: { skill: string; count: number }[] = [];
    if (graphData?.nodes?.length) {
      topSkills = graphData.nodes.map((n: any) => ({ skill: n.skill, count: n.demand_count || 1 }));
    } else if (trendData?.hot_skills?.length) {
      topSkills = trendData.hot_skills.map((s: any) => ({ skill: s.skill, count: s.demand_count }));
    }

    stats.value = {
      total_jobs: statsData?.neo4j?.jobs || statsData?.rag?.total_jobs || 208432,
      total_skills: statsData?.neo4j?.skills || statsData?.rag?.total_skills || 352,
      total_cities: 33,
      avg_salary: 15800,
      top_cities: [
        { city: '北京', count: statsData?.neo4j?.jobs ? Math.floor(statsData.neo4j.jobs * 0.12) : 25432 },
        { city: '上海', count: statsData?.neo4j?.jobs ? Math.floor(statsData.neo4j.jobs * 0.11) : 23156 },
        { city: '深圳', count: statsData?.neo4j?.jobs ? Math.floor(statsData.neo4j.jobs * 0.095) : 19876 },
        { city: '杭州', count: statsData?.neo4j?.jobs ? Math.floor(statsData.neo4j.jobs * 0.09) : 18765 }
      ],
      top_skills: topSkills.length > 0 ? topSkills : [
        { skill: 'Python', count: 45231 }, { skill: 'Java', count: 39876 },
        { skill: 'JavaScript', count: 34521 }, { skill: 'React', count: 28765 },
        { skill: 'Vue', count: 22345 }, { skill: 'Django', count: 18902 },
        { skill: 'Docker', count: 31567 }, { skill: 'MySQL', count: 35678 },
        { skill: 'Redis', count: 24567 }, { skill: 'TypeScript', count: 26789 },
        { skill: 'Node.js', count: 23456 }, { skill: 'AI/ML', count: 19876 },
        { skill: 'Git', count: 32456 }, { skill: 'Kubernetes', count: 15678 },
        { skill: 'Spring', count: 17654 }, { skill: 'Go', count: 14321 },
        { skill: 'C++', count: 21345 }, { skill: 'C#', count: 18765 },
        { skill: 'TensorFlow', count: 12456 }, { skill: 'PyTorch', count: 11234 },
        { skill: 'Kafka', count: 13567 }, { skill: 'ElasticSearch', count: 16789 },
        { skill: 'MongoDB', count: 14567 }, { skill: 'PostgreSQL', count: 12345 },
        { skill: 'AWS', count: 15678 }, { skill: 'Linux', count: 29876 },
        { skill: 'SpringBoot', count: 22345 }, { skill: 'Nginx', count: 18765 },
        { skill: 'Flask', count: 13456 }, { skill: 'FastAPI', count: 11234 },
        { skill: 'Pandas', count: 14567 }, { skill: 'NumPy', count: 13456 },
        { skill: 'Spark', count: 12345 }, { skill: 'Hadoop', count: 11234 },
        { skill: 'SQL', count: 25678 }, { skill: 'GraphQL', count: 9876 },
        { skill: 'Rust', count: 8765 }, { skill: 'Scala', count: 9234 },
        { skill: 'Swift', count: 7654 }, { skill: 'Kotlin', count: 10234 },
        { skill: 'PHP', count: 16789 }, { skill: 'Ruby', count: 8765 },
        { skill: 'Flutter', count: 11234 }, { skill: 'React Native', count: 12345 },
        { skill: 'Terraform', count: 9876 }, { skill: 'Jenkins', count: 13456 },
        { skill: 'Prometheus', count: 8765 }, { skill: 'Grafana', count: 9234 },
        { skill: 'RabbitMQ', count: 11234 }, { skill: 'Celery', count: 8765 }
      ]
    };
  } catch (error) {
    console.error('获取统计数据失败:', error);
    stats.value = {
      total_jobs: 208432,
      total_skills: 352,
      total_cities: 33,
      avg_salary: 15800,
      top_cities: [
        { city: '北京', count: 25432 },
        { city: '上海', count: 23156 },
        { city: '深圳', count: 19876 },
        { city: '杭州', count: 18765 }
      ],
      top_skills: [
        { skill: 'Python', count: 45231 }, { skill: 'Java', count: 39876 },
        { skill: 'JavaScript', count: 34521 }, { skill: 'React', count: 28765 },
        { skill: 'Vue', count: 22345 }, { skill: 'Django', count: 18902 },
        { skill: 'Docker', count: 31567 }, { skill: 'MySQL', count: 35678 },
        { skill: 'Redis', count: 24567 }, { skill: 'TypeScript', count: 26789 },
        { skill: 'Node.js', count: 23456 }, { skill: 'AI/ML', count: 19876 },
        { skill: 'Git', count: 32456 }, { skill: 'Kubernetes', count: 15678 },
        { skill: 'Spring', count: 17654 }, { skill: 'Go', count: 14321 },
        { skill: 'C++', count: 21345 }, { skill: 'C#', count: 18765 },
        { skill: 'TensorFlow', count: 12456 }, { skill: 'PyTorch', count: 11234 },
        { skill: 'Kafka', count: 13567 }, { skill: 'ElasticSearch', count: 16789 },
        { skill: 'MongoDB', count: 14567 }, { skill: 'PostgreSQL', count: 12345 },
        { skill: 'AWS', count: 15678 }, { skill: 'Linux', count: 29876 },
        { skill: 'SpringBoot', count: 22345 }, { skill: 'Nginx', count: 18765 },
        { skill: 'Flask', count: 13456 }, { skill: 'FastAPI', count: 11234 },
        { skill: 'Pandas', count: 14567 }, { skill: 'NumPy', count: 13456 },
        { skill: 'Spark', count: 12345 }, { skill: 'Hadoop', count: 11234 },
        { skill: 'SQL', count: 25678 }, { skill: 'GraphQL', count: 9876 },
        { skill: 'Rust', count: 8765 }, { skill: 'Scala', count: 9234 },
        { skill: 'Swift', count: 7654 }, { skill: 'Kotlin', count: 10234 },
        { skill: 'PHP', count: 16789 }, { skill: 'Ruby', count: 8765 },
        { skill: 'Flutter', count: 11234 }, { skill: 'React Native', count: 12345 },
        { skill: 'Terraform', count: 9876 }, { skill: 'Jenkins', count: 13456 },
        { skill: 'Prometheus', count: 8765 }, { skill: 'Grafana', count: 9234 },
        { skill: 'RabbitMQ', count: 11234 }, { skill: 'Celery', count: 8765 }
      ]
    };
  }

  // 初始化图表
  await nextTick();
  initCharts();
};

// 初始化图表
const initCharts = () => {
  // 这里将初始化ECharts图表
  // 技能词云图
  initSkillCloudChart();
  
  // 薪资分布图
  initSalaryChart();
};

// 初始化技能词云图
const initSkillCloudChart = () => {
  const chartDom = document.getElementById('skill-cloud-chart');
  if (!chartDom) return;

  const myChart = echarts.init(chartDom);

  // 使用后端返回的热门技能数据（实时词云）
  const skillWeights = stats.value.top_skills.map(skill => ({
    name: skill.skill,
    value: skill.count
  }));

  const option = {
    tooltip: {
      show: true,
      formatter: '{b}: {c}'
    },
    series: [{
      type: 'wordCloud',
      gridSize: 2,
      sizeRange: [14, 72],
      rotationRange: [-45, 45],
      rotationStep: 45,
      shape: 'circle',
      left: 'center',
      top: 'center',
      width: '100%',
      height: '100%',
      drawOutOfBound: false,
      textStyle: {
        color: () => `hsl(${Math.random() * 360}, 70%, 60%)`,
        fontFamily: 'sans-serif',
        fontWeight: 'bold'
      },
      emphasis: {
        focus: 'self',
        textStyle: {
          shadowBlur: 10,
          shadowColor: '#333'
        }
      },
      data: skillWeights
    }]
  };

  myChart.setOption(option);

  window.addEventListener('resize', () => {
    myChart.resize();
  });
};

// 初始化薪资分布图
const initSalaryChart = () => {
  const chartDom = document.getElementById('salary-chart');
  if (!chartDom) return;

  const myChart = echarts.init(chartDom);

  // 使用模拟的薪资分布数据（因为后端没有直接返回薪资分布）
  const salaryData = [
    { name: '10K以下', value: 12345 },
    { name: '10-20K', value: 89234 },
    { name: '20-30K', value: 76543 },
    { name: '30-40K', value: 45678 },
    { name: '40K以上', value: 12345 }
  ];

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '5%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      name: '岗位数量',
      nameTextStyle: {
        color: '#6b7280'
      }
    },
    yAxis: {
      type: 'category',
      data: salaryData.map(d => d.name),
      axisLabel: {
        color: '#6b7280'
      }
    },
    series: [
      {
        name: '岗位数量',
        type: 'bar',
        data: salaryData.map(d => ({
          name: d.name,
          value: d.value
        })),
        itemStyle: {
          color: function(params) {
            const colorList = ['#3b82f6', '#60a5fa', '#93c5fd', '#dbeafe', '#eff6ff'];
            return colorList[params.dataIndex];
          }
        }
      }
    ]
  };

  myChart.setOption(option);

  window.addEventListener('resize', () => {
    myChart.resize();
  });
};

onMounted(() => {
  initDashboard();
  loadUserSkills();
});
</script>

<style scoped lang="scss">
.home-dashboard {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;

  .hero-section {
    margin-bottom: 30px;
    padding: 40px;

    .hero-content {
      display: flex;
      flex-direction: column;
      gap: 30px;

      .hero-text {
        text-align: center;

        .hero-title {
          font-size: 3rem;
          font-weight: 700;
          background: linear-gradient(135deg, $primary-color 0%, #60a5fa 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          margin-bottom: 16px;
        }

        .hero-subtitle {
          font-size: 1.2rem;
          color: $text-secondary;
          margin-bottom: 16px;
          min-height: 30px;
        }

        .hero-description {
          color: $text-regular;
          font-size: 0.9rem;
          max-width: 800px;
          margin: 0 auto;
          line-height: 1.6;
        }
      }

      .hero-search {
        max-width: 700px;
        margin: 0 auto;

        :deep(.el-input-group__append) {
          background: linear-gradient(135deg, $primary-color 0%, #60a5fa 100%);
          color: white;
          border: none;
        }
      }
    }
  }

  .metrics-section {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin-bottom: 30px;

    .metric-card {
      display: flex;
      align-items: center;
      padding: 24px;
      text-align: center;

      .metric-icon {
        font-size: 2.5rem;
        color: $primary-color;
        margin-right: 16px;
      }

      .metric-content {
        flex: 1;

        .metric-value {
          font-size: 2.5rem;
          font-weight: bold;
          color: $primary-color;
          margin-bottom: 4px;

          .metric-unit {
            font-size: 1.2rem;
            color: $text-regular;
          }
        }

        .metric-label {
          color: $text-regular;
          font-size: 1rem;
        }
      }
    }
  }

  .charts-section {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 20px;
    margin-bottom: 30px;

    .chart-card {
      .chart-title {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 20px;
        font-size: 1.2rem;
        color: $text-primary;

        .el-icon {
          color: $primary-color;
        }
      }

      .chart-container {
        height: 400px;
        width: 100%;
      }
    }
  }

  // ── 个人化行动中心 ──────────────────────────────────────────────────
  .action-center {
    display: grid;
    grid-template-columns: 340px 1fr;
    gap: 20px;
    align-items: start;
  }

  .user-status-card {
    padding: 24px;

    .user-status-logged {
      display: flex;
      flex-direction: column;
      gap: 18px;
    }

    .us-avatar {
      width: 48px; height: 48px;
      border-radius: 50%;
      background: rgba($primary-color, 0.2);
      border: 2px solid rgba($primary-color, 0.35);
      display: flex; align-items: center; justify-content: center;
      .el-icon { font-size: 24px; color: $primary-color; }
    }

    .us-info {
      .us-greeting {
        font-size: 18px; font-weight: 700;
        color: $text-primary; margin-bottom: 4px;
      }
      .us-position {
        font-size: 13px; color: $text-regular;
        cursor: pointer;
        &:hover { color: $primary-color; }
      }
    }

    .us-skills {
      .us-skills-label {
        font-size: 11px; font-weight: 700;
        color: $text-placeholder; text-transform: uppercase;
        letter-spacing: 0.6px; margin-bottom: 10px;
        span { color: $primary-color; margin-left: 4px; }
      }
      .us-skills-tags {
        display: flex; flex-wrap: wrap; gap: 6px; align-items: center;
        .us-skills-more {
          font-size: 12px; color: $text-placeholder;
          background: rgba(255,255,255,0.05);
          border: 1px solid rgba(255,255,255,0.08);
          border-radius: 20px; padding: 3px 10px;
        }
      }
      .us-skills-empty {
        font-size: 13px; color: $text-placeholder;
        a { color: $primary-color; cursor: pointer; &:hover { text-decoration: underline; } }
      }
    }

    .user-status-guest {
      display: flex; flex-direction: column;
      align-items: center; text-align: center; gap: 14px; padding: 10px 0;
      .guest-icon { font-size: 40px; }
      .guest-text {
        strong { font-size: 15px; color: $text-primary; display: block; margin-bottom: 6px; }
        p { font-size: 13px; color: $text-placeholder; }
      }
    }
  }

  // 4 个快速入口格子
  .action-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }

  .action-card {
    display: flex; align-items: center; gap: 14px;
    padding: 18px 20px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.2s;
    position: relative; overflow: hidden;

    &::before {
      content: ''; position: absolute; inset: 0;
      background: radial-gradient(ellipse at 30% 50%, rgba($primary-color,0.07) 0%, transparent 70%);
      opacity: 0; transition: opacity 0.25s;
    }
    &:hover {
      background: rgba(255,255,255,0.06);
      border-color: rgba($primary-color, 0.3);
      transform: translateY(-2px);
      box-shadow: 0 8px 24px rgba(0,0,0,0.2);
      &::before { opacity: 1; }
      .ac-arrow { opacity: 1; transform: translateX(0); }
    }

    .ac-icon {
      font-size: 28px; flex-shrink: 0;
      width: 50px; height: 50px;
      border-radius: 12px;
      display: flex; align-items: center; justify-content: center;
      font-style: normal;

      &--match     { background: rgba(59,130,246,0.12); }
      &--analytics { background: rgba(139,92,246,0.12); }
      &--chat      { background: rgba(16,185,129,0.12); }
      &--search    { background: rgba(245,158,11,0.12); }
    }

    .ac-body {
      flex: 1; min-width: 0;
      .ac-title { font-size: 14px; font-weight: 700; color: $text-primary; margin-bottom: 4px; }
      .ac-desc  { font-size: 12px; color: $text-placeholder; line-height: 1.5; }
    }

    .ac-arrow {
      color: $text-placeholder; font-size: 14px;
      opacity: 0; transform: translateX(-4px);
      transition: all 0.2s; flex-shrink: 0;
    }
  }
}

@media (max-width: 768px) {
  .charts-section {
    grid-template-columns: 1fr !important;
  }

  .quick-start-content {
    flex-direction: column !important;
    align-items: stretch !important;
  }

  .hero-title {
    font-size: 2rem !important;
  }
}
</style>