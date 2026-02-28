<template>
  <div class="user-center">
    <GlassCard class="user-header">
      <div class="user-info">
        <div class="avatar">
          <el-icon><User /></el-icon>
        </div>
        <div class="user-details">
          <h2 class="username">{{ profileForm.name || userName }}</h2>
          <p class="user-desc">{{ profileForm.position || 'AI驱动的智能求职助手' }}</p>
          <div class="user-stats">
            <div class="stat-item">
              <span class="stat-number">{{ favoriteJobs.length }}</span>
              <span class="stat-label">收藏岗位</span>
            </div>
            <div class="stat-item">
              <span class="stat-number">{{ matchReports.length }}</span>
              <span class="stat-label">匹配报告</span>
            </div>
            <div class="stat-item">
              <span class="stat-number">{{ userSkills.length }}</span>
              <span class="stat-label">技能项</span>
            </div>
          </div>
        </div>
      </div>
    </GlassCard>

    <div class="user-center-main">
      <div class="sidebar">
        <el-menu
          :default-active="activeMenu"
          class="user-menu"
          @select="handleMenuSelect"
        >
          <el-menu-item index="profile">
            <el-icon><User /></el-icon>
            <span>个人资料</span>
          </el-menu-item>
          <el-menu-item index="resume">
            <el-icon><Document /></el-icon>
            <span>我的简历</span>
          </el-menu-item>
          <el-menu-item index="skills">
            <el-icon><Medal /></el-icon>
            <span>我的技能</span>
          </el-menu-item>
          <el-menu-item index="favorites">
            <el-icon><Star /></el-icon>
            <span>收藏岗位</span>
          </el-menu-item>
          <el-menu-item index="reports">
            <el-icon><DataAnalysis /></el-icon>
            <span>匹配报告</span>
          </el-menu-item>
        </el-menu>
      </div>

      <div class="content">
        <!-- 个人资料 -->
        <div v-if="activeMenu === 'profile'" class="profile-content">
          <GlassCard class="form-card">
            <div class="card-header">
              <h3 class="card-title">个人资料</h3>
              <!-- 求职状态徽章 -->
              <span class="job-status-badge" :class="profileForm.job_status">
                {{ JOB_STATUS_OPTIONS.find(o=>o.value===profileForm.job_status)?.label || '求职中' }}
              </span>
            </div>
            <el-form :model="profileForm" label-width="110px" class="profile-form">

              <!-- ── 基本信息 ── -->
              <div class="form-section-title">基本信息</div>
              <el-form-item label="姓名">
                <el-input v-model="profileForm.name" placeholder="真实姓名" />
              </el-form-item>
              <el-form-item label="联系邮箱">
                <el-input v-model="profileForm.email" placeholder="example@email.com" />
              </el-form-item>
              <el-form-item label="联系电话">
                <el-input v-model="profileForm.phone" placeholder="手机号码" />
              </el-form-item>
              <el-form-item label="所在城市">
                <el-select v-model="profileForm.city" placeholder="请选择所在城市" filterable>
                  <el-option v-for="c in ALL_CITIES" :key="c" :label="c" :value="c" />
                </el-select>
              </el-form-item>

              <!-- ── 求职意向 ── -->
              <div class="form-section-title">求职意向</div>
              <el-form-item label="目标职位">
                <el-input v-model="profileForm.position" placeholder="如：AI应用开发工程师 / 后端工程师" />
              </el-form-item>
              <el-form-item label="求职状态">
                <el-select v-model="profileForm.job_status" placeholder="当前求职状态">
                  <el-option v-for="o in JOB_STATUS_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
                </el-select>
              </el-form-item>
              <el-form-item label="工作年限">
                <el-select v-model="profileForm.experience_years" placeholder="工作经验">
                  <el-option v-for="o in EXP_YEAR_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
                </el-select>
              </el-form-item>

              <!-- ── 教育背景 ── -->
              <div class="form-section-title">教育背景</div>
              <el-form-item label="毕业院校">
                <el-input v-model="profileForm.school" placeholder="如：某某大学" />
              </el-form-item>
              <el-form-item label="专业">
                <el-input v-model="profileForm.major" placeholder="如：计算机科学与技术" />
              </el-form-item>
              <el-form-item label="最高学历">
                <el-select v-model="profileForm.degree" placeholder="请选择学历">
                  <el-option v-for="d in DEGREE_OPTIONS" :key="d" :label="d" :value="d" />
                </el-select>
              </el-form-item>

              <!-- ── 对外链接 ── -->
              <div class="form-section-title">对外链接</div>
              <el-form-item label="GitHub">
                <el-input v-model="profileForm.github_url" placeholder="https://github.com/yourusername">
                  <template #prefix><el-icon><Link /></el-icon></template>
                </el-input>
              </el-form-item>
              <el-form-item label="个人主页">
                <el-input v-model="profileForm.linkedin_url" placeholder="领英 / 牛客 / 个人博客 等">
                  <template #prefix><el-icon><Link /></el-icon></template>
                </el-input>
              </el-form-item>

              <el-form-item>
                <AIButton ai-type="primary" @click="saveProfile" :loading="loading.profile">
                  <template #icon><el-icon><Check /></el-icon></template>
                  保存资料
                </AIButton>
              </el-form-item>
            </el-form>
          </GlassCard>
        </div>

        <!-- 我的简历 -->
        <div v-if="activeMenu === 'resume'" class="resume-content">
          <GlassCard class="resume-card">

            <!-- ① 标题栏 -->
            <div class="rc-header">
              <div class="rc-header-left">
                <el-icon class="rc-header-icon"><Document /></el-icon>
                <span class="rc-header-title">我的简历</span>
              </div>
              <div class="rc-header-right">
                <AIButton ai-type="primary" @click="saveResume" :loading="loading.resume">
                  <template #icon><el-icon><Check /></el-icon></template>
                  保存简历
                </AIButton>
              </div>
            </div>

            <!-- ① 完整度进度条 -->
            <div class="rc-completeness">
              <div class="rc-comp-top">
                <span class="rc-comp-label">简历完整度</span>
                <span class="rc-comp-pct" :style="{ color: completenessLabel.color }">
                  {{ resumeCompleteness }}% · {{ completenessLabel.text }}
                </span>
              </div>
              <div class="rc-comp-bar">
                <div class="rc-comp-fill"
                  :style="{ width: resumeCompleteness + '%', background: completenessLabel.color }">
                </div>
              </div>
              <div class="rc-comp-tips" v-if="resumeCompleteness < 90">
                <span v-if="!resumeRawText || resumeRawText.length < 100">📝 上传或填写简历全文</span>
                <span v-if="!profileForm.github_url">🔗 填写 GitHub 链接</span>
                <span v-if="userSkills.length < 3">⚡ 添加至少3项技能</span>
              </div>
            </div>

            <!-- ② 上传区 -->
            <div
              class="rc-dropzone"
              :class="{ 'is-over': isDragOver, 'is-parsing': importLoading }"
              @dragover.prevent="isDragOver = true"
              @dragleave.prevent="isDragOver = false"
              @drop.prevent="handleFileDrop"
              @click="triggerFileInput"
            >
              <input ref="resumeFileInputRef" type="file" accept=".pdf,.docx,.doc,.txt" style="display:none" @change="handleFileChange" />
              <template v-if="importLoading">
                <span class="dz-spin"></span>
                <span class="dz-hint">正在解析文件，请稍候...</span>
              </template>
              <template v-else>
                <el-icon class="dz-up-icon"><Upload /></el-icon>
                <span class="dz-main-text">拖拽或点击上传简历文件</span>
                <span class="dz-sub-text">支持 PDF &nbsp;·&nbsp; Word (.docx) &nbsp;·&nbsp; 纯文本 (.txt)</span>
              </template>
            </div>

            <!-- ③ AI 操作按钮行 -->
            <div class="rc-ai-row">
              <button class="rc-ai-btn rc-ai-btn--analyze" :disabled="aiResumeLoading" @click="analyzeResume">
                <el-icon v-if="!(aiResumeLoading && aiResumeMode==='analyze')"><Search /></el-icon>
                <span v-else class="rc-spin"></span>
                <span class="rc-ai-btn-text">
                  <strong>AI 简历分析</strong>
                  <small>综合评分 · 优劣势 · 改进建议</small>
                </span>
              </button>
              <button class="rc-ai-btn rc-ai-btn--optimize" :disabled="aiResumeLoading" @click="optimizeResume">
                <el-icon v-if="!(aiResumeLoading && aiResumeMode==='optimize')"><MagicStick /></el-icon>
                <span v-else class="rc-spin"></span>
                <span class="rc-ai-btn-text">
                  <strong>AI 智能优化</strong>
                  <small>STAR 法则 · 量化成果 · ATS 友好</small>
                </span>
              </button>
            </div>

            <!-- ④ AI 结果面板 -->
            <transition name="rc-slide">
              <div v-if="aiResumeResult || aiResumeLoading" class="rc-ai-result">
                <div class="rc-result-bar">
                  <div class="rc-result-bar-left">
                    <el-icon><component :is="aiResumeMode==='optimize' ? MagicStick : Search" /></el-icon>
                    <span>{{ aiResumeMode === 'optimize' ? 'AI 优化建议' : 'AI 简历分析报告' }}</span>
                    <span class="rc-badge">Qwen</span>
                  </div>
                  <button v-if="aiResumeResult" class="rc-result-close" @click="aiResumeResult='';aiResumeLoading=false">✕</button>
                </div>
                <div v-if="aiResumeLoading" class="rc-skeleton">
                  <div class="sk" v-for="n in 7" :key="n" :style="{ width:[90,72,84,58,78,65,48][n-1]+'%' }"></div>
                </div>
                <div v-else class="rc-result-body" v-html="renderResumeAI(aiResumeResult)"></div>
              </div>
            </transition>

            <!-- ⑤ 简历全文编辑器 -->
            <div class="rc-editor">
              <div class="rc-editor-bar">
                <div class="rc-editor-bar-left">
                  <el-icon><EditPen /></el-icon>
                  <span>简历全文</span>
                </div>
                <span class="rc-wordcount">{{ resumeRawText.length }} 字</span>
              </div>
              <textarea
                v-model="resumeRawText"
                class="rc-textarea"
                placeholder="在此粘贴或编辑您的简历全文，也可通过上方导入文件自动提取...&#10;&#10;【基本信息】张三 | 本科 | 计算机科学&#10;【工作经历】XXX公司 后端工程师 2023.07-至今&#10;  · 负责核心模块开发，QPS 提升 40%&#10;【技能栈】Python / Java / Spring Boot / MySQL / Redis"
                spellcheck="false"
              ></textarea>
            </div>

            <!-- ⑥ 求职偏好（折叠） -->
            <div class="rc-prefs">
              <div class="rc-prefs-toggle" @click="showStructForm = !showStructForm">
                <div class="rc-prefs-toggle-left">
                  <el-icon><List /></el-icon>
                  <span>求职偏好 &nbsp;<small>期望城市 / 薪资 / 技能标签</small></span>
                </div>
                <el-icon class="rc-chevron" :class="{ 'is-open': showStructForm }"><ArrowDown /></el-icon>
              </div>
              <transition name="rc-fold">
                <div v-if="showStructForm" class="rc-prefs-body">
                  <!-- 期望城市：全部33城市可滚动 chips -->
                  <div class="pref-row">
                    <div class="pref-label-row">
                      <span class="pref-label">期望城市</span>
                      <span class="pref-selected-count">已选 {{ resumeForm.expectCities.length }} 个</span>
                    </div>
                    <div class="city-chips city-chips--scroll">
                      <label v-for="city in ALL_CITIES" :key="city"
                        class="city-chip" :class="{ active: resumeForm.expectCities.includes(city) }">
                        <input type="checkbox" :value="city" v-model="resumeForm.expectCities" style="display:none" />
                        {{ city }}
                      </label>
                    </div>
                  </div>
                  <!-- 期望薪资 -->
                  <div class="pref-row">
                    <span class="pref-label">期望薪资</span>
                    <div class="pref-salary-row">
                      <span class="salary-val">{{ formatSalary(resumeForm.expectSalary) }}</span>
                      <el-slider v-model="resumeForm.expectSalary" :min="0" :max="50" :step="5" :format-tooltip="formatSalary" class="rc-slider" />
                    </div>
                  </div>
                  <!-- 技能标签 -->
                  <div class="pref-row">
                    <span class="pref-label">技能标签</span>
                    <div class="skills-chips">
                      <SkillTag v-for="(skill, i) in resumeForm.skills" :key="i" :label="skill" level="primary" closable @close="removeSkill(i)" />
                      <el-input v-if="newSkillInputVisible" ref="newSkillInputRef" v-model="newSkillInput" class="new-skill-input" size="small" @keyup.enter="addNewSkill" @blur="addNewSkill" />
                      <el-button v-else class="add-skill-btn" size="small" @click="showNewSkillInput">+ 添加</el-button>
                    </div>
                  </div>
                </div>
              </transition>
            </div>

          </GlassCard>
        </div>

        <!-- 我的技能 -->
        <div v-if="activeMenu === 'skills'" class="skills-content">
          <GlassCard class="skills-card">
            <div class="card-header">
              <h3 class="card-title">我的技能</h3>
              <div class="card-header-btns">
                <AIButton ai-type="analysis" @click="analyzeSkills">
                  <template #icon>
                    <el-icon><DataAnalysis /></el-icon>
                  </template>
                  匹配看板
                </AIButton>
                <button class="ai-diagnose-btn" @click="diagnoseSkills" :disabled="aiDiagnoseLoading">
                  <span v-if="aiDiagnoseLoading" class="diag-spin"></span>
                  <span v-else>✨</span>
                  {{ aiDiagnoseLoading ? 'AI 诊断中...' : 'AI 诊断技能档案' }}
                </button>
              </div>
            </div>

            <!-- AI 诊断结果 -->
            <div v-if="aiDiagnoseResult || aiDiagnoseLoading" class="ai-diagnose-panel">
              <div class="diagnose-header">
                <span class="diagnose-label">✨ Qwen3.5-Plus · 技能档案诊断</span>
                <button v-if="aiDiagnoseResult" class="diagnose-close" @click="aiDiagnoseResult = ''">✕</button>
              </div>
              <div v-if="aiDiagnoseLoading" class="diagnose-skeleton">
                <div class="sk w80"></div>
                <div class="sk w60"></div>
                <div class="sk w90"></div>
                <div class="sk w50"></div>
                <div class="sk w75"></div>
              </div>
              <div v-else class="diagnose-content" v-html="renderDiagnose(aiDiagnoseResult)"></div>
            </div>

            <div class="skills-list">
              <div
                v-for="(skill, index) in userSkills"
                :key="index"
                class="skill-item"
              >
                <div class="skill-info">
                  <h4>{{ skill.name }}</h4>
                  <p>{{ skill.description }}</p>
                </div>
                <div class="skill-level">
                  <el-rate
                    v-model="skill.level"
                    :max="5"
                    show-text
                    allow-half
                  />
                </div>
              </div>
            </div>
          </GlassCard>
        </div>

        <!-- 收藏岗位 -->
        <div v-if="activeMenu === 'favorites'" class="favorites-content">
          <GlassCard class="favorites-card">
            <div class="card-header">
              <h3 class="card-title">收藏岗位</h3>
              <span class="card-count">共 {{ favoriteJobs.length }} 个</span>
            </div>

            <!-- 空状态 -->
            <div v-if="!favoriteJobs.length" class="empty-state">
              <el-icon class="empty-icon"><Star /></el-icon>
              <p>暂无收藏岗位</p>
              <small>在职位搜索中点击收藏按钮，岗位将展示在这里</small>
            </div>

            <div class="jobs-list" v-else>
              <div v-for="job in favoriteJobs" :key="job.id" class="job-item">
                <div class="job-header">
                  <div class="job-header-left">
                    <h4 class="job-title">{{ job.title }}</h4>
                    <div class="job-meta">
                      <span class="company">{{ job.company }}</span>
                      <span class="dot">·</span>
                      <span class="city">{{ job.city }}</span>
                      <span class="dot">·</span>
                      <span class="salary">{{ job.salary_range }}</span>
                    </div>
                  </div>
                  <button class="unfav-btn" @click="unfavoriteJob(job.id)" title="取消收藏">✕</button>
                </div>
                <div class="job-skills">
                  <SkillTag
                    v-for="skill in job.skills.slice(0, 6)"
                    :key="skill"
                    :label="skill"
                    level="secondary"
                  />
                </div>
              </div>
            </div>
          </GlassCard>
        </div>

        <!-- 匹配报告 -->
        <div v-if="activeMenu === 'reports'" class="reports-content">
          <GlassCard class="reports-card">
            <h3 class="card-title">匹配报告</h3>
            <div class="reports-list">
              <GlassCard
                v-for="report in matchReports"
                :key="report.id"
                class="report-item"
              >
                <div class="report-header">
                  <h4>{{ report.title }}</h4>
                  <span class="report-date">{{ report.date }}</span>
                </div>
                <div class="report-summary">
                  <p>{{ report.summary }}</p>
                </div>
                <div class="report-metrics">
                  <div class="metric">
                    <span class="metric-label">匹配度</span>
                    <el-progress
                      :percentage="report.matchRate"
                      :color="progressColor"
                    />
                  </div>
                </div>
                <div class="report-actions">
                  <AIButton ai-type="analysis" size="small">
                    详情分析
                  </AIButton>
                </div>
              </GlassCard>
            </div>
          </GlassCard>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted, computed } from 'vue';
import { ElMessage } from 'element-plus';
import { 
  User, Document, Medal, Star, 
  DataAnalysis, Check, Upload,
  MagicStick, EditPen, Search, List, ArrowDown,
  Link
} from '@element-plus/icons-vue';
import GlassCard from '@/components/GlassCard.vue';
import SkillTag from '@/components/SkillTag.vue';
import AIButton from '@/components/AIButton.vue';
import { userApi } from '@/api/userApi';
import { jobApi } from '@/api/jobApi';
import { renderMarkdown as _renderMd, buildDiagnosisPrompt } from '@/utils/aiPrompt';

// ── 33个城市（来自后端爬虫配置 cities_done + cities_new）──────────────
const ALL_CITIES = [
  '北京', '上海', '广州', '深圳', '杭州', '成都',
  '天津', '重庆', '武汉', '南京', '苏州', '西安',
  '长沙', '郑州', '合肥', '福州', '厦门', '贵阳',
  '南昌', '哈尔滨', '长春', '大连', '无锡', '扬州',
  '佛山', '东莞', '海口', '太原', '兰州', '呼和浩特',
  '常德', '开封', '芜湖'
];

// 求职状态选项
const JOB_STATUS_OPTIONS = [
  { label: '🔥 积极求职中', value: 'active' },
  { label: '👀 随时接受机会', value: 'open' },
  { label: '😴 暂不考虑', value: 'inactive' },
];

// 学历选项
const DEGREE_OPTIONS = ['大专', '本科', '硕士', '博士', 'MBA', '其他'];

// 工作年限选项
const EXP_YEAR_OPTIONS = [
  { label: '应届生', value: 0 },
  { label: '1年以内', value: 1 },
  { label: '1-3年', value: 2 },
  { label: '3-5年', value: 4 },
  { label: '5-10年', value: 7 },
  { label: '10年以上', value: 10 },
];


// 当前激活的菜单项
const activeMenu = ref('profile');

// 从localStorage读取用户名
const userName = computed(() => {
  const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}');
  return userInfo.username || userInfo.name || '用户';
});

// 加载状态
const loading = ref({
  profile: false,
  resume: false,
  skills: false,
  favorites: false,
  reports: false,
});

// 个人资料表单（含求职意向、教育、对外链接）
const profileForm = ref({
  name: '',
  email: '',
  phone: '',
  city: '',
  position: '',         // 求职目标职位（如"AI应用开发工程师"）
  job_status: 'active', // 求职状态
  experience_years: 0,  // 工作年限档位
  school: '',           // 毕业院校
  major: '',            // 专业
  degree: '',           // 学历
  github_url: '',       // GitHub / 个人主页
  linkedin_url: '',     // 领英 / 牛客 等
});

// 简历表单
const resumeForm = ref({
  id: undefined,
  name: '',
  school: '',
  major: '',
  degree: '',
  skills: [] as string[],
  expectCities: [] as string[],
  expectSalary: 0
});

// 简历全文（导入 / 手动编辑）
const resumeRawText = ref('');

// 结构化信息折叠状态
const showStructForm = ref(false);

// 文件导入相关
const resumeFileInputRef = ref<HTMLInputElement | null>(null);
const isDragOver = ref(false);
const importLoading = ref(false);

// AI 简历分析 / 优化结果
const aiResumeLoading = ref(false);
const aiResumeResult = ref('');
const aiResumeMode = ref<'analyze' | 'optimize'>('analyze');
const renderResumeAI = (text: string) => _renderMd(text);

// 技能列表
const userSkills = ref([] as Array<{
  name: string;
  description: string;
  level: number;
}>);

// 简历完整度计算（0-100）
const resumeCompleteness = computed(() => {
  let score = 0;
  if (resumeRawText.value.length > 100) score += 40;       // 简历全文
  else if (resumeRawText.value.length > 0) score += 15;
  if (profileForm.value.name)  score += 10;                 // 姓名
  if (profileForm.value.phone || profileForm.value.email) score += 10; // 联系方式
  if (profileForm.value.school) score += 10;               // 教育背景
  if (userSkills.value.length >= 3) score += 15;           // 技能 ≥3
  else if (userSkills.value.length > 0) score += 5;
  if (profileForm.value.github_url) score += 10;           // GitHub
  if (profileForm.value.position)  score += 5;             // 目标职位
  return Math.min(score, 100);
});
const completenessLabel = computed(() => {
  const s = resumeCompleteness.value;
  if (s >= 90) return { text: '非常完整', color: '#10b981' };
  if (s >= 70) return { text: '较为完整', color: '#3b82f6' };
  if (s >= 40) return { text: '基本完整', color: '#f59e0b' };
  return { text: '待完善', color: '#ef4444' };
});

// 收藏的岗位
const favoriteJobs = ref([] as Array<{
  id: string;
  title: string;
  company: string;
  salary_range: string;
  city: string;
  skills: string[];
}>);

// 匹配报告
const matchReports = ref([] as Array<{
  id: string;
  title: string;
  date: string;
  summary: string;
  matchRate: number;
}>);


// 技能添加相关
const newSkillInputVisible = ref(false);
const newSkillInput = ref('');
const newSkillInputRef = ref();

// 进度条颜色
const progressColor = '#3b82f6';

// 初始化数据
onMounted(async () => {
  await loadUserData();
});

// 加载用户数据
const loadUserData = async () => {
  try {
    // 加载个人资料
    loading.value.profile = true;
    const profileRes = await userApi.getProfile();
    if (profileRes.success) {
      const d = profileRes.data;
      profileForm.value = {
        ...profileForm.value,
        name:             d.name             || profileForm.value.name,
        email:            d.email            || profileForm.value.email,
        phone:            d.phone            || profileForm.value.phone,
        city:             d.city             || profileForm.value.city,
        position:         d.position         || profileForm.value.position,
        job_status:       d.job_status       || 'active',
        experience_years: d.experience_years ?? 0,
        school:           d.school           || '',
        major:            d.major            || '',
        degree:           d.degree           || '',
        github_url:       d.github_url       || '',
        linkedin_url:     d.linkedin_url     || '',
      };
    }
  } catch (error) {
    console.error('获取个人资料失败:', error);
  } finally {
    loading.value.profile = false;
  }

  try {
    // 加载简历信息
    loading.value.resume = true;
    const resumeRes = await userApi.getResume();
    if (resumeRes.success) {
      // 处理字段映射
      resumeForm.value = {
        ...resumeForm.value,
        name: resumeRes.data.name || resumeForm.value.name,
        school: resumeRes.data.school || resumeForm.value.school,
        major: resumeRes.data.major || resumeForm.value.major,
        degree: resumeRes.data.degree || resumeForm.value.degree,
        skills: resumeRes.data.skills || resumeForm.value.skills,
        expectCities: resumeRes.data.expect_cities || resumeForm.value.expectCities,
        expectSalary: resumeRes.data.expect_salary_min || resumeForm.value.expectSalary
      };
      // 加载简历全文（如后端支持则使用，否则从本地缓存恢复）
      if (resumeRes.data.raw_text) {
        resumeRawText.value = resumeRes.data.raw_text;
      } else {
        resumeRawText.value = localStorage.getItem('resume_raw_text') || '';
      }
    }
  } catch (error) {
    console.error('获取简历信息失败:', error);
  } finally {
    loading.value.resume = false;
  }

  try {
    // 加载用户技能
    loading.value.skills = true;
    const skillsRes = await userApi.getUserSkills();
    if (skillsRes.success && skillsRes.data) {
      const data = Array.isArray(skillsRes.data) ? skillsRes.data : [];
      userSkills.value = data.map((skill: any) => ({
        name: skill.skill_name,
        description: `熟练度: ${skill.proficiency_level || 1}/5 · 经验: ${skill.years_of_experience || 0}年`,
        level: skill.proficiency_level || 1
      }));
      // 写入技能名称缓存，供 JobSearch / Home 等页面读取匹配
      const skillNames = data.map((s: any) => s.skill_name).filter(Boolean);
      localStorage.setItem('uc_skills_cache', JSON.stringify(skillNames));
    }
  } catch (error) {
    console.error('获取用户技能失败（未登录或无数据）:', error);
  } finally {
    loading.value.skills = false;
  }

  try {
    // 加载收藏岗位
    loading.value.favorites = true;
    const favoritesRes = await userApi.getFavorites();
    if (favoritesRes.success) {
      favoriteJobs.value = favoritesRes.data;
    }
  } catch (error) {
    console.error('获取收藏岗位失败:', error);
  } finally {
    loading.value.favorites = false;
  }

  try {
    // 加载匹配报告
    loading.value.reports = true;
    const reportsRes = await userApi.getMatchReports();
    if (reportsRes.success) {
      // 处理字段映射
      matchReports.value = reportsRes.data.map((report: any) => ({
        id: report.id.toString(),
        title: report.report_title || report.title,
        date: report.created_at || report.date,
        summary: report.summary,
        matchRate: report.match_rate ? Math.round(Number(report.match_rate)) : report.matchRate
      }));
    }
  } catch (error) {
    console.error('获取匹配报告失败:', error);
  } finally {
    loading.value.reports = false;
  }

};

// 处理菜单选择
const handleMenuSelect = (index: string) => {
  activeMenu.value = index;
  // 根据菜单项加载相应数据
  switch (index) {
    case 'profile':
      if (profileForm.value.name === '') {
        loadUserData();
      }
      break;
    case 'resume':
      if (resumeForm.value.name === '') {
        loadUserData();
      }
      break;
    case 'skills':
      if (userSkills.value.length === 0) {
        loadUserData();
      }
      break;
    case 'favorites':
      if (favoriteJobs.value.length === 0) {
        loadUserData();
      }
      break;
    case 'reports':
      if (matchReports.value.length === 0) {
        loadUserData();
      }
      break;
  }
};

// 保存个人资料
const saveProfile = async () => {
  try {
    loading.value.profile = true;
    // 字段映射：前端字段名 -> 后端字段名
    const profileData = {
      name:             profileForm.value.name,
      email:            profileForm.value.email,
      phone:            profileForm.value.phone,
      city:             profileForm.value.city,
      position:         profileForm.value.position,
      job_status:       profileForm.value.job_status,
      experience_years: profileForm.value.experience_years,
      school:           profileForm.value.school,
      major:            profileForm.value.major,
      degree:           profileForm.value.degree,
      github_url:       profileForm.value.github_url,
      linkedin_url:     profileForm.value.linkedin_url,
    };
    const response = await userApi.updateProfile(profileData);
    if (response.success) {
      ElMessage.success('个人资料保存成功');
    } else {
      ElMessage.error(response.message || '保存失败');
    }
  } catch (error) {
    console.error('保存个人资料失败:', error);
    ElMessage.error('保存失败，请稍后重试');
  } finally {
    loading.value.profile = false;
  }
};

// 保存简历
const saveResume = async () => {
  try {
    loading.value.resume = true;
    const resumeData = {
      name: resumeForm.value.name,
      school: resumeForm.value.school,
      major: resumeForm.value.major,
      degree: resumeForm.value.degree,
      skills: resumeForm.value.skills,
      expect_cities: resumeForm.value.expectCities,
      expect_salary_min: resumeForm.value.expectSalary,
      expect_salary_max: resumeForm.value.expectSalary + 5,
      raw_text: resumeRawText.value  // 同时保存全文
    };
    // 始终将全文同步到本地缓存，确保离线也能恢复
    localStorage.setItem('resume_raw_text', resumeRawText.value);
    const response = await userApi.updateResume(resumeData);
    if (response.success) {
      ElMessage.success('简历保存成功');
    } else {
      ElMessage.error(response.message || '保存失败');
    }
  } catch (error) {
    console.error('保存简历失败:', error);
    // 后端失败时本地缓存已经成功，告知用户
    ElMessage.warning('已保存到本地缓存，后端同步失败请稍后重试');
  } finally {
    loading.value.resume = false;
  }
};

// ── 文件导入：触发选择框 ──────────────────────────────────────────────
const triggerFileInput = () => resumeFileInputRef.value?.click();

const handleFileDrop = (e: DragEvent) => {
  isDragOver.value = false;
  const file = e.dataTransfer?.files?.[0];
  if (file) parseResumeFile(file);
};

const handleFileChange = (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (file) parseResumeFile(file);
  // 清空 input，允许重复上传同名文件
  (e.target as HTMLInputElement).value = '';
};

// ── 文件解析核心：PDF / DOCX / TXT ──────────────────────────────────
const parseResumeFile = async (file: File) => {
  const ext = file.name.split('.').pop()?.toLowerCase();
  importLoading.value = true;
  try {
    let text = '';
    if (ext === 'txt') {
      text = await file.text();
    } else if (ext === 'pdf') {
      text = await parsePDF(file);
    } else if (ext === 'docx' || ext === 'doc') {
      text = await parseDOCX(file);
    } else {
      ElMessage.warning('不支持的文件格式，请上传 PDF、Word 或 TXT');
      return;
    }
    if (text.trim()) {
      resumeRawText.value = text.trim();
      ElMessage.success(`已成功解析 ${file.name}，请检查内容后保存`);
    } else {
      ElMessage.warning('文件内容为空或无法提取文字，请尝试其他格式');
    }
  } catch (err: any) {
    console.error('文件解析失败:', err);
    const msg = err?.message || '';
    if (msg.includes('password') || msg.includes('Password')) {
      ElMessage.error('PDF 已加密，请先去除密码保护后再上传');
    } else if (msg.includes('Invalid') || msg.includes('corrupt')) {
      ElMessage.error('PDF 文件损坏，请尝试重新导出后上传');
    } else {
      ElMessage.error('文件解析失败，请确认文件格式正确（推荐使用导出的 PDF 或 .docx）');
    }
  } finally {
    importLoading.value = false;
  }
};

const parsePDF = async (file: File): Promise<string> => {
  const pdfjsLib = await import('pdfjs-dist');
  // 使用本地 worker（pdfjs-dist v5+ 需要 .mjs 扩展名，CDN 可能无此版本）
  pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
    'pdfjs-dist/build/pdf.worker.min.mjs',
    import.meta.url
  ).href;
  const buffer = await file.arrayBuffer();
  const pdf = await pdfjsLib.getDocument({ data: buffer }).promise;
  const pages: string[] = [];
  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);
    const content = await page.getTextContent();
    const pageText = content.items
      .map((item: any) => ('str' in item ? item.str : ''))
      .join(' ');
    pages.push(pageText);
  }
  return pages.join('\n');
};

const parseDOCX = async (file: File): Promise<string> => {
  const mammoth = await import('mammoth');
  const buffer = await file.arrayBuffer();
  const result = await mammoth.extractRawText({ arrayBuffer: buffer });
  return result.value;
};

// ── AI 分析简历 ──────────────────────────────────────────────────────
const analyzeResume = async () => {
  const text = resumeRawText.value.trim();
  if (!text) {
    ElMessage.warning('请先填写简历全文或导入简历文件');
    return;
  }
  aiResumeMode.value = 'analyze';
  aiResumeLoading.value = true;
  aiResumeResult.value = '';
  try {
    const prompt = `你是一位专业的HR顾问和职业规划师，请对以下简历进行深度分析，给出以下几个方面的评估（使用 Markdown 格式，层次清晰）：

## 📋 简历内容
${text.slice(0, 3000)}

请从以下维度分析：
1. **整体评分**（满分100，给出分数及理由）
2. **亮点与优势**（具体列举）
3. **不足与待改进**（具体指出问题）
4. **IT/AI行业匹配度**（与当前市场需求对比）
5. **关键技能评估**（技术栈完整性和深度）
6. **改进建议**（3-5条可执行的具体建议）

请给出专业、客观、有针对性的分析。`;
    const res = await jobApi.chat({ message: prompt, session_id: `resume_analyze_${Date.now()}` });
    aiResumeResult.value = res.data?.response || res.data?.data?.response || '暂无回复';
  } catch {
    aiResumeResult.value = '⚠️ AI 服务暂时不可用，请稍后重试';
  } finally {
    aiResumeLoading.value = false;
  }
};

// ── AI 优化简历 ──────────────────────────────────────────────────────
const optimizeResume = async () => {
  const text = resumeRawText.value.trim();
  if (!text) {
    ElMessage.warning('请先填写简历全文或导入简历文件');
    return;
  }
  aiResumeMode.value = 'optimize';
  aiResumeLoading.value = true;
  aiResumeResult.value = '';
  try {
    const prompt = `你是一位专业的简历优化顾问，擅长 IT/AI 领域的求职简历撰写。请对以下简历进行优化改写，要求：
1. 保留原有真实信息，不捏造经历
2. 使用 STAR 法则（情境-任务-行动-结果）描述项目和工作经历
3. 突出量化成果（用数字体现影响力）
4. 强化技术关键词，提高 ATS 系统匹配率
5. 语言简洁有力，逻辑清晰
6. 输出完整的优化版简历文本（Markdown 格式）

## 原简历内容
${text.slice(0, 3000)}

请直接输出优化后的完整简历，并在末尾附上【优化说明】说明主要改动点。`;
    const res = await jobApi.chat({ message: prompt, session_id: `resume_optimize_${Date.now()}` });
    aiResumeResult.value = res.data?.response || res.data?.data?.response || '暂无回复';
  } catch {
    aiResumeResult.value = '⚠️ AI 服务暂时不可用，请稍后重试';
  } finally {
    aiResumeLoading.value = false;
  }
};

// 分析技能 - 跳转到匹配看板
const analyzeSkills = async () => {
  const skillNames = userSkills.value.map(s => s.name).join(', ');
  window.location.href = `/match?skills=${encodeURIComponent(skillNames)}`;
};

// ---- AI 技能档案诊断 ----
const aiDiagnoseLoading = ref(false);
const aiDiagnoseResult = ref('');

const renderDiagnose = (text: string) => _renderMd(text);

const diagnoseSkills = async () => {
  if (userSkills.value.length === 0) {
    ElMessage.warning('请先在下方添加你的技能后再诊断');
    return;
  }
  aiDiagnoseLoading.value = true;
  aiDiagnoseResult.value = '';
  try {
    const prompt = buildDiagnosisPrompt({
      skills: userSkills.value.map(s => ({ name: s.name, level: s.level })),
      expectCities: userProfile.value.expectCities,
      expectSalary: userProfile.value.expectSalary
    });
    const res = await jobApi.chat({ message: prompt, session_id: `diagnose_${Date.now()}` });
    aiDiagnoseResult.value = res.data?.response || res.data?.data?.response || '暂无回复';
  } catch {
    aiDiagnoseResult.value = '⚠️ AI 服务暂时不可用，请稍后重试';
  } finally {
    aiDiagnoseLoading.value = false;
  }
};


// 显示新技能输入框
const showNewSkillInput = () => {
  newSkillInputVisible.value = true;
  nextTick(() => {
    if (newSkillInputRef.value) {
      // @ts-ignore
      newSkillInputRef.value.focus();
    }
  });
};

// 添加新技能
const addNewSkill = () => {
  if (newSkillInput.value.trim() && !resumeForm.value.skills.includes(newSkillInput.value.trim())) {
    resumeForm.value.skills.push(newSkillInput.value.trim());
    newSkillInputVisible.value = false;
    newSkillInput.value = '';
  } else {
    newSkillInputVisible.value = false;
    newSkillInput.value = '';
  }
};

// 移除技能
const removeSkill = (index: number) => {
  resumeForm.value.skills.splice(index, 1);
};

// 取消收藏岗位
const unfavoriteJob = async (jobId: string) => {
  try {
    const response = await userApi.removeFavorite(jobId);
    if (response.success || response.message === '收藏已取消') {
      favoriteJobs.value = favoriteJobs.value.filter(job => job.id !== jobId);
      ElMessage.success('已取消收藏');
    } else {
      ElMessage.error(response.message || '取消收藏失败');
    }
  } catch (error) {
    console.error('取消收藏失败:', error);
    ElMessage.error('取消收藏失败，请稍后重试');
  }
};

// 格式化薪资显示
const formatSalary = (value: number) => {
  return `${value}K`;
};
</script>

<style scoped lang="scss">
.user-center {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;

  .user-header {
    margin-bottom: 20px;
    padding: 30px;

    .user-info {
      display: flex;
      align-items: center;
      gap: 24px;

      .avatar {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        background: linear-gradient(135deg, $primary-color 0%, #60a5fa 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 32px;
        color: white;
      }

      .user-details {
        flex: 1;

        .username {
          font-size: 1.5rem;
          font-weight: 600;
          color: $text-primary;
          margin: 0 0 8px;
        }

        .user-desc {
          color: $text-secondary;
          margin: 0 0 16px;
        }

        .user-stats {
          display: flex;
          gap: 24px;

          .stat-item {
            text-align: center;

            .stat-number {
              display: block;
              font-size: 1.5rem;
              font-weight: bold;
              color: $primary-color;
            }

            .stat-label {
              display: block;
              font-size: 0.8rem;
              color: $text-secondary;
            }
          }
        }
      }
    }
  }

  .user-center-main {
    display: flex;
    gap: 20px;

    .sidebar {
      width: 220px;

      .user-menu {
        background: transparent;
        border: none;

        :deep(.el-menu-item) {
          color: $text-regular;
          margin: 4px 0;
          border-radius: 8px;
          transition: $transition-base;

          &.is-active {
            background: rgba($primary-color, 0.2);
            color: $primary-color;
            font-weight: 500;
          }

          .el-icon {
            color: $text-secondary;
            margin-right: 8px;
          }

          &:hover {
            background: rgba(255, 255, 255, 0.05);
          }
        }
      }
    }

    .content {
      flex: 1;

      .form-card, .skills-card, .favorites-card, .reports-card {
        padding: 24px;
        margin-bottom: 20px;

        .card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
          flex-wrap: wrap;
          gap: 10px;

          .card-title {
            margin: 0;
            font-size: 1.2rem;
            color: $text-primary;
          }

          .card-header-btns {
            display: flex;
            align-items: center;
            gap: 10px;

            .ai-diagnose-btn {
              display: flex;
              align-items: center;
              gap: 6px;
              padding: 7px 16px;
              border-radius: 20px;
              border: 1px solid rgba(234,179,8,0.35);
              background: rgba(234,179,8,0.07);
              color: #fde047;
              font-size: 13px;
              font-weight: 600;
              cursor: pointer;
              transition: all 0.2s;
              white-space: nowrap;

              &:hover:not(:disabled) {
                background: rgba(234,179,8,0.15);
                border-color: rgba(234,179,8,0.6);
                box-shadow: 0 0 12px rgba(234,179,8,0.18);
              }
              &:disabled { opacity: 0.55; cursor: default; }

              .diag-spin {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                border: 2px solid #fde047;
                border-top-color: transparent;
                animation: spin-diag 0.8s linear infinite;
              }
            }
          }
        }

        // AI 诊断结果面板
        .ai-diagnose-panel {
          margin-bottom: 20px;
          border-radius: 12px;
          background: rgba(234,179,8,0.05);
          border: 1px solid rgba(234,179,8,0.2);
          overflow: hidden;

          .diagnose-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 16px;
            background: rgba(234,179,8,0.08);
            border-bottom: 1px solid rgba(234,179,8,0.12);

            .diagnose-label {
              font-size: 12px;
              color: #fde047;
              font-weight: 700;
              letter-spacing: 0.3px;
            }
            .diagnose-close {
              background: none;
              border: none;
              color: rgba(255,255,255,0.4);
              cursor: pointer;
              font-size: 13px;
              padding: 2px 6px;
              border-radius: 4px;
              &:hover { color: #fff; background: rgba(255,255,255,0.08); }
            }
          }

          .diagnose-skeleton {
            padding: 16px 18px;
            display: flex;
            flex-direction: column;
            gap: 10px;

            .sk {
              height: 13px;
              border-radius: 6px;
              background: linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.09) 50%, rgba(255,255,255,0.04) 75%);
              background-size: 200% 100%;
              animation: shimmer-diag 1.5s infinite;
              &.w80 { width: 80%; }
              &.w60 { width: 60%; }
              &.w90 { width: 90%; }
              &.w50 { width: 50%; }
              &.w75 { width: 75%; }
            }
          }

          .diagnose-content {
            padding: 16px 18px;
            font-size: 13.5px;
            color: $text-primary;
            line-height: 1.8;
            opacity: 0.92;

            :deep(.dh3) { font-size: 14px; font-weight: 700; color: #fde047; margin: 10px 0 5px; }
            :deep(.dh4) { font-size: 13.5px; font-weight: 600; color: #fcd34d; margin: 8px 0 4px; }
            :deep(strong) { color: #fde047; }
            :deep(code) {
              background: rgba(234,179,8,0.12);
              color: #fde047;
              padding: 1px 6px;
              border-radius: 4px;
              font-size: 12.5px;
            }
            :deep(li) {
              list-style: none;
              padding-left: 16px;
              position: relative;
              margin: 3px 0;
              &::before { content: '▸'; position: absolute; left: 0; color: #fbbf24; font-size: 11px; }
              &.ol::before { content: none; }
              .on {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 18px;
                height: 18px;
                border-radius: 50%;
                background: rgba(234,179,8,0.15);
                color: #fde047;
                font-size: 11px;
                font-weight: 700;
                margin-right: 6px;
              }
            }
          }
        }

        .card-title {
          margin: 0 0 20px;
          font-size: 1.2rem;
          color: $text-primary;
        }

        .profile-form {
          max-width: 600px;
        }


        .skills-chips {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          align-items: center;

          .new-skill-input {
            width: 120px;
          }

          .add-skill-btn {
            background: $bg-secondary;
            border: 1px dashed $border-color;
            color: $text-placeholder;
            padding: 8px 12px;
            border-radius: 6px;

            &:hover {
              border-color: $primary-color;
              color: $primary-color;
              background: rgba($primary-color, 0.1);
            }
          }
        }

        .skills-list {
          .skill-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 0;
            border-bottom: 1px solid $border-color;

            &:last-child {
              border-bottom: none;
            }

            .skill-info {
              flex: 1;

              h4 {
                margin: 0 0 4px;
                color: $text-primary;
              }

              p {
                margin: 0;
                color: $text-regular;
                font-size: 0.9rem;
              }
            }

            .skill-level {
              width: 200px;
            }
          }
        }

        .jobs-list {
          .job-item {
            margin-bottom: 16px;
            padding: 16px;

            .job-header {
              display: flex;
              justify-content: space-between;
              align-items: center;
              margin-bottom: 12px;

              .job-title {
                margin: 0;
                font-size: 1.1rem;
                color: $text-primary;
              }
            }

            .job-meta {
              display: flex;
              gap: 16px;
              margin-bottom: 12px;
              font-size: 0.9rem;
              color: $text-regular;

              .company {
                color: $text-primary;
              }

              .salary {
                color: $success-color;
                font-weight: 500;
              }
            }

            .job-skills {
              display: flex;
              flex-wrap: wrap;
              gap: 6px;
            }
          }
        }

        .reports-list {
          .report-item {
            margin-bottom: 16px;
            padding: 16px;

            .report-header {
              display: flex;
              justify-content: space-between;
              align-items: center;
              margin-bottom: 8px;

              h4 {
                margin: 0;
                color: $text-primary;
              }

              .report-date {
                color: $text-placeholder;
                font-size: 0.8rem;
              }
            }

            .report-summary {
              margin-bottom: 12px;
              color: $text-regular;
            }

            .report-metrics {
              margin-bottom: 12px;

              .metric {
                margin-bottom: 8px;

                .metric-label {
                  display: block;
                  font-size: 0.9rem;
                  color: $text-secondary;
                  margin-bottom: 4px;
                }
              }
            }

            .report-actions {
              text-align: right;
            }
          }
        }
      }
    }
  }
}

@keyframes spin-diag {
  to { transform: rotate(360deg); }
}
@keyframes shimmer-diag {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@media (max-width: 768px) {
  .user-center-main {
    flex-direction: column;

    .sidebar {
      width: 100%;
      margin-bottom: 20px;
    }
  }

  .user-info {
    flex-direction: column !important;
    text-align: center !important;
  }
}
</style>

<!-- 简历模块独立样式，放在非 scoped 块确保生效 -->
<style lang="scss">
@keyframes rc-spin { to { transform: rotate(360deg); } }
@keyframes rc-shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

// 卡片容器
.resume-card {
  padding: 28px !important;
  display: flex !important;
  flex-direction: column !important;
  gap: 20px !important;
}

// ① 标题栏
.rc-header {
  display: flex !important;
  align-items: center;
  justify-content: space-between;
}
.rc-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.rc-header-icon.el-icon { font-size: 20px; color: #3b82f6; }
.rc-header-title { font-size: 18px; font-weight: 700; color: #fff; }

// ② 上传区
.rc-dropzone {
  display: flex !important;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 110px !important;
  border: 1.5px dashed rgba(59,130,246,0.35) !important;
  border-radius: 12px !important;
  background: rgba(59,130,246,0.04) !important;
  cursor: pointer;
  transition: all 0.22s;
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute; inset: 0;
    background: radial-gradient(ellipse at center, rgba(59,130,246,0.08) 0%, transparent 70%);
    opacity: 0; transition: opacity 0.3s;
  }
  &:hover, &.is-over {
    border-color: rgba(59,130,246,0.65) !important;
    background: rgba(59,130,246,0.09) !important;
    &::before { opacity: 1; }
  }
  &.is-parsing { pointer-events: none; }

  .dz-up-icon.el-icon { font-size: 28px !important; color: rgba(59,130,246,0.75) !important; }
  .dz-main-text { font-size: 14px; font-weight: 600; color: #cbd5e1; }
  .dz-sub-text   { font-size: 12px; color: #64748b; }
  .dz-spin {
    width: 24px; height: 24px;
    border: 2.5px solid rgba(59,130,246,0.2);
    border-top-color: #3b82f6; border-radius: 50%;
    animation: rc-spin 0.8s linear infinite;
  }
  .dz-hint { font-size: 13px; color: #94a3b8; }
}

// ③ AI 按钮行
.rc-ai-row {
  display: flex !important;
  gap: 12px;
}
.rc-ai-btn {
  flex: 1;
  display: flex !important;
  align-items: center;
  gap: 14px;
  padding: 16px 20px !important;
  border-radius: 12px !important;
  border: 1px solid transparent !important;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
  background: none;

  .el-icon { font-size: 22px !important; flex-shrink: 0; }

  .rc-spin {
    width: 18px; height: 18px; flex-shrink: 0;
    border: 2px solid rgba(255,255,255,0.15);
    border-top-color: currentColor; border-radius: 50%;
    animation: rc-spin 0.8s linear infinite;
  }

  .rc-ai-btn-text {
    display: flex;
    flex-direction: column;
    gap: 4px;
    strong { font-size: 14px; font-weight: 700; display: block; line-height: 1.2; }
    small  { font-size: 11px; opacity: 0.7; display: block; line-height: 1.2; }
  }

  &:disabled { opacity: 0.4; cursor: not-allowed; }

  &.rc-ai-btn--analyze {
    background: rgba(59,130,246,0.08) !important;
    border-color: rgba(59,130,246,0.22) !important;
    color: #60a5fa !important;
    &:hover:not(:disabled) {
      background: rgba(59,130,246,0.16) !important;
      border-color: rgba(59,130,246,0.5) !important;
      box-shadow: 0 4px 20px rgba(59,130,246,0.18);
      transform: translateY(-1px);
    }
  }
  &.rc-ai-btn--optimize {
    background: rgba(139,92,246,0.08) !important;
    border-color: rgba(139,92,246,0.22) !important;
    color: #a78bfa !important;
    &:hover:not(:disabled) {
      background: rgba(139,92,246,0.16) !important;
      border-color: rgba(139,92,246,0.5) !important;
      box-shadow: 0 4px 20px rgba(139,92,246,0.18);
      transform: translateY(-1px);
    }
  }
}

// ④ AI 结果面板
.rc-ai-result {
  border: 1px solid rgba(59,130,246,0.2);
  border-radius: 10px; overflow: hidden;
  background: rgba(59,130,246,0.04);

  .rc-result-bar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 11px 16px;
    background: rgba(59,130,246,0.08);
    border-bottom: 1px solid rgba(59,130,246,0.12);

    .rc-result-bar-left {
      display: flex; align-items: center; gap: 8px;
      font-size: 13px; font-weight: 700; color: #fff;
      .el-icon { font-size: 14px; color: #60a5fa; }
      .rc-badge {
        font-size: 10px; padding: 1px 7px; border-radius: 20px;
        background: rgba(59,130,246,0.18); border: 1px solid rgba(59,130,246,0.35);
        color: #60a5fa; font-weight: 700;
      }
    }
    .rc-result-close {
      background: none; border: none; cursor: pointer;
      color: #64748b; font-size: 13px; width: 22px; height: 22px;
      border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      transition: all 0.2s;
      &:hover { background: rgba(255,255,255,0.1); color: #fff; }
    }
  }

  .rc-skeleton {
    padding: 18px 20px; display: flex; flex-direction: column; gap: 10px;
    .sk {
      height: 11px; border-radius: 5px;
      background: linear-gradient(90deg,
        rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.09) 50%, rgba(255,255,255,0.04) 75%);
      background-size: 200% 100%;
      animation: rc-shimmer 1.5s infinite;
    }
  }

  .rc-result-body {
    padding: 16px 20px; font-size: 14px; line-height: 1.85;
    color: #94a3b8; max-height: 480px; overflow-y: auto;
    &::-webkit-scrollbar { width: 3px; }
    &::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }
    h2, h3 { color: #fff; font-size: 14px; margin: 12px 0 5px; font-weight: 700; }
    strong  { color: #cbd5e1; }
    ul, ol  { padding-left: 16px; }
    li      { margin: 3px 0; }
    code    { background: rgba(59,130,246,0.1); border-radius: 3px; padding: 1px 5px; font-size: 12px; color: #60a5fa; }
  }
}

// ⑤ 全文编辑器
.rc-editor {
  border: 1px solid rgba(255,255,255,0.09) !important;
  border-radius: 10px !important;
  overflow: hidden;

  .rc-editor-bar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 10px 14px;
    background: rgba(255,255,255,0.03);
    border-bottom: 1px solid rgba(255,255,255,0.07);
    .rc-editor-bar-left {
      display: flex; align-items: center; gap: 7px;
      font-size: 13px; font-weight: 600; color: #cbd5e1;
      .el-icon { font-size: 14px; color: #3b82f6; }
    }
    .rc-wordcount { font-size: 12px; color: #64748b; }
  }

  .rc-textarea {
    width: 100% !important; box-sizing: border-box !important;
    padding: 14px 16px !important;
    background: transparent !important;
    border: none !important; outline: none !important;
    color: #fff !important; font-size: 13px; line-height: 1.9;
    font-family: 'Consolas', 'SF Mono', 'Fira Code', monospace;
    resize: vertical; min-height: 260px !important;
    display: block !important;
    &::placeholder { color: rgba(100,116,139,0.55); font-family: sans-serif; font-size: 12.5px; }
    &::-webkit-scrollbar { width: 3px; }
    &::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 2px; }
  }
}

// ⑥ 求职偏好折叠
.rc-prefs {
  border: 1px solid rgba(255,255,255,0.08) !important;
  border-radius: 10px !important; overflow: hidden;

  .rc-prefs-toggle {
    display: flex !important; align-items: center;
    justify-content: space-between;
    padding: 12px 16px; cursor: pointer; user-select: none;
    background: rgba(255,255,255,0.02);
    transition: background 0.2s;
    &:hover { background: rgba(59,130,246,0.06); }

    .rc-prefs-toggle-left {
      display: flex; align-items: center; gap: 8px;
      font-size: 13px; font-weight: 600; color: #cbd5e1;
      .el-icon { font-size: 14px; color: #64748b; }
      small { font-size: 12px; color: #64748b; font-weight: 400; }
    }
    .rc-chevron {
      font-size: 13px; color: #64748b; transition: transform 0.25s;
      &.is-open { transform: rotate(180deg); }
    }
  }

  .rc-prefs-body {
    padding: 18px 16px; display: flex; flex-direction: column; gap: 16px;
    border-top: 1px solid rgba(255,255,255,0.07);

    .pref-row { display: flex; flex-direction: column; gap: 8px; }
    .pref-label {
      font-size: 11px; font-weight: 600; color: #64748b;
      text-transform: uppercase; letter-spacing: 0.5px;
    }
    .pref-salary-row {
      display: flex; align-items: center; gap: 14px;
      .salary-val { font-size: 14px; font-weight: 700; color: #3b82f6; flex-shrink: 0; min-width: 60px; }
      .rc-slider { flex: 1; }
    }
    .city-chips {
      display: flex; flex-wrap: wrap; gap: 8px;
      .city-chip {
        padding: 5px 14px; border-radius: 20px; cursor: pointer;
        font-size: 13px; font-weight: 500;
        border: 1px solid rgba(255,255,255,0.1);
        background: rgba(255,255,255,0.04);
        color: #94a3b8; transition: all 0.18s;
        &.active {
          border-color: rgba(59,130,246,0.55);
          background: rgba(59,130,246,0.14);
          color: #60a5fa;
        }
        &:hover:not(.active) { border-color: rgba(255,255,255,0.22); color: #cbd5e1; }
      }
    }
  }
}

// ── el-form 暗色主题全局覆盖（解决白色背景问题）──────────────────────
.el-input__wrapper {
  background-color: #151932 !important;
  box-shadow: 0 0 0 1px rgba(255,255,255,0.1) inset !important;
}
.el-input__wrapper.is-focus {
  box-shadow: 0 0 0 1px #3b82f6 inset !important;
}
.el-input__inner {
  color: #fff !important;
  background: transparent !important;
}
.el-input__prefix-inner .el-icon { color: #64748b !important; }
.el-select__wrapper {
  background-color: #151932 !important;
  box-shadow: 0 0 0 1px rgba(255,255,255,0.1) inset !important;
  color: #fff !important;
}
.el-select__wrapper.is-focused {
  box-shadow: 0 0 0 1px #3b82f6 inset !important;
}
.el-select__selected-item { color: #fff !important; }
.el-select__placeholder { color: #64748b !important; }
.el-select-dropdown__wrap { background: #151932 !important; }
.el-select-dropdown__item {
  color: #94a3b8 !important;
  &.is-hovering, &:hover { background: rgba(59,130,246,0.1) !important; color: #60a5fa !important; }
  &.is-selected { color: #3b82f6 !important; font-weight: 700 !important; }
}
.el-form-item__label { color: #94a3b8 !important; font-size: 13px !important; }
.el-rate__icon { color: rgba(255,255,255,0.15) !important; }
.el-rate__icon.is-active { color: #f59e0b !important; }

// ── 个人资料：分区标题 ──────────────────────────────────────────────
.form-section-title {
  font-size: 11px; font-weight: 700; color: #3b82f6;
  text-transform: uppercase; letter-spacing: 0.8px;
  padding: 14px 0 6px;
  border-bottom: 1px solid rgba(59,130,246,0.15);
  margin-bottom: 14px;
}

// 求职状态徽章
.job-status-badge {
  display: inline-flex; align-items: center;
  padding: 4px 12px; border-radius: 20px;
  font-size: 12px; font-weight: 600;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.05);
  color: #94a3b8;

  &.active   { border-color: rgba(16,185,129,0.4); background: rgba(16,185,129,0.1); color: #34d399; }
  &.open     { border-color: rgba(59,130,246,0.4); background: rgba(59,130,246,0.1); color: #60a5fa; }
  &.inactive { border-color: rgba(100,116,139,0.3); background: rgba(100,116,139,0.07); color: #64748b; }
}

// ── 城市 chips：可滚动区域 ──────────────────────────────────────────
.city-chips--scroll {
  max-height: 130px !important;
  overflow-y: auto !important;
  padding: 2px 0 !important;
  &::-webkit-scrollbar { width: 3px; }
  &::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }
}
.pref-label-row {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 8px;
}
.pref-selected-count { font-size: 11px; color: #3b82f6; font-weight: 600; }

// ── 简历完整度进度条 ────────────────────────────────────────────────
.rc-completeness {
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 10px;
  padding: 14px 18px;

  .rc-comp-top {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 10px;
  }
  .rc-comp-label { font-size: 12px; font-weight: 600; color: #94a3b8; }
  .rc-comp-pct   { font-size: 13px; font-weight: 700; }

  .rc-comp-bar {
    width: 100%; height: 6px;
    background: rgba(255,255,255,0.07);
    border-radius: 3px; overflow: hidden;
  }
  .rc-comp-fill {
    height: 100%; border-radius: 3px;
    transition: width 0.6s cubic-bezier(0.4,0,0.2,1);
  }

  .rc-comp-tips {
    display: flex; flex-wrap: wrap; gap: 8px;
    margin-top: 10px;
    span {
      font-size: 11px; color: #64748b;
      background: rgba(255,255,255,0.03);
      border: 1px solid rgba(255,255,255,0.07);
      border-radius: 20px; padding: 2px 10px;
    }
  }
}

// ── 收藏岗位：新版卡片 ──────────────────────────────────────────────
.card-count {
  font-size: 12px; color: #64748b;
  background: rgba(255,255,255,0.05);
  padding: 3px 10px; border-radius: 20px;
  border: 1px solid rgba(255,255,255,0.08);
}

.empty-state {
  display: flex; flex-direction: column; align-items: center;
  padding: 48px 20px; color: #475569;
  .empty-icon { font-size: 40px; margin-bottom: 12px; color: #334155; }
  p   { font-size: 15px; font-weight: 600; margin: 0 0 6px; }
  small { font-size: 13px; }
}

.jobs-list { display: flex; flex-direction: column; gap: 10px; margin-top: 4px; }

.job-item {
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.07);
  background: rgba(255,255,255,0.025);
  padding: 14px 16px;
  display: flex; flex-direction: column; gap: 10px;
  transition: background 0.2s, border-color 0.2s;

  &:hover { background: rgba(255,255,255,0.045); border-color: rgba(255,255,255,0.12); }

  .job-header {
    display: flex; align-items: flex-start; justify-content: space-between; gap: 12px;
  }
  .job-header-left { flex: 1; min-width: 0; }
  .job-title {
    font-size: 15px; font-weight: 700; color: #e2e8f0;
    margin: 0 0 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .job-meta {
    display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
    font-size: 13px; color: #64748b;
    .company { color: #94a3b8; font-weight: 500; }
    .salary  { color: #34d399; font-weight: 600; }
    .dot     { color: #334155; }
  }

  .unfav-btn {
    background: none; border: 1px solid rgba(239,68,68,0.2);
    border-radius: 6px; color: #64748b; font-size: 12px;
    width: 28px; height: 28px; flex-shrink: 0; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: all 0.18s;
    &:hover { background: rgba(239,68,68,0.1); border-color: rgba(239,68,68,0.5); color: #ef4444; }
  }

  .job-skills { display: flex; flex-wrap: wrap; gap: 6px; }
}

// el-slider 暗色覆盖（仅在 resume 区域）
.rc-slider {
  .el-slider__runway {
    background-color: rgba(255,255,255,0.1) !important;
    height: 4px !important;
  }
  .el-slider__bar {
    background: linear-gradient(90deg, #3b82f6, #60a5fa) !important;
    height: 4px !important;
  }
  .el-slider__button {
    width: 14px !important; height: 14px !important;
    border-color: #3b82f6 !important;
    background: #1e3a5f !important;
    box-shadow: 0 0 6px rgba(59,130,246,0.45) !important;
  }
  .el-slider__marks-text { color: #64748b !important; font-size: 11px !important; }
}

// 折叠过渡
.rc-fold-enter-active, .rc-fold-leave-active { transition: all 0.28s ease; overflow: hidden; }
.rc-fold-enter-from, .rc-fold-leave-to { opacity: 0; max-height: 0; }
.rc-fold-enter-to, .rc-fold-leave-from { opacity: 1; max-height: 600px; }
.rc-slide-enter-active, .rc-slide-leave-active { transition: all 0.25s ease; }
.rc-slide-enter-from, .rc-slide-leave-to { opacity: 0; transform: translateY(-8px); }
</style>