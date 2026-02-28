<template>
  <div class="match-dashboard">

    <!-- ① 输入区：技能 + 目标岗位 + 分析按钮 -->
    <GlassCard class="setup-card">
      <div class="setup-title">
        <el-icon class="title-icon"><Medal /></el-icon>
        <div>
          <h1>技能 · 岗位匹配分析</h1>
          <p>输入你的技能和目标岗位，AI 帮你找差距、定学习路径</p>
        </div>
      </div>

      <div class="setup-body">
        <!-- 技能区 -->
        <div class="setup-section">
          <div class="section-label">
            <span class="label-num">1</span>
            <span>技能来源</span>
          </div>

          <!-- 输入源 Tab -->
          <div class="source-tabs">
            <button
              :class="['src-tab', { active: inputMode === 'manual' }]"
              @click="inputMode = 'manual'"
            >✏️ 手动输入</button>
            <button
              :class="['src-tab', { active: inputMode === 'resume' }]"
              @click="inputMode = 'resume'"
            >
              📄 从简历提取
              <span v-if="savedResumeText" class="src-tab-dot"></span>
            </button>
          </div>

          <!-- ── 手动输入模式 ── -->
          <template v-if="inputMode === 'manual'">
            <div class="import-row" v-if="hasProfile">
              <button class="import-btn" @click="importFromProfile">
                <el-icon><User /></el-icon>从档案导入
              </button>
            </div>
            <!-- Tag 输入框 -->
            <div class="tag-input-area" @click="focusSkillInput">
              <span v-for="(tag, i) in skillTags" :key="tag" class="skill-tag-chip">
                {{ tag }}
                <button class="tag-remove" @click.stop="removeTag(i)">×</button>
              </span>
              <input
                ref="skillInputRef"
                v-model="skillInputVal"
                class="tag-input"
                placeholder="输入技能，按 Enter 或逗号添加..."
                @keydown.enter.prevent="addTag"
                @keydown.188.prevent="addTag"
                @keydown.delete="deleteLastTag"
                @input="onSkillInput"
              />
            </div>
            <div v-if="skillSuggestions.length > 0" class="skill-suggestions">
              <button v-for="s in skillSuggestions" :key="s" class="suggestion-chip" @click="addTagDirect(s)">+ {{ s }}</button>
            </div>
            <!-- 快捷标签：始终显示，已选中的高亮 -->
            <div class="quick-tags">
              <span class="quick-label">常用：</span>
              <button
                v-for="t in quickSkills"
                :key="t"
                :class="['quick-chip', { 'quick-chip--selected': skillTags.includes(t) }]"
                @click="toggleSkill(t)"
              >
                <span v-if="skillTags.includes(t)" class="qc-check">✓</span>{{ t }}
              </button>
            </div>

            <!-- 技能浏览器展开按钮 -->
            <button class="browser-toggle-btn" @click="showSkillBrowser = !showSkillBrowser">
              <span>📋</span>
              浏览全部技能
              <span class="btb-count">{{ appStore.skillsList.length || '...' }}</span>
              <span class="btb-arrow">{{ showSkillBrowser ? '▲' : '▼' }}</span>
            </button>

            <!-- ── 技能浏览器面板 ── -->
            <div v-if="showSkillBrowser" class="skill-browser">
              <!-- 搜索栏 -->
              <div class="sb-search-bar">
                <input
                  v-model="skillBrowserSearch"
                  class="sb-search-input"
                  placeholder="搜索技能..."
                />
                <span class="sb-count">共 {{ filteredBrowserSkills.length }} 个</span>
              </div>

              <!-- 热门技能 -->
              <div class="sb-hot-section">
                <span class="sb-section-title">🔥 热门</span>
                <div class="sb-hot-chips">
                  <button
                    v-for="s in hotSkillsPreset"
                    :key="s"
                    :class="['sb-chip', { selected: skillTags.includes(s) }]"
                    @click="toggleSkill(s)"
                  >{{ s }}<span v-if="skillTags.includes(s)" class="sb-check">✓</span></button>
                </div>
              </div>

              <!-- 字母分组 + 索引 -->
              <div class="sb-body">
                <!-- 字母索引 -->
                <div class="sb-letter-index">
                  <button
                    v-for="letter in availableLetters"
                    :key="letter"
                    class="sb-letter-btn"
                    @click="scrollToLetter(letter)"
                  >{{ letter }}</button>
                </div>
                <!-- 技能列表 -->
                <div class="sb-list" ref="sbListRef">
                  <div
                    v-for="[letter, skills] in skillsGroupedByLetter"
                    :key="letter"
                    :id="`sb-letter-${letter}`"
                    class="sb-group"
                  >
                    <div class="sb-letter-header">{{ letter }}</div>
                    <div class="sb-group-skills">
                      <button
                        v-for="s in skills"
                        :key="s"
                        :class="['sb-skill-item', { selected: skillTags.includes(s) }]"
                        @click="toggleSkill(s)"
                      >{{ s }}</button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </template>

          <!-- ── 简历提取模式 ── -->
          <template v-else>
            <!-- 个人中心已保存的简历 -->
            <div v-if="savedResumeText" class="resume-source-card rsc-saved">
              <div class="rsc-header">
                <el-icon><Document /></el-icon>
                <span class="rsc-title">个人中心简历</span>
                <span class="rsc-len">{{ savedResumeText.length }} 字</span>
              </div>
              <div class="rsc-preview">{{ savedResumeText.slice(0, 160) }}…</div>
              <button
                class="extract-btn"
                :disabled="extracting"
                @click="extractSkillsFromResume(savedResumeText)"
              >
                <span v-if="extracting" class="ext-spin"></span>
                <span v-else>🤖</span>
                {{ extracting ? 'AI 提取中...' : 'AI 一键提取技能' }}
              </button>
            </div>
            <div v-else class="rsc-empty">
              <span>个人中心暂无简历，可上传文件或前往</span>
              <router-link to="/user-center" class="rsc-link">用户中心</router-link>
              <span>填写</span>
            </div>

            <!-- 文件上传区 -->
            <div
              class="resume-upload-zone"
              :class="{ uploading: resumeUploading }"
              @click="triggerResumeUpload"
              @dragover.prevent
              @drop.prevent="handleResumeDrop"
            >
              <input
                ref="resumeFileRef"
                type="file"
                accept=".pdf,.docx,.doc,.txt"
                style="display:none"
                @change="handleResumeFile"
              />
              <template v-if="resumeUploading">
                <span class="ruz-spin"></span>
                <span class="ruz-text">解析中...</span>
              </template>
              <template v-else>
                <el-icon class="ruz-icon"><Upload /></el-icon>
                <span class="ruz-text">拖放或点击上传简历</span>
                <span class="ruz-hint">支持 PDF · Word (.docx) · TXT</span>
              </template>
            </div>

            <!-- 已提取的技能 -->
            <div v-if="skillTags.length > 0" class="extracted-result">
              <div class="er-header">
                <span class="er-label">已提取 {{ skillTags.length }} 项技能</span>
                <button class="er-clear" @click="skillTags = []">清空</button>
              </div>
              <div class="tag-input-area tag-area-readonly">
                <span v-for="(tag, i) in skillTags" :key="tag" class="skill-tag-chip">
                  {{ tag }}
                  <button class="tag-remove" @click.stop="removeTag(i)">×</button>
                </span>
              </div>
            </div>
          </template>
        </div>

        <!-- 目标岗位区 -->
        <div class="setup-section">
          <div class="section-label">
            <span class="label-num">2</span>
            <span>目标岗位</span>
          </div>
          <input
            v-model="targetPosition"
            class="position-input"
            placeholder="如：Python后端工程师、Java架构师、前端开发..."
            @keydown.enter="analyzeMatch"
          />
          <div class="position-presets">
            <span class="quick-label">热门岗位：</span>
            <button
              v-for="p in popularPositions"
              :key="p"
              class="preset-chip"
              :class="{ active: targetPosition === p }"
              @click="targetPosition = p"
            >{{ p }}</button>
          </div>
        </div>

        <!-- 分析按钮 -->
        <div class="setup-action">
          <button
            class="analyze-btn"
            :class="{ loading: loading, ready: skillTags.length > 0 && targetPosition }"
            :disabled="loading"
            @click="analyzeMatch"
          >
            <span v-if="loading" class="btn-spin"></span>
            <el-icon v-else><MagicStick /></el-icon>
            {{ loading ? '分析中，请稍候...' : '开始匹配分析' }}
          </button>
          <span class="tech-hint">🧠 RAG 检索 · Neo4j 图谱推理 · Qwen3.5-Plus</span>
        </div>
      </div>
    </GlassCard>

    <!-- 分析前空状态 -->
    <div v-if="!matchAnalysis && !loading" class="empty-state">
      <div class="empty-icon">📊</div>
      <p class="empty-title">填写上方信息，点击「开始匹配分析」</p>
      <p class="empty-sub">系统将从知识图谱中检索 {{ targetPosition || '目标岗位' }} 的技能要求，与你的技能对比分析</p>
    </div>

    <!-- 加载中占位 -->
    <div v-if="loading" class="loading-state">
      <div class="loading-ring"></div>
      <p>正在从 Neo4j 图谱检索「{{ targetPosition }}」技能要求...</p>
    </div>

    <!-- ② 结果区：仅在有结果时显示 -->
    <template v-if="matchAnalysis">

      <!-- 结果摘要横幅 -->
      <GlassCard class="result-banner">
        <div class="banner-left">
          <div class="match-ring" :class="matchRateClass">
            <svg viewBox="0 0 64 64" class="ring-svg">
              <circle cx="32" cy="32" r="26" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="6"/>
              <circle cx="32" cy="32" r="26" fill="none" :stroke="matchRingColor" stroke-width="6"
                stroke-linecap="round" stroke-dasharray="163.36"
                :stroke-dashoffset="163.36 * (1 - matchAnalysis.matchRate)"
                transform="rotate(-90 32 32)"/>
            </svg>
            <div class="ring-text">
              <span class="ring-pct">{{ Math.round(matchAnalysis.matchRate * 100) }}%</span>
              <span class="ring-label">匹配</span>
            </div>
          </div>
          <div class="banner-info">
            <div class="banner-position">{{ matchAnalysis.targetPosition }}</div>
            <div class="banner-verdict" :class="matchRateClass">{{ matchVerdict }}</div>
          </div>
        </div>
        <div class="banner-stats">
          <div class="bstat">
            <div class="bstat-val bstat-green">{{ matchAnalysis.matchedSkills.length }}</div>
            <div class="bstat-label">已掌握</div>
          </div>
          <div class="bstat-div"></div>
          <div class="bstat">
            <div class="bstat-val bstat-red">{{ matchAnalysis.missingSkills.length }}</div>
            <div class="bstat-label">待补充</div>
          </div>
          <div class="bstat-div"></div>
          <div class="bstat">
            <div class="bstat-val bstat-blue">{{ matchAnalysis.matchedSkills.length + matchAnalysis.missingSkills.length }}</div>
            <div class="bstat-label">岗位要求</div>
          </div>
        </div>
        <div class="banner-action">
          <button class="re-analyze-btn" @click="resetAnalysis">重新分析</button>
          <button class="chat-bridge-btn" @click="bridgeToChat" title="将缺失技能和分析结果带入 AI 助手继续深聊">
            🤖 让 AI 帮我补齐缺口
          </button>
        </div>
      </GlassCard>

      <!-- 雷达图 + 差距分析 并排 -->
      <div class="two-col-row">
        <!-- 雷达图 -->
        <GlassCard class="radar-chart-panel">
          <h3 class="panel-title">📊 技能雷达图</h3>
          <div ref="radarChartRef" class="chart-container"></div>
        </GlassCard>

        <!-- 技能差距分析 -->
        <GlassCard class="gap-analysis-panel">
          <div class="panel-title-row">
            <h3 class="panel-title">🔍 技能差距</h3>
            <div class="rag-badge">
              <span class="rag-dot"></span>
              RAG · 图谱
            </div>
          </div>
          <div class="gap-info">
            <div class="gap-section">
              <h4 class="gap-sec-title">✅ 已掌握 <span class="cnt">{{ matchAnalysis.matchedSkills.length }}</span></h4>
              <div class="skills-list">
                <SkillTag v-for="skill in matchAnalysis.matchedSkills" :key="skill" :label="skill" level="primary"/>
              </div>
            </div>
            <div class="gap-section">
              <h4 class="gap-sec-title">❌ 待补充 <span class="cnt cnt-red">{{ matchAnalysis.missingSkills.length }}</span></h4>
              <div class="skills-list">
                <SkillTag v-for="skill in matchAnalysis.missingSkills" :key="skill" :label="skill" level="danger"/>
              </div>
            </div>
          </div>

          <div class="gap-ai-row">
            <button class="ai-interpret-btn" @click="generateAIInterpretation" :disabled="aiInterpretLoading">
              <span v-if="aiInterpretLoading" class="ai-plan-loading-dot"></span>
              <span v-else>🤖</span>
              {{ aiInterpretLoading ? 'AI 解读中...' : 'AI 解读，给出提升建议' }}
            </button>
          </div>
          <div v-if="aiInterpretResult || aiInterpretLoading" class="ai-interpret-panel">
            <div class="ai-panel-header">
              <span class="ai-badge">🤖 Qwen3.5-Plus · 匹配分析解读</span>
              <button v-if="aiInterpretResult" class="ai-close-btn" @click="aiInterpretResult = ''">✕</button>
            </div>
            <div v-if="aiInterpretLoading" class="ai-skeleton">
              <div class="skeleton-line w80"></div>
              <div class="skeleton-line w60"></div>
              <div class="skeleton-line w90"></div>
            </div>
            <div v-else class="ai-content" v-html="renderMarkdown(aiInterpretResult)"></div>
          </div>
        </GlassCard>
      </div>

      <!-- 学习路径 -->
      <GlassCard v-if="prioritizedPath.length > 0" class="learning-path-panel">
        <div class="path-header">
          <h3 class="panel-title">🚀 推荐学习路径</h3>
          <div class="path-header-right">
            <span class="progress-text">
              已具备 <strong>{{ matchAnalysis.matchedSkills.length }}</strong> 项 ·
              还需补足 <strong>{{ prioritizedPath.length }}</strong> 项关键技能
            </span>
            <button class="ai-plan-btn" @click="generateAIPlan" :disabled="aiPlanLoading">
              <span v-if="aiPlanLoading" class="ai-plan-loading-dot"></span>
              <span v-else>✨</span>
              {{ aiPlanLoading ? 'AI 规划中...' : 'AI 制定学习计划' }}
            </button>
          </div>
        </div>

        <!-- AI 学习计划结果 -->
        <div v-if="aiPlanResult || aiPlanLoading" class="ai-plan-result">
          <div class="ai-panel-header">
            <span class="ai-badge">✨ Qwen3.5-Plus · AI 学习规划</span>
            <button v-if="aiPlanResult" class="ai-close-btn" @click="aiPlanResult = ''">✕</button>
          </div>
          <div v-if="aiPlanLoading" class="ai-skeleton">
            <div class="skeleton-line w80"></div>
            <div class="skeleton-line w60"></div>
            <div class="skeleton-line w90"></div>
            <div class="skeleton-line w50"></div>
          </div>
          <div v-else class="ai-content" v-html="renderMarkdown(aiPlanResult)"></div>
        </div>

        <!-- 可立即开始区 -->
        <div v-if="readySteps.length > 0" class="path-section">
          <div class="section-tag tag-ready">⚡ 可立即开始</div>
          <div class="learning-steps">
            <div
              v-for="(step, index) in readySteps"
              :key="step.skill"
              class="learning-step step-ready"
            >
              <div class="step-left">
                <div class="step-num">{{ index + 1 }}</div>
                <div class="step-priority" :class="getPriorityClass(index)">
                  {{ getPriorityLabel(index) }}
                </div>
              </div>
              <div class="step-body">
                <div class="step-title-row">
                  <span class="step-skill">{{ step.skill }}</span>
                  <span class="step-ready-badge">无前置要求</span>
                </div>
                <div v-if="step.ownedPrerequisites.length > 0" class="step-owned">
                  <span class="pre-label">你已具备基础：</span>
                  <span v-for="pre in step.ownedPrerequisites.slice(0, 4)" :key="pre" class="owned-chip">{{ pre }}</span>
                </div>
                <div class="step-actions">
                  <button class="step-btn btn-search" @click="searchJobsBySkill(step.skill)">
                    🔍 搜索相关岗位
                  </button>
                  <button class="step-btn btn-gap" @click="analyzeSkillGap(step.skill)">
                    📊 深入分析
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 需要前置学习区 -->
        <div v-if="blockedSteps.length > 0" class="path-section">
          <div class="section-tag tag-blocked">📌 建议先补充前置技能</div>
          <div class="learning-steps">
            <div
              v-for="(step, index) in blockedSteps"
              :key="step.skill"
              class="learning-step step-blocked"
            >
              <div class="step-left">
                <div class="step-num">{{ readySteps.length + index + 1 }}</div>
              </div>
              <div class="step-body">
                <div class="step-title-row">
                  <span class="step-skill">{{ step.skill }}</span>
                </div>
                <div class="step-prereq">
                  <span class="pre-label">先学这些（{{ step.neededPrerequisites.length }} 项）：</span>
                  <span v-for="pre in step.neededPrerequisites.slice(0, 4)" :key="pre" class="needed-chip">{{ pre }}</span>
                  <span v-if="step.neededPrerequisites.length > 4" class="more-pre">+{{ step.neededPrerequisites.length - 4 }}</span>
                </div>
                <div class="step-actions">
                  <button class="step-btn btn-search" @click="searchJobsBySkill(step.skill)">
                    🔍 搜索相关岗位
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </GlassCard>

      <!-- 匹配岗位推荐 -->
      <GlassCard v-if="matchAnalysis.sampleJobs.length > 0" class="sample-jobs-panel">
        <div class="panel-header-row">
          <h3 class="panel-title">💼 匹配岗位推荐</h3>
          <span class="panel-sub">基于你的技能，找到以下可投递岗位</span>
        </div>
        <div class="jobs-list">
          <div
            v-for="job in matchAnalysis.sampleJobs"
            :key="job.title + job.company"
            class="job-card"
          >
            <div class="jc-top">
              <div class="jc-main">
                <div class="jc-title">{{ job.title }}</div>
                <div class="jc-meta">
                  <span class="jc-company">{{ job.company || '企业' }}</span>
                  <span class="dot">·</span>
                  <el-icon style="font-size:12px;vertical-align:-1px"><Location /></el-icon>
                  <span>{{ job.city || '全国' }}</span>
                  <template v-if="job.experience && job.experience !== '不限'">
                    <span class="dot">·</span>
                    <span>{{ job.experience }}</span>
                  </template>
                </div>
              </div>
              <div class="jc-right">
                <div class="jc-salary">{{ job.salary_range || '薪资面议' }}</div>
                <div v-if="calcJobMatch(job) > 0" class="jc-match"
                  :class="{ 'match-high': calcJobMatch(job) >= 60, 'match-med': calcJobMatch(job) >= 30 }">
                  匹配 {{ calcJobMatch(job) }}%
                </div>
              </div>
            </div>

            <!-- 技能对比 -->
            <div v-if="job.skills && job.skills.length" class="jc-skills">
              <template v-if="getJobMatchedSkills(job).length > 0">
                <span class="sk-label sk-have">✅ 已具备：</span>
                <span v-for="s in getJobMatchedSkills(job).slice(0,4)" :key="s" class="sk-chip chip-have">{{ s }}</span>
              </template>
              <template v-if="getJobGapSkills(job).length > 0">
                <span class="sk-label sk-need">📌 还缺：</span>
                <span v-for="s in getJobGapSkills(job).slice(0,3)" :key="s" class="sk-chip chip-need">{{ s }}</span>
              </template>
            </div>

            <!-- 操作 -->
            <div class="jc-actions">
              <button class="jc-btn btn-primary" @click="goSearchSimilar(job)">
                🔍 搜索同类岗位
              </button>
              <button class="jc-btn btn-secondary" @click="goGapAnalysisJob(job)">
                📊 差距分析
              </button>
            </div>
          </div>
        </div>
      </GlassCard>

    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import {
  Medal, MagicStick, Location, User, Upload, Document
} from '@element-plus/icons-vue';
import GlassCard from '@/components/GlassCard.vue';
import SkillTag from '@/components/SkillTag.vue';
import AIButton from '@/components/AIButton.vue';
import { jobApi } from '@/api/jobApi';
import { useAppStore } from '@/stores/app';
import {
  renderMarkdown,
  buildLearningPlanPrompt,
  buildInterpretationPrompt
} from '@/utils/aiPrompt';

const route = useRoute();
const router = useRouter();
const appStore = useAppStore();

// ── 简历来源模式：manual=手动输入，resume=从简历提取
const inputMode = ref<'manual' | 'resume'>('manual');

// 个人中心已保存的简历全文
const savedResumeText = computed(() =>
  (localStorage.getItem('resume_raw_text') || '').trim()
);

// 文件上传引用
const resumeFileRef = ref<HTMLInputElement | null>(null);
const resumeUploading = ref(false);
const extracting = ref(false);

// 触发文件选择
const triggerResumeUpload = () => resumeFileRef.value?.click();

// 解析上传的简历文件
const parseResumeFile = async (file: File): Promise<string> => {
  const name = file.name.toLowerCase();
  if (name.endsWith('.txt')) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = e => resolve((e.target?.result as string) || '');
      reader.onerror = reject;
      reader.readAsText(file, 'utf-8');
    });
  }
  if (name.endsWith('.pdf')) {
    const pdfjsLib = await import('pdfjs-dist');
    pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
      'pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url
    ).toString();
    const ab = await file.arrayBuffer();
    const pdf = await pdfjsLib.getDocument({ data: ab }).promise;
    let text = '';
    for (let i = 1; i <= pdf.numPages; i++) {
      const page = await pdf.getPage(i);
      const content = await page.getTextContent();
      text += content.items.map((it: any) => it.str).join(' ') + '\n';
    }
    return text;
  }
  if (name.endsWith('.docx') || name.endsWith('.doc')) {
    const mammoth = await import('mammoth');
    const ab = await file.arrayBuffer();
    const result = await mammoth.extractRawText({ arrayBuffer: ab });
    return result.value;
  }
  throw new Error('不支持的文件格式');
};

// 处理文件选择 / 拖放
const handleResumeFile = async (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (!file) return;
  await processUploadedResume(file);
  (e.target as HTMLInputElement).value = '';
};
const handleResumeDrop = async (e: DragEvent) => {
  const file = e.dataTransfer?.files?.[0];
  if (file) await processUploadedResume(file);
};
const processUploadedResume = async (file: File) => {
  resumeUploading.value = true;
  try {
    const text = await parseResumeFile(file);
    if (text.trim().length < 50) {
      ElMessage.warning('文件内容过少，请确认文件是否正确');
      return;
    }
    // 保存到 localStorage 并提取技能
    localStorage.setItem('resume_raw_text', text.trim());
    ElMessage.success(`已解析简历（${text.length} 字），正在 AI 提取技能...`);
    await extractSkillsFromResume(text);
  } catch (err: any) {
    ElMessage.error(err?.message || '文件解析失败');
  } finally {
    resumeUploading.value = false;
  }
};

// AI 从简历文本中提取技能
const extractSkillsFromResume = async (text: string) => {
  if (!text.trim()) return;
  extracting.value = true;
  try {
    const prompt =
      `请从以下简历文本中提取所有技术技能（编程语言、框架、工具、平台等），` +
      `只输出技能名称，用英文逗号分隔，不要解释，不要分类，不要序号：\n\n` +
      text.slice(0, 3000);
    const res = await jobApi.chat({ message: prompt, session_id: `extract_${Date.now()}` });
    const raw: string = (res as any)?.data?.response || (res as any)?.data?.data?.response || '';
    if (!raw.trim()) { ElMessage.warning('AI 未能提取到技能，请手动输入'); return; }
    // 解析逗号分隔的技能列表
    const extracted = raw
      .split(/[,，\n]/)
      .map((s: string) => s.replace(/^[0-9\.\-\*\s·]+/, '').trim())
      .filter((s: string) => s.length > 0 && s.length < 30);
    const added = extracted.filter((s: string) => !skillTags.value.includes(s));
    skillTags.value = [...new Set([...skillTags.value, ...added])];
    ElMessage.success(`AI 提取了 ${added.length} 项技能，可继续手动补充`);
  } catch {
    ElMessage.error('AI 提取失败，请稍后重试');
  } finally {
    extracting.value = false;
  }
};

// ── 技能 Tag 输入
const skillTags = ref<string[]>([]);
const skillInputVal = ref('');
const skillInputRef = ref<HTMLInputElement | null>(null);

const focusSkillInput = () => skillInputRef.value?.focus();

const addTag = () => {
  const val = skillInputVal.value.replace(/,|，/g, '').trim();
  if (val && !skillTags.value.includes(val)) {
    skillTags.value.push(val);
  }
  skillInputVal.value = '';
};

const addTagDirect = (tag: string) => {
  if (!skillTags.value.includes(tag)) skillTags.value.push(tag);
};

const removeTag = (i: number) => skillTags.value.splice(i, 1);

const deleteLastTag = () => {
  if (!skillInputVal.value && skillTags.value.length > 0) {
    skillTags.value.pop();
  }
};

// 输入联想（空函数，通过 computed 实现）
const onSkillInput = () => {};

// 技能联想
const skillSuggestions = computed(() => {
  const q = skillInputVal.value.trim().toLowerCase();
  if (!q || q.length < 1) return [];
  const pool = appStore.skillsLoaded ? appStore.skillsList : [];
  return pool
    .filter(s => s.toLowerCase().includes(q) && !skillTags.value.includes(s))
    .slice(0, 8);
});

const quickSkills = ['Python', 'LangChain', 'FastAPI', 'Vue', 'Docker', 'MySQL', 'Redis', 'Git'];

// ── 技能浏览器
const showSkillBrowser = ref(false);
const skillBrowserSearch = ref('');
const sbListRef = ref<HTMLElement | null>(null);

const hotSkillsPreset = [
  'Python', 'Java', 'JavaScript', 'TypeScript', 'Go', 'React', 'Vue', 'Spring Boot',
  'FastAPI', 'Docker', 'MySQL', 'Redis', 'Git', 'LangChain', 'PyTorch', 'AI/ML'
];

const filteredBrowserSkills = computed(() => {
  const q = skillBrowserSearch.value.trim().toLowerCase();
  const pool = appStore.skillsLoaded ? appStore.skillsList : hotSkillsPreset;
  return q ? pool.filter(s => s.toLowerCase().includes(q)) : pool;
});

const skillsGroupedByLetter = computed(() => {
  const groups: Record<string, string[]> = {};
  for (const skill of filteredBrowserSkills.value) {
    const first = skill[0]?.toUpperCase() ?? '#';
    const key = /[A-Z]/.test(first) ? first : '#';
    if (!groups[key]) groups[key] = [];
    groups[key].push(skill);
  }
  return Object.entries(groups).sort(([a], [b]) => {
    if (a === '#') return 1;
    if (b === '#') return -1;
    return a.localeCompare(b);
  });
});

const availableLetters = computed(() =>
  skillsGroupedByLetter.value.map(([letter]) => letter)
);

const toggleSkill = (skill: string) => {
  const idx = skillTags.value.indexOf(skill);
  if (idx >= 0) skillTags.value.splice(idx, 1);
  else skillTags.value.push(skill);
};

const scrollToLetter = (letter: string) => {
  const el = sbListRef.value?.querySelector(`#sb-letter-${letter}`) as HTMLElement | null;
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
};

const popularPositions = [
  'AI应用开发工程师', '大模型工程师', 'Python后端工程师',
  '前端开发工程师', '全栈工程师', '数据工程师', '算法工程师', 'Java架构师'
];

// ── 从档案导入（优先读 uc_skills_cache，更准确）
const hasProfile = computed(() =>
  !!(localStorage.getItem('uc_skills_cache') || localStorage.getItem('userInfo'))
);

const importFromProfile = () => {
  try {
    // 优先读 UserCenter 写入的技能缓存
    const cached = localStorage.getItem('uc_skills_cache');
    let skills: string[] = [];
    if (cached) {
      skills = JSON.parse(cached);
    } else {
      const info = JSON.parse(localStorage.getItem('userInfo') || '{}');
      skills = info.skills || info.user_skills || [];
    }
    if (skills.length === 0) {
      ElMessage.info('档案中暂无技能记录，请前往用户中心添加');
      return;
    }
    const added = skills.filter((s: string) => !skillTags.value.includes(s));
    skillTags.value = [...skillTags.value, ...added];
    ElMessage.success(`已从档案导入 ${added.length} 项技能`);
  } catch {
    ElMessage.error('导入失败');
  }
};

// ── 目标岗位
const targetPosition = ref('');

// ── 加载状态
const loading = ref(false);

// ── 匹配分析结果
const matchAnalysis = ref<any>(null);

// ── 结果摘要计算属性
const matchRateClass = computed(() => {
  if (!matchAnalysis.value) return '';
  const r = matchAnalysis.value.matchRate;
  if (r >= 0.7) return 'rate-high';
  if (r >= 0.4) return 'rate-med';
  return 'rate-low';
});
const matchRingColor = computed(() => {
  if (!matchAnalysis.value) return '#6366f1';
  const r = matchAnalysis.value.matchRate;
  if (r >= 0.7) return '#22c55e';
  if (r >= 0.4) return '#f59e0b';
  return '#ef4444';
});
const matchVerdict = computed(() => {
  if (!matchAnalysis.value) return '';
  const r = matchAnalysis.value.matchRate;
  if (r >= 0.8) return '高度匹配，可直接投递';
  if (r >= 0.6) return '基本匹配，补充少量技能可投递';
  if (r >= 0.4) return '部分匹配，建议针对性学习后投递';
  return '差距较大，建议系统性学习';
});

// ── 雷达图引用
const radarChartRef = ref<HTMLElement | null>(null);
let radarChart: echarts.ECharts | null = null;

// ── 重置
const resetAnalysis = () => {
  matchAnalysis.value = null;
  aiPlanResult.value = '';
  aiInterpretResult.value = '';
};

// ── 分析匹配
const analyzeMatch = async () => {
  if (skillTags.value.length === 0) {
    ElMessage.warning('请先添加你的技能');
    return;
  }
  if (!targetPosition.value) {
    ElMessage.warning('请输入目标岗位');
    return;
  }

  loading.value = true;
  matchAnalysis.value = null;
  try {
    const response = await jobApi.graphGapAnalysis({
      user_skills: skillTags.value,
      target_position: targetPosition.value
    });

    if (response.success) {
      matchAnalysis.value = {
        targetPosition: response.data.target_position,
        matchedSkills: response.data.matched_skills || [],
        missingSkills: response.data.missing_skills || [],
        matchRate: response.data.match_rate || 0,
        learningPath: (response.data.learning_path || []).map((step: any) => ({
          skill: step.skill,
          readyToLearn: step.ready_to_learn ?? false,
          neededPrerequisites: step.needed_prerequisites || [],
          ownedPrerequisites: step.owned_prerequisites || []
        })),
        sampleJobs: response.data.sample_jobs || []
      };

      await nextTick();
      updateRadarChart();
    } else {
      throw new Error(response.message || '分析失败');
    }
  } catch (error) {
    console.error('分析匹配失败:', error);
    ElMessage.error('分析失败，请检查后端服务是否正常');
  } finally {
    loading.value = false;
  }
};

// ── 学习路径计算属性
const prioritizedPath = computed(() => {
  if (!matchAnalysis.value?.learningPath) return [];
  const path = matchAnalysis.value.learningPath;
  const ready = path.filter((s: any) => s.readyToLearn);
  const blocked = path.filter((s: any) => !s.readyToLearn);
  return [...ready, ...blocked].slice(0, 8);
});

const readySteps = computed(() => prioritizedPath.value.filter((s: any) => s.readyToLearn));
const blockedSteps = computed(() => prioritizedPath.value.filter((s: any) => !s.readyToLearn));

const getPriorityClass = (index: number) => {
  if (index === 0) return 'pri-hot';
  if (index <= 1) return 'pri-high';
  return 'pri-med';
};
const getPriorityLabel = (index: number) => {
  if (index === 0) return '🔥 最优先';
  if (index <= 1) return '⭐ 高优先';
  return '推荐';
};

// ── 相关岗位计算属性
const calcJobMatch = (job: any): number => {
  if (!job.skills?.length || !matchAnalysis.value?.matchedSkills?.length) return 0;
  const userSet = new Set(matchAnalysis.value.matchedSkills.map((s: string) => s.toLowerCase()));
  const matched = job.skills.filter((s: string) => userSet.has(s.toLowerCase())).length;
  return Math.round((matched / job.skills.length) * 100);
};

const getJobMatchedSkills = (job: any): string[] => {
  if (!job.skills?.length || !matchAnalysis.value?.matchedSkills?.length) return [];
  const userSet = new Set(matchAnalysis.value.matchedSkills.map((s: string) => s.toLowerCase()));
  return job.skills.filter((s: string) => userSet.has(s.toLowerCase()));
};

const getJobGapSkills = (job: any): string[] => {
  if (!job.skills?.length) return [];
  const userSet = new Set([
    ...(matchAnalysis.value?.matchedSkills || []).map((s: string) => s.toLowerCase())
  ]);
  return job.skills.filter((s: string) => !userSet.has(s.toLowerCase()));
};

// ── AI 调用
const aiPlanLoading = ref(false);
const aiPlanResult = ref('');
const aiInterpretLoading = ref(false);
const aiInterpretResult = ref('');

const generateAIPlan = async () => {
  if (!matchAnalysis.value) return;
  aiPlanLoading.value = true;
  aiPlanResult.value = '';
  try {
    const prompt = buildLearningPlanPrompt({
      targetPosition: matchAnalysis.value.targetPosition || targetPosition.value,
      matchRate: Math.round(matchAnalysis.value.matchRate * 100),
      matchedSkills: matchAnalysis.value.matchedSkills,
      missingSkills: matchAnalysis.value.missingSkills
    });
    const res = await jobApi.chat({ message: prompt, session_id: `plan_${Date.now()}` });
    aiPlanResult.value = (res as any)?.data?.response || (res as any)?.data?.data?.response || '暂无回复';
  } catch {
    aiPlanResult.value = '⚠️ AI 服务暂时不可用，请稍后重试';
  } finally {
    aiPlanLoading.value = false;
  }
};

const generateAIInterpretation = async () => {
  if (!matchAnalysis.value) return;
  aiInterpretLoading.value = true;
  aiInterpretResult.value = '';
  try {
    const prompt = buildInterpretationPrompt({
      targetPosition: matchAnalysis.value.targetPosition || targetPosition.value,
      matchRate: Math.round(matchAnalysis.value.matchRate * 100),
      matchedSkills: matchAnalysis.value.matchedSkills,
      missingSkills: matchAnalysis.value.missingSkills
    });
    const res = await jobApi.chat({ message: prompt, session_id: `interp_${Date.now()}` });
    aiInterpretResult.value = (res as any)?.data?.response || (res as any)?.data?.data?.response || '暂无回复';
  } catch {
    aiInterpretResult.value = '⚠️ AI 服务暂时不可用，请稍后重试';
  } finally {
    aiInterpretLoading.value = false;
  }
};

// ── 桥接：将匹配分析结果带入 AI 助手
const bridgeToChat = () => {
  if (!matchAnalysis.value) return;
  const missing = matchAnalysis.value.missingSkills.join('、');
  const matched = matchAnalysis.value.matchedSkills.join('、');
  const pct = Math.round(matchAnalysis.value.matchRate * 100);
  const prompt =
    `我正在准备应聘「${matchAnalysis.value.targetPosition}」，技能匹配度为 ${pct}%。\n\n` +
    `✅ 我已掌握：${matched || '暂无'}\n` +
    `❌ 我还缺少：${missing || '暂无'}\n\n` +
    `请根据以上差距，帮我制定一个详细的技能提升学习计划，` +
    `包括学习顺序、推荐资源、预计时间，重点结合 2025-2026 年 AI/后端方向岗位需求。`;
  localStorage.setItem('chat_pending_message', prompt);
  localStorage.setItem('chat_pending_mode', 'llm'); // 规划类提示词直接走 LLM，无需图谱检索
  router.push('/chat');
};

// ── 操作函数
const searchJobsBySkill = (skill: string) => {
  router.push(`/search?q=${encodeURIComponent(skill)}`);
};

const analyzeSkillGap = (skill: string) => {
  targetPosition.value = skill;
  analyzeMatch();
};

const goSearchSimilar = (job: any) => {
  router.push(`/search?q=${encodeURIComponent(job.title)}`);
};

const goGapAnalysisJob = (job: any) => {
  targetPosition.value = job.title;
  matchAnalysis.value = null;
  analyzeMatch();
};

// ── 更新雷达图
const updateRadarChart = () => {
  if (!radarChartRef.value) return;
  if (radarChart) radarChart.dispose();

  radarChart = echarts.init(radarChartRef.value);
  if (!matchAnalysis.value) return;

  const allSkills = [
    ...matchAnalysis.value.matchedSkills,
    ...matchAnalysis.value.missingSkills
  ].slice(0, 10);

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(15,15,25,0.9)',
      borderColor: 'rgba(99,102,241,0.3)',
      textStyle: { color: '#e2e8f0', fontSize: 12 }
    },
    radar: {
      shape: 'circle',
      indicator: allSkills.map(skill => ({ name: skill, max: 100 })),
      center: ['50%', '50%'],
      radius: '68%',
      splitArea: { areaStyle: { color: ['rgba(99,102,241,0.04)', 'rgba(99,102,241,0.08)'] } },
      splitLine: { lineStyle: { color: 'rgba(99,102,241,0.2)' } },
      axisLine: { lineStyle: { color: 'rgba(99,102,241,0.25)' } },
      axisName: {
        color: '#94a3b8',
        fontSize: 11,
        formatter: (name: string) => name.length > 6 ? name.slice(0, 5) + '…' : name
      }
    },
    series: [{
      type: 'radar',
      data: [
        {
          value: allSkills.map(skill =>
            matchAnalysis.value.matchedSkills.includes(skill) ? 85 : 15
          ),
          name: '技能掌握',
          areaStyle: {
            color: {
              type: 'radial',
              x: 0.5, y: 0.5, r: 0.5,
              colorStops: [
                { offset: 0, color: 'rgba(99,102,241,0.4)' },
                { offset: 1, color: 'rgba(99,102,241,0.1)' }
              ]
            }
          },
          lineStyle: { color: '#6366f1', width: 2 },
          itemStyle: { color: '#6366f1' },
          symbolSize: 5
        }
      ]
    }]
  };

  radarChart.setOption(option);
  window.addEventListener('resize', () => { radarChart?.resize(); });
};

onMounted(() => {
  if (route.query.skills) {
    const raw = String(route.query.skills);
    skillTags.value = raw.split(',').map(s => s.trim()).filter(Boolean);
  }
  if (route.query.position) {
    targetPosition.value = String(route.query.position);
  }
  appStore.preloadSkills();
});
</script>

<style scoped lang="scss">
.match-dashboard {
  padding: 24px;
  max-width: 1280px;
  margin: 0 auto;
  min-height: calc(100vh - 130px);
  display: flex;
  flex-direction: column;
  gap: 20px;

  // ── 输入卡片
  .setup-card {
    padding: 28px 32px;

    .setup-title {
      display: flex;
      align-items: center;
      gap: 14px;
      margin-bottom: 28px;

      .title-icon { font-size: 28px; color: $primary-color; flex-shrink: 0; }

      h1 { font-size: 1.35rem; font-weight: 700; color: $text-primary; margin: 0 0 4px; }
      p { font-size: 13px; color: $text-secondary; margin: 0; }
    }

    .setup-body {
      display: grid;
      grid-template-columns: 1fr 1fr auto;
      gap: 24px;
      align-items: start;

      @media (max-width: 900px) { grid-template-columns: 1fr; }
    }

    .setup-section {
      .section-label {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 10px;
        font-size: 13.5px;
        font-weight: 600;
        color: $text-primary;

        .label-num {
          width: 22px; height: 22px;
          background: $primary-color; color: #fff;
          border-radius: 50%;
          display: flex; align-items: center; justify-content: center;
          font-size: 12px; font-weight: 700; flex-shrink: 0;
        }
      }

      // ── 来源 Tab 切换
      .source-tabs {
        display: flex; gap: 6px; margin-bottom: 10px;
        .src-tab {
          flex: 1; padding: 6px 12px; border-radius: 8px; cursor: pointer;
          font-size: 12.5px; font-weight: 500;
          border: 1px solid rgba(255,255,255,0.08);
          background: rgba(255,255,255,0.04); color: #64748b;
          transition: all 0.15s; position: relative;
          display: flex; align-items: center; justify-content: center; gap: 4px;
          &:hover { background: rgba(255,255,255,0.07); color: #94a3b8; }
          &.active {
            background: rgba(99,102,241,0.12);
            border-color: rgba(99,102,241,0.3);
            color: #a5b4fc;
          }
          .src-tab-dot {
            width: 6px; height: 6px; border-radius: 50%;
            background: #22c55e; flex-shrink: 0;
          }
        }
      }

      // 从档案导入按钮行
      .import-row {
        margin-bottom: 8px;
        .import-btn {
          display: inline-flex; align-items: center; gap: 4px;
          font-size: 12px; color: $primary-color;
          background: rgba(99,102,241,0.1);
          border: 1px solid rgba(99,102,241,0.25);
          border-radius: 6px; padding: 4px 12px;
          cursor: pointer; transition: all 0.2s;
          &:hover { background: rgba(99,102,241,0.2); }
        }
      }

      // ── 简历来源卡片
      .resume-source-card {
        border-radius: 10px; padding: 12px 14px; margin-bottom: 8px;
        &.rsc-saved {
          background: rgba(34,197,94,0.05);
          border: 1px solid rgba(34,197,94,0.15);
        }
        .rsc-header {
          display: flex; align-items: center; gap: 6px; margin-bottom: 6px;
          .rsc-title { font-size: 12.5px; font-weight: 600; color: #86efac; }
          .rsc-len { margin-left: auto; font-size: 11px; color: #475569; }
        }
        .rsc-preview {
          font-size: 11.5px; color: #64748b; line-height: 1.5;
          margin-bottom: 10px;
          display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
          overflow: hidden;
        }
        .extract-btn {
          width: 100%; padding: 8px; border-radius: 8px; cursor: pointer;
          background: rgba(99,102,241,0.12); border: 1px solid rgba(99,102,241,0.3);
          color: #a5b4fc; font-size: 13px; font-weight: 500;
          display: flex; align-items: center; justify-content: center; gap: 6px;
          transition: all 0.2s;
          &:hover:not(:disabled) { background: rgba(99,102,241,0.2); }
          &:disabled { opacity: 0.6; cursor: not-allowed; }
          .ext-spin {
            width: 14px; height: 14px; border-radius: 50%;
            border: 2px solid rgba(165,180,252,0.3); border-top-color: #a5b4fc;
            animation: spin 0.8s linear infinite; flex-shrink: 0;
          }
        }
      }
      .rsc-empty {
        font-size: 12px; color: #475569;
        padding: 8px 0; margin-bottom: 8px;
        .rsc-link { color: $primary-color; text-decoration: none; margin: 0 3px;
          &:hover { text-decoration: underline; }
        }
      }

      // ── 文件上传区
      .resume-upload-zone {
        border: 1.5px dashed rgba(255,255,255,0.12); border-radius: 10px;
        padding: 14px; margin-bottom: 8px; cursor: pointer;
        display: flex; flex-direction: column; align-items: center; gap: 4px;
        transition: all 0.2s;
        &:hover { border-color: rgba(99,102,241,0.4); background: rgba(99,102,241,0.04); }
        &.uploading { border-color: rgba(99,102,241,0.4); cursor: default; }
        .ruz-icon { font-size: 22px; color: #475569; margin-bottom: 2px; }
        .ruz-text { font-size: 12.5px; color: #64748b; }
        .ruz-hint { font-size: 11px; color: #334155; }
        .ruz-spin {
          width: 20px; height: 20px; border-radius: 50%;
          border: 2px solid rgba(255,255,255,0.1); border-top-color: #6366f1;
          animation: spin 0.8s linear infinite;
        }
      }

      // ── 提取结果展示
      .extracted-result {
        .er-header {
          display: flex; align-items: center; justify-content: space-between;
          margin-bottom: 6px;
          .er-label { font-size: 12px; color: #22c55e; font-weight: 500; }
          .er-clear {
            font-size: 11px; color: #475569; background: none; border: none;
            cursor: pointer; padding: 2px 6px;
            &:hover { color: #ef4444; }
          }
        }
        .tag-area-readonly { cursor: default; }
      }

      // 原 import-btn（兼容旧引用）
      .import-btn {
        display: inline-flex; align-items: center; gap: 4px;
        font-size: 12px; color: $primary-color;
        background: rgba(99,102,241,0.1);
        border: 1px solid rgba(99,102,241,0.25);
        border-radius: 6px; padding: 3px 10px;
        cursor: pointer; transition: all 0.2s;
        &:hover { background: rgba(99,102,241,0.2); }
      }

      .tag-input-area {
        min-height: 56px; padding: 8px 10px;
        background: rgba(255,255,255,0.04);
        border: 1.5px solid rgba(255,255,255,0.1);
        border-radius: 10px;
        display: flex; flex-wrap: wrap; align-items: center; gap: 6px;
        cursor: text; transition: border-color 0.2s;

        &:focus-within {
          border-color: rgba(99,102,241,0.5);
          box-shadow: 0 0 0 3px rgba(99,102,241,0.08);
        }

        .skill-tag-chip {
          display: inline-flex; align-items: center; gap: 5px;
          background: rgba(99,102,241,0.15);
          border: 1px solid rgba(99,102,241,0.3);
          color: #a5b4fc; font-size: 12.5px;
          padding: 3px 8px 3px 10px; border-radius: 20px; white-space: nowrap;

          .tag-remove {
            background: none; border: none; color: rgba(165,180,252,0.6);
            cursor: pointer; padding: 0; font-size: 14px; line-height: 1;
            transition: color 0.15s;
            &:hover { color: #ef4444; }
          }
        }

        .tag-input {
          flex: 1; min-width: 140px;
          background: none; border: none; outline: none;
          color: $text-primary; font-size: 13px; padding: 2px 4px;
          &::placeholder { color: $text-secondary; }
        }
      }

      .skill-suggestions {
        display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px;

        .suggestion-chip {
          font-size: 12px; padding: 2px 10px;
          background: rgba(16,185,129,0.08); color: #6ee7b7;
          border: 1px solid rgba(16,185,129,0.2); border-radius: 20px;
          cursor: pointer; transition: all 0.15s;
          &:hover { background: rgba(16,185,129,0.18); }
        }
      }

      .quick-tags {
        display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-top: 8px;

        .quick-label { font-size: 12px; color: $text-secondary; }

        .quick-chip {
          font-size: 12px; padding: 2px 10px;
          background: rgba(255,255,255,0.05); color: $text-secondary;
          border: 1px solid rgba(255,255,255,0.1); border-radius: 20px;
          cursor: pointer; transition: all 0.15s;
          display: inline-flex; align-items: center; gap: 4px;
          &:hover { background: rgba(99,102,241,0.12); color: #a5b4fc; border-color: rgba(99,102,241,0.3); }
          &.quick-chip--selected {
            background: rgba(99,102,241,0.18); color: #a5b4fc;
            border-color: rgba(99,102,241,0.4);
          }
          .qc-check { font-size: 10px; color: #22c55e; }
        }
      }

      // ── 技能浏览器
      .browser-toggle-btn {
        width: 100%; margin-top: 8px; padding: 7px 14px;
        background: rgba(255,255,255,0.03); border: 1px dashed rgba(255,255,255,0.1);
        border-radius: 8px; color: #64748b; font-size: 12.5px; cursor: pointer;
        display: flex; align-items: center; gap: 6px; transition: all 0.15s;
        &:hover { background: rgba(99,102,241,0.06); border-color: rgba(99,102,241,0.25); color: #94a3b8; }
        .btb-count {
          margin-left: 2px; font-size: 11px; padding: 1px 6px; border-radius: 10px;
          background: rgba(99,102,241,0.15); color: #a5b4fc;
        }
        .btb-arrow { margin-left: auto; font-size: 10px; }
      }

      .skill-browser {
        margin-top: 8px; border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.08);
        background: rgba(15,20,40,0.6); overflow: hidden;

        .sb-search-bar {
          display: flex; align-items: center; gap: 8px; padding: 10px 12px;
          border-bottom: 1px solid rgba(255,255,255,0.06);
          .sb-search-input {
            flex: 1; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08);
            border-radius: 6px; padding: 6px 10px; color: #e2e8f0; font-size: 12.5px;
            outline: none;
            &::placeholder { color: #475569; }
            &:focus { border-color: rgba(99,102,241,0.4); }
          }
          .sb-count { font-size: 11px; color: #475569; white-space: nowrap; }
        }

        .sb-hot-section {
          padding: 10px 12px; border-bottom: 1px solid rgba(255,255,255,0.06);
          .sb-section-title { font-size: 11.5px; font-weight: 600; color: #f59e0b; margin-right: 8px; }
          .sb-hot-chips {
            display: flex; flex-wrap: wrap; gap: 5px; margin-top: 6px;
            .sb-chip {
              font-size: 12px; padding: 3px 10px; border-radius: 20px; cursor: pointer;
              background: rgba(245,158,11,0.08); color: #fbbf24;
              border: 1px solid rgba(245,158,11,0.2); transition: all 0.15s;
              display: inline-flex; align-items: center; gap: 4px;
              &:hover { background: rgba(245,158,11,0.15); }
              &.selected { background: rgba(99,102,241,0.18); color: #a5b4fc; border-color: rgba(99,102,241,0.4); }
              .sb-check { font-size: 10px; color: #22c55e; }
            }
          }
        }

        .sb-body {
          display: flex; height: 320px; overflow: hidden;

          .sb-letter-index {
            width: 28px; flex-shrink: 0; overflow-y: auto; padding: 4px 0;
            background: rgba(255,255,255,0.02);
            border-right: 1px solid rgba(255,255,255,0.05);
            display: flex; flex-direction: column; align-items: center; gap: 1px;
            &::-webkit-scrollbar { display: none; }
            .sb-letter-btn {
              width: 22px; height: 18px; font-size: 10px; font-weight: 600;
              background: none; border: none; color: #475569; cursor: pointer;
              border-radius: 4px; transition: all 0.1s;
              &:hover { background: rgba(99,102,241,0.15); color: #a5b4fc; }
            }
          }

          .sb-list {
            flex: 1; overflow-y: auto; padding: 0 8px 8px;
            &::-webkit-scrollbar { width: 3px; }
            &::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 2px; }

            .sb-group { margin-bottom: 2px; }

            .sb-letter-header {
              font-size: 12px; font-weight: 700; color: #6366f1;
              padding: 6px 4px 4px; position: sticky; top: 0;
              background: rgba(15,20,40,0.95);
            }

            .sb-group-skills {
              display: flex; flex-wrap: wrap; gap: 4px; padding: 0 2px 6px;
              .sb-skill-item {
                font-size: 12px; padding: 3px 10px; border-radius: 16px; cursor: pointer;
                background: rgba(255,255,255,0.04); color: #94a3b8;
                border: 1px solid rgba(255,255,255,0.07); transition: all 0.12s;
                &:hover { background: rgba(99,102,241,0.1); color: #c7d2fe; border-color: rgba(99,102,241,0.25); }
                &.selected {
                  background: rgba(99,102,241,0.2); color: #a5b4fc;
                  border-color: rgba(99,102,241,0.45);
                }
              }
            }
          }
        }
      }

      .position-input {
        width: 100%; box-sizing: border-box;
        padding: 12px 14px;
        background: rgba(255,255,255,0.04);
        border: 1.5px solid rgba(255,255,255,0.1);
        border-radius: 10px; color: $text-primary; font-size: 13.5px;
        outline: none; transition: border-color 0.2s;
        &::placeholder { color: $text-secondary; }
        &:focus { border-color: rgba(99,102,241,0.5); box-shadow: 0 0 0 3px rgba(99,102,241,0.08); }
      }

      .position-presets {
        display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-top: 8px;

        .quick-label { font-size: 12px; color: $text-secondary; white-space: nowrap; }

        .preset-chip {
          font-size: 12px; padding: 2px 10px;
          background: rgba(255,255,255,0.05); color: $text-secondary;
          border: 1px solid rgba(255,255,255,0.1); border-radius: 20px;
          cursor: pointer; transition: all 0.15s;
          &:hover, &.active {
            background: rgba(239,68,68,0.12); color: #fca5a5; border-color: rgba(239,68,68,0.3);
          }
        }
      }
    }

    .setup-action {
      display: flex; flex-direction: column; align-items: center; gap: 10px; padding-top: 30px;

      .analyze-btn {
        display: flex; align-items: center; gap: 8px;
        padding: 13px 32px; font-size: 15px; font-weight: 600;
        border-radius: 12px; border: none; cursor: pointer; white-space: nowrap;
        transition: all 0.2s;
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        color: #fff; box-shadow: 0 4px 16px rgba(99,102,241,0.3);

        &:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(99,102,241,0.45); }
        &:disabled { opacity: 0.7; cursor: not-allowed; }
        &.loading { background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); }

        .btn-spin {
          width: 16px; height: 16px;
          border: 2px solid rgba(255,255,255,0.3);
          border-top-color: #fff; border-radius: 50%;
          animation: spin 0.8s linear infinite; display: inline-block;
        }
      }

      .tech-hint { font-size: 11.5px; color: $text-secondary; text-align: center; }
    }
  }

  // ── 空状态
  .empty-state {
    text-align: center; padding: 60px 20px; color: $text-secondary;

    .empty-icon { font-size: 56px; margin-bottom: 16px; opacity: 0.5; }
    .empty-title { font-size: 16px; color: $text-primary; margin: 0 0 8px; }
    .empty-sub { font-size: 13px; max-width: 420px; margin: 0 auto; }
  }

  // ── 加载状态
  .loading-state {
    text-align: center; padding: 60px 20px; color: $text-secondary;

    .loading-ring {
      width: 48px; height: 48px;
      border: 3px solid rgba(99,102,241,0.2); border-top-color: $primary-color;
      border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 16px;
    }

    p { font-size: 14px; color: $text-secondary; }
  }

  // ── 结果摘要横幅
  .result-banner {
    padding: 24px 28px; display: flex; align-items: center; gap: 24px;

    .banner-left {
      display: flex; align-items: center; gap: 16px; flex-shrink: 0;

      .match-ring {
        position: relative; width: 80px; height: 80px; flex-shrink: 0;

        .ring-svg { width: 80px; height: 80px; }

        .ring-text {
          position: absolute; inset: 0;
          display: flex; flex-direction: column; align-items: center; justify-content: center;

          .ring-pct { font-size: 18px; font-weight: 700; line-height: 1; color: $text-primary; }
          .ring-label { font-size: 11px; color: $text-secondary; }
        }
      }

      .banner-info {
        .banner-position { font-size: 18px; font-weight: 700; color: $text-primary; margin-bottom: 4px; }
        .banner-verdict {
          font-size: 13px;
          &.rate-high { color: #22c55e; }
          &.rate-med  { color: #f59e0b; }
          &.rate-low  { color: #ef4444; }
        }
      }
    }

    .banner-stats {
      display: flex; align-items: center; gap: 20px; flex: 1; justify-content: center;

      .bstat {
        text-align: center;
        .bstat-val { font-size: 28px; font-weight: 700; line-height: 1; margin-bottom: 4px;
          &.bstat-green { color: #22c55e; }
          &.bstat-red   { color: #ef4444; }
          &.bstat-blue  { color: #60a5fa; }
        }
        .bstat-label { font-size: 12px; color: $text-secondary; }
      }

      .bstat-div { width: 1px; height: 36px; background: rgba(255,255,255,0.08); }
    }

    .banner-action {
      flex-shrink: 0;
      display: flex; flex-direction: column; gap: 8px;

      .re-analyze-btn {
        padding: 8px 20px;
        background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12);
        border-radius: 8px; color: $text-secondary; font-size: 13px;
        cursor: pointer; transition: all 0.2s;
        &:hover { background: rgba(255,255,255,0.1); color: $text-primary; }
      }

      .chat-bridge-btn {
        padding: 9px 18px;
        background: rgba(16,185,129,0.1);
        border: 1px solid rgba(16,185,129,0.3);
        border-radius: 8px; color: #34d399; font-size: 13px; font-weight: 600;
        cursor: pointer; transition: all 0.2s; white-space: nowrap;
        &:hover {
          background: rgba(16,185,129,0.18);
          border-color: rgba(16,185,129,0.55);
          box-shadow: 0 4px 16px rgba(16,185,129,0.15);
          transform: translateY(-1px);
        }
      }
    }
  }

  // ── 雷达 + 差距 并排
  .two-col-row {
    display: grid; grid-template-columns: 420px 1fr; gap: 20px;
    @media (max-width: 900px) { grid-template-columns: 1fr; }
  }

  .radar-chart-panel {
    padding: 24px; height: fit-content;
    .panel-title { margin: 0 0 16px; font-size: 1rem; font-weight: 600; color: $text-primary; }
    .chart-container { width: 100%; height: 320px; }
  }

  .gap-analysis-panel {
    padding: 24px; height: fit-content;

    .panel-title-row {
      display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;
      .panel-title { margin: 0; font-size: 1rem; font-weight: 600; color: $text-primary; }
      .rag-badge {
        display: flex; align-items: center; gap: 5px; font-size: 11px; color: $text-secondary;
        background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
        border-radius: 10px; padding: 3px 10px;
        .rag-dot { width: 6px; height: 6px; background: #22c55e; border-radius: 50%; box-shadow: 0 0 6px #22c55e; }
      }
    }

    .gap-info {
      display: flex; flex-direction: column; gap: 16px; margin-bottom: 16px;

      .gap-section {
        .gap-sec-title {
          font-size: 13px; font-weight: 600; color: $text-secondary; margin: 0 0 8px;
          .cnt { background: rgba(52,211,153,0.12); color: #34d399; border-radius: 10px; padding: 0 7px; font-size: 12px; margin-left: 4px;
            &.cnt-red { background: rgba(239,68,68,0.1); color: #f87171; }
          }
        }
        .skills-list { display: flex; flex-wrap: wrap; gap: 6px; }
      }
    }

    .gap-ai-row { margin-top: 8px; }

    .ai-interpret-btn {
      display: flex; align-items: center; gap: 7px; width: 100%; padding: 10px 18px;
      border-radius: 10px; border: 1px dashed rgba(234,179,8,0.3);
      background: rgba(234,179,8,0.04); color: #fbbf24;
      font-size: 13px; font-weight: 500; cursor: pointer; transition: all 0.2s; justify-content: center;
      &:hover:not(:disabled) { background: rgba(234,179,8,0.1); border-color: rgba(234,179,8,0.5); border-style: solid; }
      &:disabled { opacity: 0.5; cursor: default; }
      .ai-plan-loading-dot { width: 8px; height: 8px; border-radius: 50%; border: 2px solid #fbbf24; border-top-color: transparent; animation: spin 0.8s linear infinite; }
    }

    .ai-interpret-panel {
      margin-top: 12px;
      @extend %ai-panel-base;
    }
  }

  // ── 共用 AI 面板 base
  %ai-panel-base {
    border-radius: 14px;
    background: linear-gradient(135deg, rgba(15,15,25,0.9) 0%, rgba(20,16,8,0.9) 100%);
    border: 1px solid rgba(234,179,8,0.22);
    box-shadow: 0 4px 24px rgba(234,179,8,0.06), inset 0 1px 0 rgba(255,255,255,0.04);
    overflow: hidden;
  }

  // AI panel header, skeleton, content
  .ai-panel-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 11px 18px;
    background: linear-gradient(90deg, rgba(234,179,8,0.1) 0%, rgba(234,179,8,0.04) 100%);
    border-bottom: 1px solid rgba(234,179,8,0.12);

    .ai-badge {
      display: flex; align-items: center; gap: 7px;
      font-size: 12px; color: #fde047; font-weight: 700; letter-spacing: 0.5px;
      &::before {
        content: ''; width: 6px; height: 6px; border-radius: 50%;
        background: #fde047; box-shadow: 0 0 6px rgba(253,224,71,0.6);
        animation: pulse-dot 2s ease-in-out infinite;
      }
    }

    .ai-close-btn {
      background: none; border: none; color: rgba(255,255,255,0.3);
      cursor: pointer; font-size: 14px; width: 24px; height: 24px;
      border-radius: 6px; display: flex; align-items: center; justify-content: center;
      transition: all 0.15s;
      &:hover { color: #fff; background: rgba(255,255,255,0.1); }
    }
  }

  .ai-skeleton {
    padding: 20px; display: flex; flex-direction: column; gap: 12px;
    .skeleton-line {
      height: 12px; border-radius: 6px;
      background: linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(234,179,8,0.08) 50%, rgba(255,255,255,0.04) 75%);
      background-size: 200% 100%; animation: shimmer 1.5s infinite;
      &.w80 { width: 80%; } &.w60 { width: 60%; } &.w90 { width: 90%; } &.w50 { width: 50%; }
    }
  }

  .ai-content {
    padding: 18px 20px 20px; font-size: 13.5px; color: rgba(255,255,255,0.88); line-height: 1.85;

    :deep(.md-h3) { font-size: 14px; font-weight: 700; color: #fde047; margin: 18px 0 8px; padding: 6px 12px; background: rgba(234,179,8,0.08); border-left: 3px solid #fde047; border-radius: 0 6px 6px 0; &:first-child { margin-top: 0; } }
    :deep(.md-h4) { font-size: 13.5px; font-weight: 600; color: #fbbf24; margin: 14px 0 6px; }
    :deep(.md-h5) { font-size: 13px; font-weight: 600; color: #fcd34d; margin: 10px 0 4px; }
    :deep(.md-p) { margin: 5px 0; color: rgba(255,255,255,0.82); }
    :deep(.md-spacer) { height: 6px; }
    :deep(strong) { color: #fde047; font-weight: 700; }
    :deep(em) { color: rgba(255,255,255,0.6); font-style: italic; }
    :deep(.md-code) { background: rgba(234,179,8,0.12); color: #fde047; padding: 1px 7px; border-radius: 4px; font-size: 12.5px; font-family: 'Consolas', monospace; border: 1px solid rgba(234,179,8,0.2); }
    :deep(.md-quote) { margin: 8px 0; padding: 8px 14px; border-left: 3px solid rgba(234,179,8,0.4); background: rgba(234,179,8,0.05); border-radius: 0 6px 6px 0; color: rgba(255,255,255,0.7); font-style: italic; }
    :deep(.md-li-ul) { list-style: none; padding: 3px 0 3px 20px; position: relative; color: rgba(255,255,255,0.82); &::before { content: ''; position: absolute; left: 6px; top: 50%; transform: translateY(-50%); width: 5px; height: 5px; border-radius: 50%; background: rgba(253,224,71,0.6); } }
    :deep(.md-li-ol) { list-style: none; display: flex; align-items: baseline; gap: 8px; padding: 4px 0; color: rgba(255,255,255,0.82); .md-ol-num { flex-shrink: 0; display: inline-flex; align-items: center; justify-content: center; width: 20px; height: 20px; border-radius: 50%; background: rgba(234,179,8,0.18); border: 1px solid rgba(234,179,8,0.3); color: #fde047; font-size: 11px; font-weight: 700; } }
    :deep(.md-table-wrap) { overflow-x: auto; margin: 12px 0; border-radius: 8px; border: 1px solid rgba(234,179,8,0.15); }
    :deep(.md-table) { width: 100%; border-collapse: collapse; font-size: 13px;
      th { padding: 9px 14px; text-align: left; background: rgba(234,179,8,0.12); color: #fde047; font-weight: 700; border-bottom: 1px solid rgba(234,179,8,0.2); white-space: nowrap; }
      td { padding: 8px 14px; color: rgba(255,255,255,0.82); border-bottom: 1px solid rgba(255,255,255,0.05); vertical-align: top; line-height: 1.6; }
      tr:last-child td { border-bottom: none; }
      tr:nth-child(even) td { background: rgba(255,255,255,0.02); }
    }
  }

  // ── 学习路径卡片
  .learning-path-panel {
    padding: 24px;

    .path-header {
      display: flex; justify-content: space-between; align-items: flex-start;
      margin-bottom: 20px; flex-wrap: wrap; gap: 10px;

      .panel-title { margin: 0; color: $text-primary; font-size: 1rem; font-weight: 600; }

      .path-header-right {
        display: flex; flex-direction: column; align-items: flex-end; gap: 8px;

        .progress-text { font-size: 13px; color: $text-secondary; strong { color: $text-primary; } }

        .ai-plan-btn {
          display: flex; align-items: center; gap: 6px;
          padding: 6px 16px; border-radius: 20px;
          border: 1px solid rgba(234,179,8,0.35); background: rgba(234,179,8,0.08);
          color: #fde047; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s; white-space: nowrap;
          &:hover:not(:disabled) { background: rgba(234,179,8,0.16); border-color: rgba(234,179,8,0.6); }
          &:disabled { opacity: 0.6; cursor: default; }
          .ai-plan-loading-dot { width: 8px; height: 8px; border-radius: 50%; border: 2px solid #fde047; border-top-color: transparent; animation: spin 0.8s linear infinite; }
        }
      }
    }

    .ai-plan-result {
      margin-bottom: 20px;
      @extend %ai-panel-base;
    }

    .path-section {
      margin-bottom: 20px;

      .section-tag {
        display: inline-block; font-size: 12px; font-weight: 600;
        border-radius: 20px; padding: 3px 12px; margin-bottom: 12px;
        &.tag-ready { background: rgba(16,185,129,0.12); color: #34d399; border: 1px solid rgba(16,185,129,0.25); }
        &.tag-blocked { background: rgba(251,191,36,0.1); color: #fbbf24; border: 1px solid rgba(251,191,36,0.2); }
      }
    }

    .learning-steps { display: flex; flex-direction: column; gap: 10px; }

    .learning-step {
      display: flex; gap: 14px; padding: 14px 16px; border-radius: 10px;
      &.step-ready { background: rgba(16,185,129,0.05); border: 1px solid rgba(16,185,129,0.15); border-left: 3px solid #10b981; }
      &.step-blocked { background: rgba(251,191,36,0.04); border: 1px solid rgba(251,191,36,0.12); border-left: 3px solid #d97706; }

      .step-left {
        display: flex; flex-direction: column; align-items: center; gap: 6px; flex-shrink: 0;
        .step-num { width: 28px; height: 28px; border-radius: 50%; background: rgba(99,102,241,0.2); color: #a5b4fc; font-size: 12px; font-weight: 700; display: flex; align-items: center; justify-content: center; }
        .step-priority { font-size: 10px; font-weight: 600; padding: 2px 6px; border-radius: 8px; white-space: nowrap;
          &.pri-hot { background: rgba(239,68,68,0.15); color: #f87171; }
          &.pri-high { background: rgba(245,158,11,0.15); color: #fbbf24; }
          &.pri-med { background: rgba(99,102,241,0.12); color: #a5b4fc; }
        }
      }

      .step-body {
        flex: 1; min-width: 0;

        .step-title-row {
          display: flex; align-items: center; gap: 8px; margin-bottom: 6px;
          .step-skill { font-size: 14.5px; font-weight: 700; color: $text-primary; }
          .step-ready-badge { font-size: 11px; padding: 1px 8px; border-radius: 10px; background: rgba(16,185,129,0.1); color: #34d399; border: 1px solid rgba(16,185,129,0.2); }
        }

        .step-owned, .step-prereq {
          display: flex; flex-wrap: wrap; align-items: center; gap: 5px; margin-bottom: 6px; font-size: 12px;
          .pre-label { color: $text-secondary; white-space: nowrap; }
          .owned-chip { padding: 1px 8px; border-radius: 10px; background: rgba(52,211,153,0.08); color: #6ee7b7; border: 1px solid rgba(52,211,153,0.15); font-size: 11.5px; }
          .needed-chip { padding: 1px 8px; border-radius: 10px; background: rgba(251,191,36,0.08); color: #fbbf24; border: 1px solid rgba(251,191,36,0.15); font-size: 11.5px; }
          .more-pre { color: $text-secondary; font-size: 11px; }
        }

        .step-actions {
          display: flex; gap: 8px; flex-wrap: wrap;
          .step-btn { font-size: 12px; padding: 4px 12px; border-radius: 7px; cursor: pointer; border: none; transition: all 0.2s;
            &.btn-search { background: rgba(99,102,241,0.1); color: #a5b4fc; border: 1px solid rgba(99,102,241,0.2); &:hover { background: rgba(99,102,241,0.2); } }
            &.btn-gap { background: rgba(236,72,153,0.08); color: #f9a8d4; border: 1px solid rgba(236,72,153,0.15); &:hover { background: rgba(236,72,153,0.15); } }
          }
        }
      }
    }
  }

  // ── 相关岗位卡片
  .sample-jobs-panel {
    padding: 24px;

    .panel-header-row {
      display: flex; align-items: baseline; gap: 12px; margin-bottom: 16px;
      .panel-title { margin: 0; color: $text-primary; font-size: 1rem; font-weight: 600; }
      .panel-sub { font-size: 12px; color: $text-secondary; opacity: 0.7; }
    }

    .jobs-list { display: flex; flex-direction: column; gap: 12px; }

    .job-card {
      padding: 16px 18px; border-radius: 10px;
      background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07);
      transition: border-color 0.2s, background 0.2s;
      &:hover { background: rgba(255,255,255,0.055); border-color: rgba(99,102,241,0.25); }

      .jc-top {
        display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 10px;

        .jc-main {
          .jc-title { font-size: 15px; font-weight: 700; color: $text-primary; margin-bottom: 4px; line-height: 1.4; }
          .jc-meta { display: flex; align-items: center; gap: 5px; font-size: 12.5px; color: $text-secondary; flex-wrap: wrap;
            .jc-company { color: $text-primary; opacity: 0.8; } .dot { opacity: 0.4; }
          }
        }

        .jc-right {
          text-align: right; flex-shrink: 0;
          .jc-salary { font-size: 15px; font-weight: 700; color: #f59e0b; white-space: nowrap; }
          .jc-match { margin-top: 4px; font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 10px; background: rgba(251,191,36,0.1); color: #fbbf24; border: 1px solid rgba(251,191,36,0.2); white-space: nowrap;
            &.match-high { background: rgba(52,211,153,0.1); color: #34d399; border-color: rgba(52,211,153,0.25); }
            &.match-med { background: rgba(99,102,241,0.1); color: #a5b4fc; border-color: rgba(99,102,241,0.2); }
          }
        }
      }

      .jc-skills {
        display: flex; flex-wrap: wrap; align-items: center; gap: 5px; margin-bottom: 10px; font-size: 12px;
        .sk-label { font-size: 11px; font-weight: 600; white-space: nowrap; &.sk-have { color: #34d399; } &.sk-need { color: #fbbf24; } }
        .sk-chip { font-size: 11px; padding: 2px 8px; border-radius: 10px;
          &.chip-have { background: rgba(52,211,153,0.1); color: #34d399; border: 1px solid rgba(52,211,153,0.2); }
          &.chip-need { background: rgba(251,191,36,0.08); color: #fbbf24; border: 1px solid rgba(251,191,36,0.18); }
        }
      }

      .jc-actions {
        display: flex; gap: 8px;
        .jc-btn { font-size: 12.5px; padding: 5px 14px; border-radius: 7px; cursor: pointer; border: none; transition: all 0.2s;
          &.btn-primary { background: rgba(99,102,241,0.12); color: #a5b4fc; border: 1px solid rgba(99,102,241,0.25); &:hover { background: rgba(99,102,241,0.22); } }
          &.btn-secondary { background: rgba(236,72,153,0.08); color: #f9a8d4; border: 1px solid rgba(236,72,153,0.18); &:hover { background: rgba(236,72,153,0.15); } }
        }
      }
    }
  }
}

@keyframes spin { to { transform: rotate(360deg); } }
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
@keyframes pulse-dot {
  0%, 100% { opacity: 1; box-shadow: 0 0 6px rgba(253,224,71,0.6); }
  50% { opacity: 0.5; box-shadow: 0 0 2px rgba(253,224,71,0.2); }
}

@media (max-width: 900px) {
  .match-dashboard .two-col-row { grid-template-columns: 1fr !important; }
  .match-dashboard .setup-body { grid-template-columns: 1fr !important; }
}
</style>
