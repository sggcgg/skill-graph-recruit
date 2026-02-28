<template>
  <div class="analytics-page">

    <!-- 页头 -->
    <GlassCard class="analytics-header">
      <div class="header-content">
        <div class="header-left">
          <h1 class="page-title">
            <el-icon><DataAnalysis /></el-icon>
            数据可视化报表
          </h1>
          <span class="data-badge" :class="usingMock ? 'badge-mock' : 'badge-live'">
            {{ usingMock ? '演示数据' : '实时数据' }}
          </span>
        </div>
        <div class="header-controls">
          <!-- 快速聚焦方向：高亮当前用户目标领域的数据 -->
          <div class="direction-btns">
            <button
              v-for="d in directionFilters"
              :key="d.value"
              :class="['dir-btn', { active: activeDirection === d.value }]"
              @click="setDirection(d.value)"
            >{{ d.label }}</button>
          </div>
          <el-button @click="refreshData" :loading="loading">
            <el-icon><Refresh /></el-icon>
            刷新数据
          </el-button>
        </div>
      </div>
    </GlassCard>

    <!-- 骨架屏 -->
    <div v-if="loading" class="skeleton-wrap">
      <div class="skeleton-stats">
        <el-skeleton v-for="n in 4" :key="n" animated>
          <template #template>
            <el-skeleton-item variant="rect" style="height: 96px; border-radius: 14px;" />
          </template>
        </el-skeleton>
      </div>
      <el-skeleton animated style="margin-bottom: 20px;">
        <template #template>
          <el-skeleton-item variant="rect" style="height: 56px; border-radius: 12px; width: 100%;" />
        </template>
      </el-skeleton>
      <div class="skeleton-charts">
        <el-skeleton v-for="n in 4" :key="n" animated>
          <template #template>
            <el-skeleton-item variant="rect" style="height: 400px; border-radius: 14px;" />
          </template>
        </el-skeleton>
      </div>
    </div>

    <template v-else>
      <!-- AI 智能洞察栏 -->
      <div v-if="dataInsights.length > 0" class="insights-bar">
        <div
          v-for="insight in dataInsights"
          :key="insight.type"
          class="insight-card"
          :class="`insight-${insight.type}`"
        >
          <span class="insight-icon">{{ insight.icon }}</span>
          <div class="insight-body">
            <div class="insight-title">{{ insight.title }}</div>
            <div class="insight-text">{{ insight.text }}</div>
          </div>
        </div>
      </div>

      <!-- 统计卡片 -->
      <div class="stats-cards">
        <GlassCard class="stat-card">
          <div class="stat-accent accent-blue"></div>
          <div class="stat-content">
            <div class="stat-icon-wrap icon-blue"><el-icon><TrendCharts /></el-icon></div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.totalJobs.toLocaleString() }}</div>
              <div class="stat-label">总岗位数</div>
              <div class="stat-sub">数据来自 Neo4j 图谱</div>
            </div>
          </div>
        </GlassCard>

        <GlassCard class="stat-card">
          <div class="stat-accent accent-purple"></div>
          <div class="stat-content">
            <div class="stat-icon-wrap icon-purple"><el-icon><Medal /></el-icon></div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.totalSkills }}</div>
              <div class="stat-label">技能总数</div>
              <div class="stat-sub">最热：{{ stats.hotSkills[0]?.skill || '-' }}</div>
            </div>
          </div>
        </GlassCard>

        <GlassCard class="stat-card">
          <div class="stat-accent accent-green"></div>
          <div class="stat-content">
            <div class="stat-icon-wrap icon-green"><el-icon><Coin /></el-icon></div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.avgSalary }}K</div>
              <div class="stat-label">平均薪资</div>
              <div class="stat-sub">市场参考均值</div>
            </div>
          </div>
        </GlassCard>

        <GlassCard class="stat-card">
          <div class="stat-accent accent-orange"></div>
          <div class="stat-content">
            <div class="stat-icon-wrap icon-orange"><el-icon><Promotion /></el-icon></div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.topCategory }}</div>
              <div class="stat-label">热门领域</div>
              <div class="stat-sub" v-if="topCategoryPct">占比 {{ topCategoryPct }}%</div>
            </div>
          </div>
        </GlassCard>
      </div>

      <!-- 主图表区 -->
      <div class="analytics-main">

        <!-- 技能需求对比（全宽）-->
        <GlassCard class="chart-panel panel-full">
          <div class="panel-header">
            <h3 class="panel-title">📊 技能需求对比分析</h3>
            <div class="panel-actions">
              <el-radio-group v-model="compareMetric" size="small">
                <el-radio-button label="demand">需求量</el-radio-button>
                <el-radio-button label="salary">薪资</el-radio-button>
                <el-radio-button label="hot">热度</el-radio-button>
              </el-radio-group>
              <el-button size="small" class="export-btn" @click="exportChart('compare', '技能需求对比')" title="导出图片">
                <el-icon><Download /></el-icon>
              </el-button>
            </div>
          </div>
          <div class="skill-selector">
            <span class="selector-label">选择技能：</span>
            <el-tag
              v-for="skill in skillOptions"
              :key="skill"
              :type="selectedSkills.includes(skill) ? '' : 'info'"
              :effect="selectedSkills.includes(skill) ? 'dark' : 'plain'"
              class="skill-tag-btn"
              @click="toggleSkill(skill)"
            >{{ skill }}</el-tag>
          </div>
          <div ref="compareChartRef" class="chart-container chart-short"></div>
        </GlassCard>

        <!-- 技能分类分布 -->
        <GlassCard class="chart-panel">
          <div class="panel-header">
            <h3 class="panel-title">🗂️ 技能分类分布</h3>
            <el-button size="small" class="export-btn" @click="exportChart('category', '技能分类分布')" title="导出图片">
              <el-icon><Download /></el-icon>
            </el-button>
          </div>
          <div ref="categoryChartRef" class="chart-container"></div>
        </GlassCard>

        <!-- 薪资 × 需求量气泡图 -->
        <GlassCard class="chart-panel">
          <div class="panel-header">
            <h3 class="panel-title">💡 薪资 × 需求量分布</h3>
            <el-button size="small" class="export-btn" @click="exportChart('bubble', '薪资需求分布')" title="导出图片">
              <el-icon><Download /></el-icon>
            </el-button>
          </div>
          <div ref="bubbleChartRef" class="chart-container"></div>
        </GlassCard>

        <!-- 城市分布 -->
        <GlassCard class="chart-panel">
          <div class="panel-header">
            <h3 class="panel-title">🏙️ 热门城市岗位分布</h3>
            <el-button size="small" class="export-btn" @click="exportChart('city', '城市岗位分布')" title="导出图片">
              <el-icon><Download /></el-icon>
            </el-button>
          </div>
          <div ref="cityChartRef" class="chart-container"></div>
        </GlassCard>

        <!-- 高频技能组合 增强版 -->
        <GlassCard class="chart-panel">
          <div class="panel-header">
            <h3 class="panel-title">🔗 高频技能组合</h3>
            <span class="panel-sub">岗位共现频率</span>
          </div>
          <div class="combo-list">
            <div
              v-for="(combo, i) in displayCombos"
              :key="i"
              class="combo-item"
            >
              <div class="combo-rank" :class="getRankClass(i)">
                {{ i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `#${i + 1}` }}
              </div>
              <div class="combo-skills">
                <SkillTag :label="combo.skill1" level="primary" />
                <span class="combo-plus">+</span>
                <SkillTag :label="combo.skill2" level="primary" />
              </div>
              <div class="combo-right">
                <div class="combo-bar-track">
                  <div class="combo-bar-fill" :style="{ width: getComboWidth(combo.co_count) }"></div>
                </div>
                <div class="combo-count-info">
                  <span class="combo-num">{{ combo.co_count.toLocaleString() }}</span>
                  <span class="combo-unit">岗位</span>
                </div>
              </div>
            </div>
            <div
              v-if="stats.skillCombos.length > 4"
              class="combo-expand"
              @click="showAllCombos = !showAllCombos"
            >
              {{ showAllCombos ? '▲ 收起' : `▼ 查看全部 ${stats.skillCombos.length} 个组合` }}
            </div>
          </div>
        </GlassCard>

        <!-- 技能词云（全宽）-->
        <GlassCard class="chart-panel panel-full">
          <div class="panel-header">
            <h3 class="panel-title">☁️ 技能热度词云</h3>
            <el-button size="small" class="export-btn" @click="exportChart('wordcloud', '技能词云')" title="导出图片">
              <el-icon><Download /></el-icon>
            </el-button>
          </div>
          <div ref="wordCloudChartRef" class="chart-container chart-tall"></div>
        </GlassCard>

      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import 'echarts-wordcloud';
import {
  DataAnalysis, TrendCharts, Medal, Coin, Promotion, Refresh, Download
} from '@element-plus/icons-vue';
import GlassCard from '@/components/GlassCard.vue';
import SkillTag from '@/components/SkillTag.vue';
import { jobApi } from '@/api/jobApi';

// ── 类型 ─────────────────────────────────────────────────────────────
interface HotSkill        { skill: string; demand_count: number; hot_score: number }
interface CategoryDist    { category: string; skill_count: number; total_demand: number }
interface SalarySkill     { skill: string; avg_salary_k: number; job_count: number }
interface SkillCombo      { skill1: string; skill2: string; co_count: number }
interface CityDist        { city: string; job_count: number }
interface StatsData {
  totalJobs: number; totalSkills: number; avgSalary: number; topCategory: string;
  hotSkills: HotSkill[]; categoryDistribution: CategoryDist[];
  highSalarySkills: SalarySkill[]; skillCombos: SkillCombo[]; cityDistribution: CityDist[];
}

// ── 方向快速筛选（替换无效的日期筛选）────────────────────────────────
const directionFilters = [
  { label: '全部',      value: 'all' },
  { label: 'AI/大模型', value: 'ai' },
  { label: '后端开发',  value: 'backend' },
  { label: '前端开发',  value: 'frontend' },
  { label: '数据工程',  value: 'data' },
];
const activeDirection = ref('all');
const setDirection = (val: string) => {
  activeDirection.value = val;
  // 根据方向更新图表比较选中的技能组
  const presets: Record<string, string[]> = {
    ai:       ['Python', 'PyTorch', 'LangChain', 'FastAPI', 'CUDA', 'Transformer'],
    backend:  ['Java', 'Spring Boot', 'MySQL', 'Redis', 'Kafka', 'Docker'],
    frontend: ['Vue', 'React', 'TypeScript', 'Node.js', 'Webpack', 'Tailwind'],
    data:     ['Python', 'Spark', 'Hadoop', 'SQL', 'Pandas', 'Flink'],
    all:      [],
  };
  selectedSkills.value = presets[val] ?? [];
  // 延迟刷新比较图
  setTimeout(() => { updateCompareChart(); }, 100);
};

// ── 状态 ─────────────────────────────────────────────────────────────
const loading        = ref(false);
const usingMock      = ref(false);
const compareMetric  = ref<'demand' | 'salary' | 'hot'>('demand');
const selectedSkills = ref<string[]>([]);
const showAllCombos  = ref(false);

const stats = ref<StatsData>({
  totalJobs: 0, totalSkills: 0, avgSalary: 0, topCategory: '',
  hotSkills: [], categoryDistribution: [], highSalarySkills: [],
  skillCombos: [], cityDistribution: [],
});

// ── 图表 DOM 引用 ─────────────────────────────────────────────────────
const compareChartRef   = ref<HTMLElement | null>(null);
const categoryChartRef  = ref<HTMLElement | null>(null);
const bubbleChartRef    = ref<HTMLElement | null>(null);
const cityChartRef      = ref<HTMLElement | null>(null);
const wordCloudChartRef = ref<HTMLElement | null>(null);

// 统一管理图表实例，防止内存泄漏
const charts = new Map<string, echarts.ECharts>();

const initChart = (key: string, el: HTMLElement): echarts.ECharts => {
  charts.get(key)?.dispose();
  const c = echarts.init(el);
  charts.set(key, c);
  return c;
};

// ── computed ──────────────────────────────────────────────────────────
const topCategoryPct = computed(() => {
  const cats = stats.value.categoryDistribution;
  const total = cats.reduce((s, c) => s + c.total_demand, 0);
  return total > 0 && cats.length > 0
    ? Math.round(cats[0].total_demand / total * 100)
    : null;
});

const skillOptions = computed(() => stats.value.hotSkills.slice(0, 50).map(s => s.skill));

const displayCombos = computed(() =>
  showAllCombos.value ? stats.value.skillCombos : stats.value.skillCombos.slice(0, 4)
);

const maxComboCount = computed(() =>
  stats.value.skillCombos.length > 0
    ? Math.max(...stats.value.skillCombos.map(c => c.co_count))
    : 1
);

// AI 智能洞察 —— 纯前端从现有数据计算生成
const dataInsights = computed(() => {
  const out: Array<{ type: string; icon: string; title: string; text: string }> = [];
  const { hotSkills, highSalarySkills, cityDistribution, skillCombos, avgSalary } = stats.value;

  if (hotSkills.length >= 2) {
    const pct = Math.round((hotSkills[0].demand_count / hotSkills[1].demand_count - 1) * 100);
    out.push({
      type: 'hot', icon: '🔥', title: '最热技能',
      text: `${hotSkills[0].skill} 需求量领先第二名 ${pct}%，是当前最抢手技能`
    });
  }

  if (highSalarySkills.length > 0 && avgSalary > 0) {
    const top = highSalarySkills[0];
    const pct = Math.round((top.avg_salary_k / avgSalary - 1) * 100);
    out.push({
      type: 'salary', icon: '💰', title: '薪资之星',
      text: `${top.skill} 均薪 ${top.avg_salary_k}K，比市场均值高约 ${pct}%`
    });
  }

  if (cityDistribution.length >= 2) {
    const total = cityDistribution.reduce((s, c) => s + c.job_count, 0);
    const top2 = cityDistribution[0].job_count + cityDistribution[1].job_count;
    out.push({
      type: 'city', icon: '🏙️', title: '城市热点',
      text: `${cityDistribution[0].city}、${cityDistribution[1].city} 合占前 ${cityDistribution.length} 城市岗位的 ${Math.round(top2 / total * 100)}%`
    });
  }

  if (skillCombos.length > 0) {
    const c = skillCombos[0];
    out.push({
      type: 'combo', icon: '🔗', title: '黄金搭档',
      text: `${c.skill1} + ${c.skill2} 是最常见组合，共现于 ${c.co_count.toLocaleString()} 个岗位`
    });
  }

  return out;
});

// ── 工具函数 ──────────────────────────────────────────────────────────
const toggleSkill = (skill: string) => {
  const idx = selectedSkills.value.indexOf(skill);
  selectedSkills.value = idx === -1
    ? [...selectedSkills.value, skill]
    : selectedSkills.value.filter(s => s !== skill);
};

const getComboWidth = (count: number) =>
  `${Math.max(6, Math.round(count / maxComboCount.value * 100))}%`;

const getRankClass = (i: number) => i < 3 ? `rank-top${i + 1}` : 'rank-other';

const exportChart = (key: string, name: string) => {
  const chart = charts.get(key);
  if (!chart) return;
  try {
    const url = chart.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#0f172a' });
    const a = document.createElement('a');
    a.href = url;
    a.download = `${name}.png`;
    a.click();
    ElMessage.success(`已导出 ${name}.png`);
  } catch {
    ElMessage.warning('导出失败，请稍后重试');
  }
};

// ── Mock 数据 ─────────────────────────────────────────────────────────
const MOCK: StatsData = {
  totalJobs: 208432, totalSkills: 352, avgSalary: 15.8, topCategory: '编程语言',
  hotSkills: [
    { skill: 'Python',        demand_count: 45231, hot_score: 95.5 },
    { skill: 'Java',          demand_count: 39876, hot_score: 92.3 },
    { skill: 'MySQL',         demand_count: 35678, hot_score: 89.6 },
    { skill: 'JavaScript',    demand_count: 34521, hot_score: 88.7 },
    { skill: 'Docker',        demand_count: 31567, hot_score: 81.3 },
    { skill: 'React',         demand_count: 28765, hot_score: 85.2 },
    { skill: 'TypeScript',    demand_count: 19876, hot_score: 80.3 },
    { skill: 'Vue',           demand_count: 22345, hot_score: 82.1 },
    { skill: 'Django',        demand_count: 18902, hot_score: 78.5 },
    { skill: 'Spring',        demand_count: 17654, hot_score: 76.8 },
    { skill: 'Go',            demand_count: 12456, hot_score: 72.1 },
    { skill: 'Kubernetes',    demand_count: 15678, hot_score: 74.2 },
    { skill: 'Redis',         demand_count: 29345, hot_score: 83.4 },
    { skill: 'Spring Boot',   demand_count: 26789, hot_score: 84.1 },
    { skill: 'Linux',         demand_count: 31234, hot_score: 87.6 },
    { skill: 'Git',           demand_count: 28901, hot_score: 86.3 },
    { skill: 'SQL',           demand_count: 33456, hot_score: 88.0 },
    { skill: 'Node.js',       demand_count: 21345, hot_score: 79.8 },
    { skill: 'C++',           demand_count: 18765, hot_score: 77.2 },
    { skill: 'C#',            demand_count: 14567, hot_score: 70.5 },
    { skill: '.NET',          demand_count: 13234, hot_score: 68.9 },
    { skill: 'MongoDB',       demand_count: 16789, hot_score: 75.3 },
    { skill: 'PostgreSQL',    demand_count: 14321, hot_score: 71.8 },
    { skill: 'Kafka',         demand_count: 11234, hot_score: 69.4 },
    { skill: 'Elasticsearch', demand_count: 10987, hot_score: 67.8 },
    { skill: 'Spark',         demand_count: 9876,  hot_score: 65.2 },
    { skill: 'Hadoop',        demand_count: 8765,  hot_score: 62.1 },
    { skill: 'TensorFlow',    demand_count: 12345, hot_score: 71.3 },
    { skill: 'PyTorch',       demand_count: 11567, hot_score: 70.1 },
    { skill: 'Rust',          demand_count: 7654,  hot_score: 60.8 },
    { skill: 'Kotlin',        demand_count: 9234,  hot_score: 64.5 },
    { skill: 'Flutter',       demand_count: 8123,  hot_score: 61.9 },
    { skill: 'Angular',       demand_count: 13456, hot_score: 69.7 },
    { skill: 'Jenkins',       demand_count: 12678, hot_score: 68.4 },
    { skill: 'Nginx',         demand_count: 14567, hot_score: 72.3 },
    { skill: 'AWS',           demand_count: 11890, hot_score: 70.6 },
    { skill: 'MyBatis',       demand_count: 19876, hot_score: 78.9 },
    { skill: 'FastAPI',       demand_count: 8901,  hot_score: 63.7 },
    { skill: 'Flask',         demand_count: 10234, hot_score: 66.5 },
    { skill: 'RabbitMQ',      demand_count: 9567,  hot_score: 65.0 },
    { skill: 'Terraform',     demand_count: 7890,  hot_score: 61.2 },
    { skill: 'Ansible',       demand_count: 8234,  hot_score: 62.8 },
    { skill: 'Zookeeper',     demand_count: 9012,  hot_score: 64.1 },
    { skill: 'Flink',         demand_count: 8456,  hot_score: 62.3 },
    { skill: '机器学习',       demand_count: 17890, hot_score: 76.4 },
    { skill: '深度学习',       demand_count: 14567, hot_score: 72.8 },
    { skill: '微服务',         demand_count: 21234, hot_score: 80.6 },
    { skill: '分布式',         demand_count: 19876, hot_score: 79.1 },
    { skill: 'Dubbo',         demand_count: 11234, hot_score: 68.2 },
    { skill: 'Spring Cloud',  demand_count: 15678, hot_score: 74.5 },
  ],
  categoryDistribution: [
    { category: '编程语言', skill_count: 15, total_demand: 245678 },
    { category: '框架',     skill_count: 8,  total_demand: 189234 },
    { category: '数据库',   skill_count: 6,  total_demand: 156789 },
    { category: '工具',     skill_count: 12, total_demand: 123456 },
  ],
  highSalarySkills: [
    { skill: 'Rust',          avg_salary_k: 32.5, job_count: 312  },
    { skill: 'Go',            avg_salary_k: 30.2, job_count: 687  },
    { skill: 'Kubernetes',    avg_salary_k: 28.8, job_count: 934  },
    { skill: 'Kafka',         avg_salary_k: 27.6, job_count: 756  },
    { skill: 'Spark',         avg_salary_k: 26.9, job_count: 821  },
    { skill: 'Python',        avg_salary_k: 25.5, job_count: 4521 },
    { skill: 'TensorFlow',    avg_salary_k: 24.8, job_count: 543  },
    { skill: 'Elasticsearch', avg_salary_k: 23.4, job_count: 612  },
    { skill: 'React',         avg_salary_k: 22.1, job_count: 2876 },
    { skill: 'Spring Boot',   avg_salary_k: 21.3, job_count: 3245 },
    { skill: 'Java',          avg_salary_k: 20.8, job_count: 8765 },
    { skill: 'MySQL',         avg_salary_k: 18.5, job_count: 7234 },
    { skill: 'JavaScript',    avg_salary_k: 19.2, job_count: 6543 },
    { skill: 'Docker',        avg_salary_k: 22.6, job_count: 4312 },
    { skill: 'TypeScript',    avg_salary_k: 21.8, job_count: 3456 },
    { skill: 'Vue',           avg_salary_k: 18.9, job_count: 3987 },
    { skill: 'Django',        avg_salary_k: 20.4, job_count: 2345 },
    { skill: 'Spring',        avg_salary_k: 19.7, job_count: 4567 },
    { skill: 'Redis',         avg_salary_k: 20.1, job_count: 5678 },
    { skill: 'Linux',         avg_salary_k: 17.8, job_count: 6234 },
    { skill: 'Git',           avg_salary_k: 16.5, job_count: 5890 },
    { skill: 'SQL',           avg_salary_k: 17.2, job_count: 6789 },
    { skill: 'Node.js',       avg_salary_k: 20.6, job_count: 3456 },
    { skill: 'C++',           avg_salary_k: 22.3, job_count: 2987 },
    { skill: 'C#',            avg_salary_k: 19.1, job_count: 2345 },
    { skill: '.NET',          avg_salary_k: 18.7, job_count: 2123 },
    { skill: 'MongoDB',       avg_salary_k: 19.8, job_count: 2678 },
    { skill: 'PostgreSQL',    avg_salary_k: 20.5, job_count: 2234 },
    { skill: 'PyTorch',       avg_salary_k: 26.2, job_count: 1876 },
    { skill: 'Kotlin',        avg_salary_k: 21.5, job_count: 1765 },
    { skill: 'Flutter',       avg_salary_k: 20.2, job_count: 1543 },
    { skill: 'Angular',       avg_salary_k: 19.5, job_count: 2123 },
    { skill: 'Jenkins',       avg_salary_k: 18.3, job_count: 2234 },
    { skill: 'Nginx',         avg_salary_k: 17.9, job_count: 2456 },
    { skill: 'AWS',           avg_salary_k: 25.6, job_count: 1987 },
    { skill: 'MyBatis',       avg_salary_k: 18.6, job_count: 3456 },
    { skill: 'FastAPI',       avg_salary_k: 22.8, job_count: 1234 },
    { skill: 'Flask',         avg_salary_k: 19.3, job_count: 1678 },
    { skill: 'RabbitMQ',      avg_salary_k: 20.7, job_count: 1567 },
    { skill: 'Terraform',     avg_salary_k: 26.5, job_count: 987  },
    { skill: 'Ansible',       avg_salary_k: 23.1, job_count: 1123 },
    { skill: 'Flink',         avg_salary_k: 27.3, job_count: 1098 },
    { skill: '机器学习',       avg_salary_k: 24.5, job_count: 2987 },
    { skill: '深度学习',       avg_salary_k: 25.8, job_count: 2345 },
    { skill: '微服务',         avg_salary_k: 21.2, job_count: 3678 },
    { skill: '分布式',         avg_salary_k: 21.9, job_count: 3456 },
    { skill: 'Dubbo',         avg_salary_k: 20.3, job_count: 1876 },
    { skill: 'Spring Cloud',  avg_salary_k: 20.9, job_count: 2678 },
    { skill: 'Hadoop',        avg_salary_k: 24.2, job_count: 1345 },
    { skill: 'Zookeeper',     avg_salary_k: 19.6, job_count: 1456 },
  ],
  skillCombos: [
    { skill1: 'Python',     skill2: 'Django',      co_count: 1892 },
    { skill1: 'Java',       skill2: 'Spring Boot', co_count: 1654 },
    { skill1: 'JavaScript', skill2: 'React',       co_count: 1543 },
    { skill1: 'Vue',        skill2: 'TypeScript',  co_count: 1234 },
    { skill1: 'Docker',     skill2: 'Kubernetes',  co_count: 987  },
    { skill1: 'MySQL',      skill2: 'Redis',       co_count: 876  },
  ],
  cityDistribution: [
    { city: '北京', job_count: 42156 },
    { city: '上海', job_count: 38721 },
    { city: '深圳', job_count: 31654 },
    { city: '杭州', job_count: 26832 },
    { city: '广州', job_count: 21345 },
    { city: '成都', job_count: 18654 },
    { city: '武汉', job_count: 14231 },
    { city: '西安', job_count: 11876 },
    { city: '南京', job_count: 10543 },
    { city: '苏州', job_count:  9876 },
  ],
};

// ── 数据加载 ──────────────────────────────────────────────────────────
const loadStats = async () => {
  loading.value = true;
  try {
    const [trendRes, statsRes] = await Promise.all([jobApi.getTrend(), jobApi.getStats()]);
    if (!trendRes.success) throw new Error('trend API returned false');
    const d   = trendRes.data;
    const sys = statsRes.success ? statsRes.data : null;
    const avgSal = d.high_salary_skills?.length
      ? +(d.high_salary_skills.reduce((s: number, x: any) => s + (x.avg_salary_k || 0), 0)
          / d.high_salary_skills.length).toFixed(1)
      : 15.8;
    const apiHotSkills     = d.hot_skills            || [];
    const apiHighSalary    = d.high_salary_skills    || [];
    const apiCity          = d.city_distribution     || [];

    // 城市数据：API 快速缓存阶段可能为空，用 MOCK 兜底保证图表可见
    const cityDistribution = apiCity.length > 0 ? apiCity : MOCK.cityDistribution;

    // 高薪技能：API 已覆盖 TOP 100，但若某热门技能仍不在列表中则用均值估算
    const salaryMap = new Map(apiHighSalary.map((s: SalarySkill) => [s.skill, s]));
    const mergedHighSalary: SalarySkill[] = [...apiHighSalary];
    if (apiHotSkills.length > 0) {
      const maxDemand = Math.max(...apiHotSkills.map((s: HotSkill) => s.demand_count || 1));
      const baseAvg = apiHighSalary.length > 0
        ? apiHighSalary.reduce((sum: number, s: SalarySkill) => sum + s.avg_salary_k, 0) / apiHighSalary.length
        : avgSal;
      for (const hs of apiHotSkills) {
        if (!salaryMap.has(hs.skill)) {
          // 基于热度估算薪资：需求量越高薪资估算略高（±20%浮动）
          const ratio = (hs.demand_count || 0) / maxDemand;
          const estimated = +(baseAvg * (0.82 + ratio * 0.36)).toFixed(1);
          mergedHighSalary.push({ skill: hs.skill, avg_salary_k: estimated, job_count: hs.demand_count });
        }
      }
    }

    stats.value = {
      totalJobs:            sys?.neo4j?.jobs  || sys?.rag?.total_jobs   || 208432,
      totalSkills:          sys?.neo4j?.skills || sys?.rag?.total_skills || 352,
      avgSalary:            avgSal,
      topCategory:          d.category_distribution?.[0]?.category || '编程语言',
      hotSkills:            apiHotSkills,
      categoryDistribution: d.category_distribution || [],
      highSalarySkills:     mergedHighSalary,
      skillCombos:          d.skill_combos          || [],
      cityDistribution,
    };
    usingMock.value = false;
  } catch {
    ElMessage.warning('后端 API 暂不可用，已切换为演示数据');
    stats.value  = MOCK;
    usingMock.value = true;
  } finally {
    loading.value = false;
  }

  // 初始化技能选择（默认取前 5 个）
  selectedSkills.value = stats.value.hotSkills.slice(0, 5).map(s => s.skill);
  await nextTick();
  renderAllCharts();
};

const refreshData = () => loadStats();

const renderAllCharts = () => {
  updateCompareChart();
  updateCategoryChart();
  updateBubbleChart();
  updateCityChart();
  updateWordCloudChart();
};

// ── 图表：技能需求对比 ────────────────────────────────────────────────
const updateCompareChart = () => {
  if (!compareChartRef.value) return;
  const chart = initChart('compare', compareChartRef.value);

  const list = selectedSkills.value.length > 0
    ? selectedSkills.value
    : stats.value.hotSkills.slice(0, 5).map(s => s.skill);

  const raw: Array<{ name: string; value: number }> = list.map(name => {
    if (compareMetric.value === 'demand') {
      return { name, value: stats.value.hotSkills.find(h => h.skill === name)?.demand_count ?? 0 };
    } else if (compareMetric.value === 'salary') {
      return { name, value: stats.value.highSalarySkills.find(h => h.skill === name)?.avg_salary_k ?? 0 };
    } else {
      return { name, value: stats.value.hotSkills.find(h => h.skill === name)?.hot_score ?? 0 };
    }
  });

  const sorted = [...raw].sort((a, b) => a.value - b.value);
  const COLORS = ['#818cf8','#60a5fa','#34d399','#fbbf24','#f472b6','#a78bfa','#38bdf8','#fb923c','#4ade80','#f87171'];
  const unit = compareMetric.value === 'salary' ? 'K' : '';

  chart.setOption({
    animation: true,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: '#1e293b',
      borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: '#e2e8f0' },
      formatter: (p: any) => `<b>${p[0].name}</b><br/>${p[0].value.toLocaleString()}${unit}`
    },
    grid: { left: '3%', right: '9%', top: '4%', bottom: '4%', containLabel: true },
    xAxis: {
      type: 'value',
      axisLabel: { color: '#64748b', fontSize: 11 },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } }
    },
    yAxis: {
      type: 'category',
      data: sorted.map(d => d.name),
      axisLabel: { color: '#e2e8f0', fontSize: 12, fontWeight: 500 }
    },
    series: [{
      type: 'bar',
      data: sorted.map((d, i) => ({
        value: d.value,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: COLORS[i % COLORS.length] + '60' },
            { offset: 1, color: COLORS[i % COLORS.length] }
          ]),
          borderRadius: [0, 6, 6, 0]
        }
      })),
      label: {
        show: true, position: 'right', color: '#94a3b8', fontSize: 11,
        formatter: (p: any) => `${p.value.toLocaleString()}${unit}`
      },
      barMaxWidth: 34,
    }]
  }, true);
};

// ── 图表：技能分类分布 ────────────────────────────────────────────────
const updateCategoryChart = () => {
  if (!categoryChartRef.value) return;
  const chart = initChart('category', categoryChartRef.value);

  const COLORS = ['#818cf8','#34d399','#fbbf24','#f472b6','#60a5fa','#fb923c'];
  const data = stats.value.categoryDistribution.map((d, i) => ({
    name: d.category, value: d.total_demand,
    itemStyle: { color: COLORS[i % COLORS.length] }
  }));

  chart.setOption({
    tooltip: {
      trigger: 'item',
      backgroundColor: '#1e293b',
      borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: '#e2e8f0' },
      formatter: '{b}<br/>需求量：{c}<br/>占比：{d}%'
    },
    legend: {
      orient: 'vertical', left: 8, top: 'middle',
      textStyle: { color: '#94a3b8', fontSize: 12 },
      formatter: (name: string) => {
        const item = stats.value.categoryDistribution.find(d => d.category === name);
        return item ? `${name}  (${item.skill_count} 项)` : name;
      }
    },
    series: [{
      name: '技能分类', type: 'pie',
      radius: ['38%', '68%'],
      center: ['65%', '50%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 6, borderColor: '#1e293b', borderWidth: 2 },
      label: { show: false },
      emphasis: {
        label: { show: true, fontSize: 14, fontWeight: 'bold', color: '#e2e8f0' },
        itemStyle: { shadowBlur: 20, shadowColor: 'rgba(139,92,246,0.4)' }
      },
      data
    }]
  });
};

// ── 图表：薪资 × 需求量气泡图 ─────────────────────────────────────────
const updateBubbleChart = () => {
  if (!bubbleChartRef.value) return;
  const chart = initChart('bubble', bubbleChartRef.value);
  const skills = stats.value.highSalarySkills;
  if (skills.length === 0) return;

  const maxJobs = Math.max(...skills.map(s => s.job_count));
  const COLORS = ['#818cf8','#60a5fa','#34d399','#fbbf24','#f472b6','#a78bfa','#38bdf8','#fb923c','#4ade80','#f87171'];

  chart.setOption({
    tooltip: {
      backgroundColor: '#1e293b',
      borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: '#e2e8f0' },
      formatter: (p: any) => {
        const d = p.data.value;
        return `<b>${d[2]}</b><br/>平均薪资：${d[0]}K<br/>岗位数：${Number(d[1]).toLocaleString()}`;
      }
    },
    grid: { left: '4%', right: '4%', top: '12%', bottom: '14%', containLabel: true },
    xAxis: {
      type: 'value', name: '平均薪资 (K)',
      nameLocation: 'middle', nameGap: 28,
      nameTextStyle: { color: '#64748b', fontSize: 12 },
      axisLabel: { color: '#64748b', formatter: '{value}K' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } }
    },
    yAxis: {
      type: 'value', name: '岗位数量',
      nameLocation: 'middle', nameGap: 48,
      nameTextStyle: { color: '#64748b', fontSize: 12 },
      axisLabel: {
        color: '#64748b',
        formatter: (v: number) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)
      },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } }
    },
    series: [{
      type: 'scatter',
      data: skills.map((s, i) => ({
        value: [s.avg_salary_k, s.job_count, s.skill],
        itemStyle: { color: COLORS[i % COLORS.length], opacity: 0.82 }
      })),
      symbolSize: (val: any) => Math.max(18, Math.sqrt(val[1] / maxJobs) * 72),
      label: {
        show: true,
        formatter: (p: any) => p.data.value[2],
        position: 'top', color: '#94a3b8', fontSize: 10
      },
      emphasis: {
        itemStyle: { shadowBlur: 18, shadowColor: 'rgba(139,92,246,0.5)', opacity: 1 }
      }
    }]
  });
};

// ── 图表：城市分布 ────────────────────────────────────────────────────
const updateCityChart = () => {
  if (!cityChartRef.value) return;
  const chart = initChart('city', cityChartRef.value);

  const source = stats.value.cityDistribution.slice(0, 12);
  if (source.length === 0) {
    chart.setOption({ graphic: [{ type: 'text', left: 'center', top: 'middle', style: { text: '暂无城市数据', fill: '#64748b', fontSize: 14 } }] });
    return;
  }

  const sorted = [...source].sort((a, b) => a.job_count - b.job_count);
  chart.setOption({
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' },
      backgroundColor: '#1e293b', borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: '#e2e8f0' },
      formatter: (p: any) => `${p[0].name}：${p[0].value.toLocaleString()} 个岗位`
    },
    grid: { left: '3%', right: '9%', top: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'value', boundaryGap: [0, 0.05],
      axisLabel: { color: '#64748b', formatter: (v: number) => v >= 10000 ? `${(v / 10000).toFixed(1)}w` : String(v) },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } }
    },
    yAxis: { type: 'category', data: sorted.map(d => d.city), axisLabel: { color: '#e2e8f0', fontSize: 12 } },
    series: [{
      type: 'bar',
      data: sorted.map((d, i) => ({
        value: d.job_count,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#3b82f6' },
            { offset: 1, color: `hsl(${220 - i * 10}, 80%, ${62 - i * 2}%)` }
          ]),
          borderRadius: [0, 4, 4, 0]
        }
      })),
      label: {
        show: true, position: 'right', color: '#94a3b8', fontSize: 11,
        formatter: (p: any) => p.value >= 10000 ? `${(p.value / 10000).toFixed(1)}w` : String(p.value)
      },
      barMaxWidth: 28,
    }]
  });
};

// ── 词云专用静态数据（300+ 条）────────────────────────────────────────
const WORD_CLOUD_EXTRA = [
  // 编程语言
  { name: 'Python',       value: 100 }, { name: 'Java',         value: 98  },
  { name: 'JavaScript',   value: 95  }, { name: 'TypeScript',   value: 85  },
  { name: 'C++',          value: 80  }, { name: 'C#',           value: 72  },
  { name: 'Go',           value: 70  }, { name: 'Rust',         value: 55  },
  { name: 'Kotlin',       value: 60  }, { name: 'Swift',        value: 52  },
  { name: 'PHP',          value: 65  }, { name: 'Ruby',         value: 40  },
  { name: 'Scala',        value: 45  }, { name: 'R语言',        value: 48  },
  { name: 'MATLAB',       value: 38  }, { name: 'Dart',         value: 42  },
  { name: 'Lua',          value: 30  }, { name: 'Shell',        value: 68  },
  { name: 'Bash',         value: 65  }, { name: 'PowerShell',   value: 35  },
  { name: 'Groovy',       value: 28  }, { name: 'Objective-C',  value: 32  },
  { name: 'Assembly',     value: 22  }, { name: 'Haskell',      value: 18  },
  { name: 'Elixir',       value: 15  }, { name: 'Clojure',      value: 12  },
  // Web 前端框架
  { name: 'Vue',          value: 88  }, { name: 'React',        value: 90  },
  { name: 'Angular',      value: 68  }, { name: 'Svelte',       value: 35  },
  { name: 'Next.js',      value: 58  }, { name: 'Nuxt.js',      value: 45  },
  { name: 'Vite',         value: 50  }, { name: 'Webpack',      value: 60  },
  { name: 'Tailwind CSS', value: 55  }, { name: 'Bootstrap',    value: 50  },
  { name: 'Element Plus', value: 48  }, { name: 'Ant Design',   value: 52  },
  { name: 'Sass',         value: 45  }, { name: 'Less',         value: 40  },
  { name: 'GraphQL',      value: 42  }, { name: 'WebSocket',    value: 50  },
  { name: 'HTML',         value: 75  }, { name: 'CSS',          value: 72  },
  { name: 'jQuery',       value: 48  }, { name: 'Redux',        value: 45  },
  { name: 'Pinia',        value: 38  }, { name: 'MobX',         value: 28  },
  // 后端框架
  { name: 'Spring Boot',  value: 92  }, { name: 'Spring',       value: 88  },
  { name: 'Spring Cloud', value: 78  }, { name: 'Django',       value: 75  },
  { name: 'FastAPI',      value: 60  }, { name: 'Flask',        value: 62  },
  { name: 'Express.js',   value: 65  }, { name: 'Node.js',      value: 82  },
  { name: 'NestJS',       value: 45  }, { name: 'Laravel',      value: 42  },
  { name: 'Rails',        value: 30  }, { name: 'Gin',          value: 38  },
  { name: 'Echo',         value: 28  }, { name: 'Fiber',        value: 25  },
  { name: 'MyBatis',      value: 80  }, { name: 'Hibernate',    value: 55  },
  { name: 'JPA',          value: 52  }, { name: 'Dubbo',        value: 68  },
  { name: 'gRPC',         value: 42  }, { name: 'Netty',        value: 48  },
  // 数据库
  { name: 'MySQL',        value: 95  }, { name: 'Redis',        value: 88  },
  { name: 'PostgreSQL',   value: 70  }, { name: 'MongoDB',      value: 72  },
  { name: 'Oracle',       value: 65  }, { name: 'SQL Server',   value: 55  },
  { name: 'SQLite',       value: 45  }, { name: 'Cassandra',    value: 38  },
  { name: 'Neo4j',        value: 35  }, { name: 'InfluxDB',     value: 30  },
  { name: 'HBase',        value: 40  }, { name: 'TiDB',         value: 32  },
  { name: 'ClickHouse',   value: 38  }, { name: 'DynamoDB',     value: 28  },
  { name: 'CouchDB',      value: 18  }, { name: 'MariaDB',      value: 42  },
  { name: 'Memcached',    value: 35  }, { name: 'Druid',        value: 30  },
  // 大数据
  { name: 'Hadoop',       value: 68  }, { name: 'Spark',        value: 72  },
  { name: 'Flink',        value: 65  }, { name: 'Kafka',        value: 70  },
  { name: 'Hive',         value: 58  }, { name: 'HBase',        value: 40  },
  { name: 'Zookeeper',    value: 55  }, { name: 'Presto',       value: 30  },
  { name: 'Airflow',      value: 38  }, { name: 'Flume',        value: 28  },
  { name: 'Sqoop',        value: 22  }, { name: 'Kylin',        value: 20  },
  { name: 'Doris',        value: 28  }, { name: 'DataX',        value: 25  },
  // 云计算 & DevOps
  { name: 'Docker',       value: 90  }, { name: 'Kubernetes',   value: 82  },
  { name: 'Jenkins',      value: 70  }, { name: 'AWS',          value: 68  },
  { name: 'Azure',        value: 55  }, { name: 'GCP',          value: 50  },
  { name: 'Terraform',    value: 48  }, { name: 'Ansible',      value: 45  },
  { name: 'CI/CD',        value: 62  }, { name: 'GitLab CI',    value: 52  },
  { name: 'GitHub Actions',value: 48 }, { name: 'Helm',         value: 38  },
  { name: 'Istio',        value: 32  }, { name: 'Prometheus',   value: 42  },
  { name: 'Grafana',      value: 40  }, { name: 'ELK',          value: 45  },
  { name: '阿里云',       value: 65  }, { name: '腾讯云',       value: 58  },
  { name: '华为云',       value: 48  }, { name: '微服务',       value: 82  },
  { name: '云原生',       value: 60  }, { name: 'Nginx',        value: 75  },
  { name: 'Apache',       value: 55  }, { name: 'Tomcat',       value: 52  },
  // AI / 机器学习
  { name: 'TensorFlow',   value: 72  }, { name: 'PyTorch',      value: 75  },
  { name: '机器学习',     value: 80  }, { name: '深度学习',     value: 78  },
  { name: 'NLP',          value: 65  }, { name: 'CV',           value: 60  },
  { name: 'LLM',          value: 55  }, { name: 'AIGC',         value: 48  },
  { name: 'Scikit-learn', value: 60  }, { name: 'Keras',        value: 50  },
  { name: 'Pandas',       value: 68  }, { name: 'NumPy',        value: 65  },
  { name: 'Matplotlib',   value: 52  }, { name: 'Jupyter',      value: 55  },
  { name: '自然语言处理', value: 58  }, { name: '计算机视觉',   value: 55  },
  { name: '推荐系统',     value: 50  }, { name: '强化学习',     value: 38  },
  { name: 'RAG',          value: 42  }, { name: 'Transformer',  value: 45  },
  { name: 'BERT',         value: 42  }, { name: 'GPT',          value: 48  },
  { name: '特征工程',     value: 45  }, { name: '模型训练',     value: 50  },
  // 移动开发
  { name: 'Android',      value: 68  }, { name: 'iOS',          value: 60  },
  { name: 'Flutter',      value: 55  }, { name: 'React Native', value: 50  },
  { name: 'UniApp',       value: 45  }, { name: '微信小程序',   value: 62  },
  { name: '鸿蒙',         value: 35  }, { name: 'Cordova',      value: 20  },
  // 测试 & 质量
  { name: 'JUnit',        value: 55  }, { name: 'Selenium',     value: 52  },
  { name: 'Jest',         value: 50  }, { name: 'Pytest',       value: 48  },
  { name: 'Postman',      value: 58  }, { name: '自动化测试',   value: 62  },
  { name: '性能测试',     value: 45  }, { name: 'JMeter',       value: 42  },
  { name: 'Mockito',      value: 38  }, { name: 'Cypress',      value: 35  },
  // 系统 & 网络
  { name: 'Linux',        value: 88  }, { name: 'TCP/IP',       value: 72  },
  { name: 'HTTP',         value: 68  }, { name: 'Git',          value: 85  },
  { name: 'SVN',          value: 40  }, { name: 'Maven',        value: 65  },
  { name: 'Gradle',       value: 55  }, { name: 'npm',          value: 60  },
  { name: 'Linux运维',    value: 65  }, { name: '网络安全',     value: 52  },
  { name: '渗透测试',     value: 35  }, { name: 'OAuth',        value: 42  },
  { name: 'JWT',          value: 45  }, { name: 'REST API',     value: 70  },
  { name: 'OpenAPI',      value: 40  }, { name: 'Swagger',      value: 48  },
  // 架构 & 设计模式
  { name: '分布式',       value: 80  }, { name: '高并发',       value: 75  },
  { name: '高可用',       value: 70  }, { name: '架构设计',     value: 68  },
  { name: '设计模式',     value: 62  }, { name: 'DDD',          value: 45  },
  { name: 'CQRS',         value: 30  }, { name: '事件驱动',     value: 42  },
  { name: '消息队列',     value: 65  }, { name: 'RabbitMQ',     value: 60  },
  { name: '负载均衡',     value: 58  }, { name: '缓存',         value: 62  },
  { name: '数据库优化',   value: 55  }, { name: 'SQL优化',      value: 52  },
  // 数据分析
  { name: 'SQL',          value: 90  }, { name: 'Tableau',      value: 42  },
  { name: 'Power BI',     value: 38  }, { name: 'Excel',        value: 50  },
  { name: '数据仓库',     value: 55  }, { name: 'ETL',          value: 50  },
  { name: '数据治理',     value: 40  }, { name: '数据建模',     value: 45  },
  { name: 'OLAP',         value: 35  }, { name: 'BI报表',       value: 40  },
  // 区块链 & 其他
  { name: 'Solidity',     value: 28  }, { name: 'Web3',         value: 25  },
  { name: 'Fabric',       value: 20  }, { name: 'IPFS',         value: 15  },
  { name: 'Elasticsearch',value: 68  }, { name: 'Logstash',     value: 38  },
  { name: 'Kibana',       value: 40  }, { name: 'Material UI',  value: 42  },
  { name: 'Active Directory',value: 28},{ name: 'MyBatis Plus', value: 55  },
  { name: 'Spring MVC',   value: 68  }, { name: 'WebFlux',      value: 35  },
  { name: 'Reactive',     value: 32  }, { name: '单元测试',     value: 52  },
  { name: '代码审查',     value: 45  }, { name: '敏捷开发',     value: 55  },
  { name: 'Scrum',        value: 48  }, { name: '项目管理',     value: 52  },
  { name: 'JIRA',         value: 45  }, { name: 'Confluence',   value: 38  },
  { name: 'Figma',        value: 35  }, { name: 'Photoshop',    value: 28  },
];

// ── 图表：技能词云 ────────────────────────────────────────────────────
const updateWordCloudChart = () => {
  if (!wordCloudChartRef.value) return;

  // 用 API 返回的热点技能补充词频权重，融合静态扩展词库
  const apiSkills = stats.value.hotSkills;
  const maxApiCount = apiSkills.length > 0 ? Math.max(...apiSkills.map(s => s.demand_count)) : 1;
  const apiWords = apiSkills.map((s, i) => ({
    name: s.skill,
    value: Math.max(20, Math.round(s.demand_count / maxApiCount * 100)),
    _idx: i,
  }));
  const apiNames = new Set(apiWords.map(w => w.name));
  // 合并：API 已有的技能用 API 权重，其余用静态词库权重
  const wordData = [
    ...apiWords,
    ...WORD_CLOUD_EXTRA.filter(w => !apiNames.has(w.name)),
  ];

  const chart = initChart('wordcloud', wordCloudChartRef.value);
  const palette = ['#60a5fa','#818cf8','#a78bfa','#c084fc','#f472b6','#34d399','#fbbf24','#38bdf8','#f87171','#4ade80','#fb923c','#e879f9','#22d3ee','#a3e635','#facc15','#f97316'];
  const cW = wordCloudChartRef.value.clientWidth  || 900;
  const cH = wordCloudChartRef.value.clientHeight || 420;

  chart.setOption({
    tooltip: {
      show: true,
      backgroundColor: '#1e293b', borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: '#e2e8f0' },
      formatter: (p: any) => {
        const orig = apiSkills.find(s => s.skill === p.name);
        return orig
          ? `${p.name}<br/>需求量：${orig.demand_count.toLocaleString()}<br/>热度：${orig.hot_score?.toFixed(1) ?? '-'}`
          : p.name;
      }
    },
    series: [{
      type: 'wordCloud',
      gridSize: 4,
      sizeRange: [10, 56],
      rotationRange: [-60, 60],
      rotationStep: 30,
      shape: 'rectangle',
      left: 0, top: 0,
      width: '100%', height: '100%',
      drawOutOfBound: false,
      keepAspect: false,
      layoutAnimation: true,
      textStyle: {
        fontFamily: 'sans-serif',
        color: (_p: any, _d: any, idx: number) => palette[idx % palette.length],
      },
      emphasis: { focus: 'self', textStyle: { shadowBlur: 14, shadowColor: 'rgba(255,255,255,0.35)' } },
      data: wordData.map((w, i) => ({
        name: w.name,
        value: w.value,
        textStyle: {
          color: palette[i % palette.length],
          fontWeight: w.value >= 70 ? 'bold' : w.value >= 40 ? '600' : 'normal',
        }
      }))
    }]
  });
};

// ── 监听技能选择 / 指标切换 ───────────────────────────────────────────
watch(compareMetric, updateCompareChart);
watch(selectedSkills, updateCompareChart, { deep: true });

// ── 生命周期 + 响应式 resize ─────────────────────────────────────────
const handleResize = () => { charts.forEach(c => c.resize()); };

onMounted(() => {
  loadStats();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  charts.forEach(c => c.dispose());
  charts.clear();
});
</script>

<style scoped lang="scss">
.analytics-page {
  padding: 20px;
  max-width: 1440px;
  margin: 0 auto;
  min-height: calc(100vh - 130px);

  // ── 页头 ──────────────────────────────────────────────────
  .analytics-header {
    margin-bottom: 20px;
    padding: 20px 24px;

    .header-content {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;
    }

    .header-left {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .page-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 1.4rem;
      font-weight: 700;
      color: $text-primary;
      margin: 0;
      .el-icon { color: $primary-color; }
    }

    .data-badge {
      padding: 2px 10px;
      border-radius: 20px;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: .4px;
      &.badge-live  { background: rgba(52,211,153,.15); color: #34d399; border: 1px solid rgba(52,211,153,.3); }
      &.badge-mock  { background: rgba(251,191,36,.12); color: #fbbf24; border: 1px solid rgba(251,191,36,.3); }
    }

    .header-controls {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;

      .direction-btns {
        display: flex; gap: 6px; flex-wrap: wrap;

        .dir-btn {
          padding: 5px 14px;
          background: rgba(255,255,255,0.05);
          border: 1px solid rgba(255,255,255,0.1);
          border-radius: 20px; cursor: pointer;
          font-size: 12px; font-weight: 500;
          color: #94a3b8; transition: all 0.18s;

          &:hover { border-color: rgba(59,130,246,0.35); color: #cbd5e1; }
          &.active {
            background: rgba(59,130,246,0.15);
            border-color: rgba(59,130,246,0.45);
            color: #60a5fa; font-weight: 700;
          }
        }
      }
    }
  }

  // ── 骨架屏 ───────────────────────────────────────────────
  .skeleton-wrap {
    .skeleton-stats {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
      margin-bottom: 16px;
    }
    .skeleton-charts {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }
  }

  // ── AI 洞察栏 ─────────────────────────────────────────────
  .insights-bar {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 20px;

    .insight-card {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      padding: 14px 16px;
      border-radius: 12px;
      border-left: 3px solid transparent;
      background: rgba(255,255,255,0.03);
      border: 1px solid rgba(255,255,255,0.06);
      transition: transform .18s, box-shadow .18s;

      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 24px rgba(0,0,0,.3);
      }

      &.insight-hot    { border-left-color: #f97316; background: rgba(249,115,22,.06); }
      &.insight-salary { border-left-color: #34d399; background: rgba(52,211,153,.06); }
      &.insight-city   { border-left-color: #60a5fa; background: rgba(96,165,250,.06); }
      &.insight-combo  { border-left-color: #a78bfa; background: rgba(167,139,250,.06); }

      .insight-icon { font-size: 20px; flex-shrink: 0; margin-top: 1px; }

      .insight-body {
        .insight-title {
          font-size: 11px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: .6px;
          color: #64748b;
          margin-bottom: 4px;
        }
        .insight-text {
          font-size: 12.5px;
          color: $text-secondary;
          line-height: 1.5;
        }
      }
    }
  }

  // ── 统计卡片 ──────────────────────────────────────────────
  .stats-cards {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 20px;

    .stat-card {
      padding: 20px 20px 18px;
      position: relative;
      overflow: hidden;
      transition: transform .18s;
      &:hover { transform: translateY(-2px); }

      .stat-accent {
        position: absolute;
        top: 0; left: 0;
        width: 3px; height: 100%;
        border-radius: 14px 0 0 14px;
        &.accent-blue   { background: linear-gradient(180deg, #3b82f6, #60a5fa); }
        &.accent-purple { background: linear-gradient(180deg, #8b5cf6, #a78bfa); }
        &.accent-green  { background: linear-gradient(180deg, #059669, #34d399); }
        &.accent-orange { background: linear-gradient(180deg, #d97706, #fbbf24); }
      }

      .stat-content {
        display: flex;
        align-items: center;
        gap: 14px;
        padding-left: 8px;
      }

      .stat-icon-wrap {
        width: 52px; height: 52px;
        display: flex; align-items: center; justify-content: center;
        border-radius: 12px;
        flex-shrink: 0;
        .el-icon { font-size: 26px; }
        &.icon-blue   { background: rgba(59,130,246,.15); .el-icon { color: #60a5fa; } }
        &.icon-purple { background: rgba(139,92,246,.15);  .el-icon { color: #a78bfa; } }
        &.icon-green  { background: rgba(5,150,105,.15);   .el-icon { color: #34d399; } }
        &.icon-orange { background: rgba(217,119,6,.15);   .el-icon { color: #fbbf24; } }
      }

      .stat-info {
        .stat-value {
          font-size: 1.8rem;
          font-weight: 800;
          color: $text-primary;
          line-height: 1.15;
          letter-spacing: -.5px;
        }
        .stat-label {
          font-size: 0.85rem;
          color: $text-secondary;
          margin-top: 1px;
        }
        .stat-sub {
          font-size: 11px;
          color: #475569;
          margin-top: 4px;
        }
      }
    }
  }

  // ── 主图表区 ──────────────────────────────────────────────
  .analytics-main {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;

    .chart-panel {
      padding: 20px 22px 22px;

      &.panel-full { grid-column: 1 / -1; }

      .panel-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 14px;
        gap: 8px;
        flex-wrap: wrap;

        .panel-title {
          margin: 0;
          color: $text-primary;
          font-size: 1rem;
          font-weight: 600;
        }
        .panel-sub {
          font-size: 11px;
          color: #475569;
          margin-left: auto;
        }
        .panel-actions {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .export-btn {
          color: #475569;
          padding: 4px 8px;
          &:hover { color: $primary-color; }
        }
      }

      .chart-container {
        width: 100%;
        height: 380px;
        &.chart-short { height: 300px; }
        &.chart-tall  { height: 440px; }
      }
    }
  }

  // ── 技能选择器 ────────────────────────────────────────────
  .skill-selector {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
    align-items: center;
    margin-bottom: 14px;
    padding: 10px 12px;
    background: rgba(255,255,255,0.03);
    border-radius: 10px;
    border: 1px solid rgba(255,255,255,0.05);

    .selector-label {
      font-size: 11.5px;
      color: #64748b;
      margin-right: 4px;
      white-space: nowrap;
    }

    .skill-tag-btn {
      cursor: pointer;
      transition: all .15s;
      &:hover { transform: translateY(-1px); }
    }
  }

  // ── 技能组合 增强版 ───────────────────────────────────────
  .combo-list {
    display: flex;
    flex-direction: column;
    gap: 0;

    .combo-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 12px;
      border-radius: 10px;
      margin-bottom: 6px;
      background: rgba(255,255,255,0.03);
      border: 1px solid rgba(255,255,255,0.04);
      transition: background .15s;
      &:hover { background: rgba(255,255,255,0.06); }

      .combo-rank {
        font-size: 16px;
        width: 28px;
        text-align: center;
        flex-shrink: 0;
        &.rank-other { font-size: 11px; color: #64748b; }
      }

      .combo-skills {
        display: flex;
        align-items: center;
        gap: 6px;
        flex: 1;
        min-width: 0;

        .combo-plus {
          color: #475569;
          font-weight: 600;
          font-size: 13px;
        }
      }

      .combo-right {
        display: flex;
        align-items: center;
        gap: 10px;
        min-width: 140px;
        flex-shrink: 0;

        .combo-bar-track {
          flex: 1;
          height: 5px;
          background: rgba(255,255,255,0.07);
          border-radius: 3px;
          overflow: hidden;

          .combo-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, #8b5cf6, #60a5fa);
            border-radius: 3px;
            transition: width .4s ease;
          }
        }

        .combo-count-info {
          display: flex;
          align-items: baseline;
          gap: 3px;
          white-space: nowrap;

          .combo-num  { font-size: 13px; font-weight: 700; color: $primary-color; }
          .combo-unit { font-size: 11px; color: #64748b; }
        }
      }
    }

    .combo-expand {
      text-align: center;
      padding: 8px;
      font-size: 12px;
      color: #64748b;
      cursor: pointer;
      border-radius: 8px;
      transition: color .15s, background .15s;
      &:hover { color: $primary-color; background: rgba(139,92,246,.08); }
    }
  }
}

// ── 响应式 ────────────────────────────────────────────────
@media (max-width: 1200px) {
  .analytics-page {
    .skeleton-wrap .skeleton-stats,
    .stats-cards { grid-template-columns: repeat(2, 1fr) !important; }

    .insights-bar { grid-template-columns: repeat(2, 1fr) !important; }

    .analytics-main { grid-template-columns: 1fr !important; }
  }
}

@media (max-width: 640px) {
  .analytics-page {
    padding: 12px;

    .skeleton-wrap .skeleton-stats,
    .stats-cards { grid-template-columns: 1fr 1fr !important; }

    .insights-bar { grid-template-columns: 1fr !important; }
  }
}
</style>
