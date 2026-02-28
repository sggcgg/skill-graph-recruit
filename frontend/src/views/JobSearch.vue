<template>
  <div class="job-search-page">
    <GlassCard class="search-section">
      <div class="search-controls">
        <div class="search-row">
          <el-input
            v-model="searchQuery"
            placeholder="输入岗位关键词，如：Python后端开发、AI工程师..."
            :prefix-icon="Search"
            size="large"
            clearable
            @keyup.enter="searchMode === 'ai' ? performAISearch() : performSearch()"
          />
          <el-button
            class="search-submit-btn"
            size="large"
            :loading="searchLoading"
            @click="searchMode === 'ai' ? performAISearch() : performSearch()"
          >
            <el-icon v-if="!searchLoading">
              <MagicStick v-if="searchMode === 'ai'" />
              <Search v-else />
            </el-icon>
            {{ searchMode === 'ai' ? 'RAG语义搜索' : '图谱搜索' }}
          </el-button>
        </div>
        <div class="search-mode-bar">
          <span class="mode-label">搜索模式：</span>
          <div class="mode-toggle">
            <button
              :class="['mode-btn', { active: searchMode === 'normal' }]"
              @click="searchMode = 'normal'"
            >
              <el-icon><Search /></el-icon>
              图谱搜索
            </button>
            <button
              :class="['mode-btn', 'mode-btn--ai', { active: searchMode === 'ai' }]"
              @click="searchMode = 'ai'"
            >
              <el-icon><MagicStick /></el-icon>
              RAG 语义搜索
            </button>
          </div>
          <span class="mode-hint">
            {{ searchMode === 'ai' ? '🧠 向量检索 + LLM 理解，适合自然语言描述' : '🔗 技能图谱精准匹配，适合关键词搜索' }}
          </span>
        </div>
      </div>
    </GlassCard>

    <!-- 筛选器区域 -->
    <div class="filters-section">
      <GlassCard class="filter-panel">
        <div class="filter-row">
          <div class="filter-item">
            <span class="filter-label">📍 城市</span>
            <AlphaSelector
              mode="city"
              :max="5"
              @selection-change="handleCityChange"
            />
          </div>

          <div class="filter-item">
            <span class="filter-label">💰 薪资范围</span>
            <div class="salary-range-widget">
              <!-- 输入行 -->
              <div class="salary-inputs">
                <div class="salary-input-box" :class="{ active: salaryMin !== undefined }">
                  <input
                    type="number"
                    v-model.number="salaryMin"
                    placeholder="最低"
                    min="0"
                    @input="onSalaryChange"
                  />
                  <span class="salary-k">K</span>
                </div>
                <span class="salary-dash">—</span>
                <div class="salary-input-box" :class="{ active: salaryMax !== undefined }">
                  <input
                    type="number"
                    v-model.number="salaryMax"
                    placeholder="最高"
                    min="0"
                    @input="onSalaryChange"
                  />
                  <span class="salary-k">K</span>
                </div>
                <button v-if="salaryMin !== undefined || salaryMax !== undefined" class="salary-clear-btn" @click="clearSalary" title="清空">
                  <el-icon><Close /></el-icon>
                </button>
              </div>
              <!-- 快捷预设 -->
              <div class="salary-presets">
                <button
                  v-for="p in salaryPresets"
                  :key="p.label"
                  :class="['salary-preset', { active: salaryMin === p.min && salaryMax === p.max }]"
                  @click="applySalaryPreset(p)"
                >{{ p.label }}</button>
              </div>
            </div>
          </div>

          <div class="filter-item">
            <span class="filter-label">🎯 技能要求</span>
            <AlphaSelector
              mode="skill"
              :max="10"
              @selection-change="handleSkillChange"
            />
          </div>

          <div class="filter-item filter-item--sort">
            <span class="filter-label">↕️ 排序方式</span>
            <div class="sort-options">
              <button
                v-for="opt in sortOptions"
                :key="opt.value"
                :class="['sort-btn', { active: sortBy === opt.value }]"
                @click="setSortBy(opt.value)"
              >
                <el-icon><component :is="opt.icon" /></el-icon>
                {{ opt.label }}
              </button>
            </div>
          </div>

          <!-- 常驻确定按钮：有搜索词时显示，有待应用变更时高亮 -->
          <div v-if="searchQuery.trim()" class="filter-item filter-item--confirm">
            <button
              class="filter-confirm-btn"
              :class="{ dirty: filterDirty, loading: searchLoading }"
              :disabled="searchLoading"
              @click="applyFilters"
            >
              <el-icon v-if="searchLoading" class="is-loading"><Loading /></el-icon>
              <el-icon v-else-if="filterDirty"><Refresh /></el-icon>
              <el-icon v-else><Search /></el-icon>
              <span>{{ searchLoading ? '搜索中…' : filterDirty ? '确定搜索' : '重新搜索' }}</span>
              <span v-if="filterDirty" class="confirm-dot"></span>
            </button>
          </div>
        </div>

        <!-- 辅助提示条（有未应用变更时才显示，颜色更柔和不干扰） -->
        <div v-if="filterDirty && searchQuery.trim()" class="filter-dirty-bar">
          <el-icon><Warning /></el-icon>
          筛选条件已变更，点击「确定搜索」使其生效
        </div>
      </GlassCard>
    </div>

    <!-- 搜索结果 -->
    <div class="results-section">
      <div class="results-header">
        <div class="results-title">
          <h2>搜索结果</h2>
          <span class="results-count">{{ sortedResults.length }} 个岗位</span>
          <span v-if="filteredResults.length < searchResults.length" class="filter-hint">
            （共 {{ searchResults.length }} 条，已筛选）
          </span>
          <span class="sort-hint" :class="{ 'sort-hint--active': sortBy }">
            <template v-if="sortBy">
              ↕ 按「{{ sortOptions.find(o => o.value === sortBy)?.label }}」排列
            </template>
            <template v-else>· 默认顺序</template>
          </span>
        </div>
      </div>

      <!-- RAG 搜索说明（上限提示） -->
      <div v-if="searchMode === 'ai' && searchResults.length >= 500" class="rag-limit-tip">
        <el-icon><InfoFilled /></el-icon>
        RAG 语义搜索已返回前 <strong>500</strong> 个最相关结果（向量相似度排序），如需获取全量数据请切换至「图谱搜索」
      </div>

      <!-- RAG LLM 摘要（懒加载） -->
      <div v-if="searchMode === 'ai' && searchResults.length > 0" class="rag-summary">
        <div class="rag-summary-header">
          <el-icon class="rag-icon"><MagicStick /></el-icon>
          <span>RAG 智能摘要</span>
          <el-tag size="small" type="info" style="margin-left:8px;">Qwen · LLM</el-tag>
          <button
            v-if="!ragSummary && !summaryLoading"
            class="summary-generate-btn"
            @click="generateSummary"
          >生成摘要</button>
          <el-icon v-if="summaryLoading" class="is-loading summary-loading-icon"><Loading /></el-icon>
        </div>
        <p v-if="ragSummary" class="rag-summary-text">{{ ragSummary }}</p>
        <p v-else-if="!summaryLoading" class="rag-summary-placeholder">点击「生成摘要」，由 LLM 对本次搜索结果进行智能总结</p>
      </div>

      <div class="results-list">
        <GlassCard
          v-for="job in paginatedResults"
          :key="job.id"
          class="job-card"
        >
          <div class="job-header">
            <div class="job-title-info">
              <div class="job-title-row">
                <h3 class="job-title">{{ job.title }}</h3>
                <span class="job-salary">{{ job.salary_range || '薪资面议' }}</span>
              </div>
              <div class="job-company-row">
                <span class="company-name">{{ job.company || '未知公司' }}</span>
                <span class="divider">·</span>
                <el-icon style="font-size:12px;vertical-align:-1px"><Location /></el-icon>
                <span>{{ job.city || '未知城市' }}</span>
                <template v-if="job.date_posted">
                  <span class="divider">·</span>
                  <el-icon style="font-size:12px;vertical-align:-1px"><Clock /></el-icon>
                  <span>{{ formatDate(job.date_posted) }}</span>
                </template>
                <span class="divider">·</span>
                <span :class="['source-badge', job.source === 'vector' ? 'source-rag' : 'source-graph']">
                  {{ job.source === 'vector' ? '🧠 RAG' : '🔗 图谱' }}
                </span>
              </div>
            </div>
            <div class="job-match">
              <!-- 技能精准匹配：显示匹配比例环 -->
              <template v-if="job.search_type === 'skill'">
                <div
                  class="match-score-ring ring-graph"
                  :style="{ '--pct': Math.round((job.similarity || 0) * 100) }"
                >
                  <span class="match-num">{{ Math.round((job.similarity || 0) * 100) }}%</span>
                </div>
                <div class="match-detail">{{ job.match_count }}/{{ job.total_skills }} 项技能匹配</div>
              </template>
              <!-- 职位名称匹配：显示图标 + 文字，不显示误导性百分比 -->
              <template v-else-if="job.search_type === 'title'">
                <div class="match-title-badge">
                  <span class="match-title-icon">🔗</span>
                  <span class="match-title-text">职位匹配</span>
                </div>
                <div class="match-detail">图谱检索</div>
              </template>
              <!-- 语义向量搜索：显示相似度环 -->
              <template v-else>
                <div
                  class="match-score-ring ring-rag"
                  :style="{ '--pct': Math.round((job.similarity || 0) * 100) }"
                >
                  <span class="match-num">{{ Math.round((job.similarity || 0) * 100) }}%</span>
                </div>
                <div class="match-detail">语义相似度</div>
              </template>
            </div>
          </div>
          
          <div class="job-details">
            <!-- 基本要求标签 -->
            <div class="job-tags-row">
              <span v-if="job.experience && job.experience !== '不限'" class="job-tag tag-exp">
                <el-icon><User /></el-icon>{{ job.experience }}
              </span>
              <span v-if="job.education && job.education !== '不限'" class="job-tag tag-edu">
                <el-icon><Reading /></el-icon>{{ job.education }}
              </span>
              <SkillTag
                v-for="skill in job.skills.slice(0, 6)"
                :key="skill"
                :label="skill"
                :level="getSkillLevel(skill)"
              />
              <span v-if="job.skills.length > 6" class="more-skills">+{{ job.skills.length - 6 }} 项技能</span>
            </div>

            <!-- 技能匹配情况：我已具备 vs 还需补充 -->
            <div v-if="getUserSkillMatch(job).length > 0 || getUserSkillGap(job).length > 0" class="skill-match-row">
              <template v-if="getUserSkillMatch(job).length > 0">
                <span class="match-label match-have">✅ 已具备：</span>
                <span v-for="s in getUserSkillMatch(job)" :key="s" class="match-chip chip-have">{{ s }}</span>
              </template>
              <template v-if="getUserSkillGap(job).length > 0">
                <span class="match-label match-gap">📌 可补充：</span>
                <span v-for="s in getUserSkillGap(job).slice(0,3)" :key="s" class="match-chip chip-gap">{{ s }}</span>
              </template>
            </div>

            <!-- JD 摘要（可展开） -->
            <div v-if="job.document" class="job-snippet-wrap">
              <p class="job-snippet">{{ expandedDescIds.has(job.id) ? job.document : job.document.slice(0, 120) }}</p>
              <button
                v-if="job.document.length > 120"
                class="snippet-toggle"
                @click.stop="toggleDesc(job.id)"
              >
                {{ expandedDescIds.has(job.id) ? '收起 ▲' : `展开全文（共 ${job.document.length} 字）▼` }}
              </button>
            </div>
          </div>

          <div class="job-actions">
            <el-button
              :type="favoritedJobIds.has(job.id) ? 'warning' : 'default'"
              :loading="favoriteLoading === job.id"
              @click="toggleFavorite(job)"
              size="small"
              class="favorite-btn"
            >
              <el-icon><StarFilled v-if="favoritedJobIds.has(job.id)" /><Star v-else /></el-icon>
              {{ favoritedJobIds.has(job.id) ? '已收藏' : '收藏' }}
            </el-button>
            <el-button size="small" class="similar-btn" :loading="similarLoading === job.id" @click="findSimilarJobs(job)">
              <el-icon v-if="similarLoading !== job.id"><Connection /></el-icon>
              相似岗位
            </el-button>
            <el-button size="small" class="gap-btn" @click="analyzeJob(job)">
              <el-icon><DataAnalysis /></el-icon>
              差距分析
            </el-button>
            <el-button size="small" class="ai-review-btn" :loading="aiReviewLoading === job.id" @click="toggleAIReview(job)">
              <span v-if="aiReviewLoading !== job.id">✨</span>
              {{ aiReviewMap.has(job.id) ? 'AI点评 ▲' : 'AI点评' }}
            </el-button>
          </div>

          <!-- AI 点评展开区 -->
          <div v-if="aiReviewLoading === job.id || aiReviewMap.has(job.id)" class="ai-review-panel">
            <div class="ai-review-header">
              <span class="ai-badge-small">✨ Qwen3.5-Plus · 岗位点评</span>
            </div>
            <div v-if="aiReviewLoading === job.id" class="ai-review-loading">
              <span class="loading-dot"></span>
              <span class="loading-dot d2"></span>
              <span class="loading-dot d3"></span>
              <span>AI 正在分析岗位匹配度...</span>
            </div>
            <div v-else class="ai-review-content" v-html="renderJobReview(aiReviewMap.get(job.id) || '')"></div>
          </div>
        </GlassCard>
      </div>

      <!-- 相似岗位抽屉 -->
      <el-drawer
        v-model="showSimilarDrawer"
        direction="rtl"
        size="500px"
        :with-header="false"
      >
        <div v-if="similarDrawerJob" class="similar-drawer-content">
          <!-- 抽屉顶部 -->
          <div class="drawer-top-bar">
            <div class="drawer-top-left">
              <span class="drawer-tag">RAG 语义检索</span>
              <span class="drawer-title">同类岗位市场参考</span>
            </div>
            <button class="drawer-close-btn" @click="showSimilarDrawer = false">✕</button>
          </div>

          <!-- 参照岗位信息卡 -->
          <div class="similar-source-card">
            <div class="source-label">当前参照岗位</div>
            <div class="source-job-title">{{ similarDrawerJob.title }}</div>
            <div class="source-job-meta">
              <span class="sj-source-company">{{ similarDrawerJob.company || '企业' }}</span>
              <span class="divider">·</span>
              <span>{{ similarDrawerJob.city || '全国' }}</span>
              <span class="divider">·</span>
              <span class="source-salary">{{ similarDrawerJob.salary_range || '薪资面议' }}</span>
            </div>
            <div class="source-hint">以下岗位基于技能、职责相似度检索，可作为薪资行情和要求对标参考</div>
          </div>

          <!-- 加载中 -->
          <div v-if="similarLoading === similarDrawerJob.id" class="similar-loading">
            <div class="loading-ring-sm"></div>
            <span>正在检索同类岗位...</span>
          </div>

          <!-- 空状态 -->
          <div v-else-if="similarJobs.length === 0" class="similar-empty">
            <div class="empty-icon-lg">🔍</div>
            <p>暂未找到相似岗位</p>
            <button class="search-more-btn" @click="searchSimilarByTitle(similarDrawerJob)">
              搜索「{{ similarDrawerJob.title }}」相关岗位
            </button>
          </div>

          <!-- 结果列表 -->
          <div v-else class="similar-results">
            <!-- 市场概览行 -->
            <div class="market-summary">
              <div class="ms-item">
                <span class="ms-val">{{ similarJobs.length }}</span>
                <span class="ms-label">同类岗位</span>
              </div>
              <div class="ms-divider"></div>
              <div class="ms-item">
                <span class="ms-val ms-salary">{{ marketSalaryRange }}</span>
                <span class="ms-label">薪资区间</span>
              </div>
              <div class="ms-divider"></div>
              <div class="ms-item">
                <span class="ms-val ms-city">{{ topCitiesText }}</span>
                <span class="ms-label">主要城市</span>
              </div>
            </div>

            <!-- 岗位列表 -->
            <div class="similar-list">
              <div v-for="(sj, idx) in similarJobs" :key="sj.id" class="similar-item">
                <!-- 顶部：标题 + 薪资 -->
                <div class="si-top">
                  <div class="si-title-area">
                    <span class="si-rank">{{ idx + 1 }}</span>
                    <div>
                      <div class="si-title">{{ sj.title }}</div>
                      <div class="si-meta">
                        <span class="si-company">{{ sj.company || '企业' }}</span>
                        <span class="si-dot">·</span>
                        <span class="si-city">{{ sj.city || '全国' }}</span>
                        <template v-if="sj.experience && sj.experience !== '不限'">
                          <span class="si-dot">·</span>
                          <span>{{ sj.experience }}</span>
                        </template>
                      </div>
                    </div>
                  </div>
                  <div class="si-salary-area">
                    <div class="si-salary">{{ sj.salary_range || '面议' }}</div>
                    <div
                      v-if="getSalaryDiff(similarDrawerJob, sj) !== 0"
                      class="si-salary-diff"
                      :class="getSalaryDiff(similarDrawerJob, sj) > 0 ? 'diff-up' : 'diff-down'"
                    >
                      {{ getSalaryDiff(similarDrawerJob, sj) > 0 ? '↑' : '↓' }}
                      {{ Math.abs(getSalaryDiff(similarDrawerJob, sj)) }}K
                    </div>
                  </div>
                </div>

                <!-- 技能对比区 -->
                <div class="si-skills">
                  <template v-if="getSharedSkills(similarDrawerJob, sj).length > 0">
                    <span class="si-skill-label">共同</span>
                    <span
                      v-for="s in getSharedSkills(similarDrawerJob, sj).slice(0,4)"
                      :key="s"
                      class="si-skill-chip chip-shared"
                    >{{ s }}</span>
                  </template>
                  <template v-if="getDiffSkills(similarDrawerJob, sj).length > 0">
                    <span class="si-skill-label si-skill-label-diff">额外要求</span>
                    <span
                      v-for="s in getDiffSkills(similarDrawerJob, sj).slice(0,3)"
                      :key="s"
                      class="si-skill-chip chip-diff"
                    >{{ s }}</span>
                  </template>
                </div>

                <!-- 操作 -->
                <div class="si-actions">
                  <button class="si-btn si-btn-primary" @click="searchSimilarByTitle(sj)">
                    🔍 搜索此类岗位
                  </button>
                  <button class="si-btn si-btn-secondary" @click="goToGapAnalysis(sj)">
                    📊 差距分析
                  </button>
                  <button
                    class="si-btn si-btn-fav"
                    :class="{ 'is-faved': favoritedJobIds.has(sj.id) }"
                    @click="addToFavoriteFromDrawer(sj)"
                  >
                    {{ favoritedJobIds.has(sj.id) ? '★ 已收藏' : '☆ 收藏' }}
                  </button>
                </div>
              </div>
            </div>

            <!-- 底部：搜索更多 -->
            <div class="drawer-footer">
              <button class="search-all-btn" @click="searchSimilarByTitle(similarDrawerJob)">
                🔍 搜索更多「{{ similarDrawerJob.title }}」相关岗位
              </button>
            </div>
          </div>
        </div>
      </el-drawer>

      <!-- 分页 -->
      <div class="pagination-wrapper" v-if="searchResults.length > 0">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="sortedResults.length"
          layout="total, prev, pager, next, jumper"
          @current-change="handlePageChange"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';
import { useAppStore } from '@/stores/app';
import { useRoute } from 'vue-router';
import { ElMessage } from 'element-plus';
import {
  Search, MagicStick, Document, Location, Star, StarFilled,
  Clock, Trophy, Coin, Timer, Connection, Loading, Warning, Refresh, Close,
  User, Reading, DataAnalysis, InfoFilled
} from '@element-plus/icons-vue';
import GlassCard from '@/components/GlassCard.vue';
import SkillTag from '@/components/SkillTag.vue';
import AlphaSelector from '@/components/AlphaSelector.vue';
import { jobApi, type Job } from '@/api/jobApi';
import { userApi } from '@/api/userApi';
import { renderMarkdown as _renderMd, buildJobReviewPrompt } from '@/utils/aiPrompt';

// 搜索相关
const searchQuery = ref('');
const searchLoading = ref(false);
const searchMode = ref<'normal' | 'ai'>('normal');
const searchResults = ref<Job[]>([]);
const ragSummary = ref('');
const summaryLoading = ref(false);
const filterDirty = ref(false);

// 收藏相关
const favoritedJobIds = ref<Set<string>>(new Set());
const favoriteLoading = ref<string | null>(null);

// 筛选器
const selectedCities = ref<string[]>([]);
const selectedSkills = ref<string[]>([]);
const salaryMin = ref<number | undefined>(undefined);
const salaryMax = ref<number | undefined>(undefined);

// 排序和分页
const sortBy = ref<'match' | 'salary' | 'date' | null>(null);
const currentPage = ref(1);

function setSortBy(val: string) {
  const next = (sortBy.value === val ? null : val) as 'match' | 'salary' | 'date' | null;
  sortBy.value = next;
  currentPage.value = 1;
  if (next && searchResults.value.length > 0) {
    const label = sortOptions.find(o => o.value === next)?.label ?? next;
    ElMessage({ message: `✓ 已切换为「${label}」排序`, type: 'success', duration: 1500, grouping: true });
  }
}
const pageSize = ref(10);

const sortOptions = [
  { value: 'salary', label: '薪资最高', icon: Coin   },
  { value: 'match',  label: '匹配度',  icon: Trophy },
];

// 格式化发布日期
const formatDate = (dateStr: string): string => {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    const now = new Date();
    const diff = Math.floor((now.getTime() - d.getTime()) / 86400000);
    if (diff === 0) return '今天';
    if (diff === 1) return '昨天';
    if (diff < 7) return `${diff}天前`;
    if (diff < 30) return `${Math.floor(diff / 7)}周前`;
    return `${d.getMonth() + 1}月${d.getDate()}日`;
  } catch {
    return dateStr;
  }
};

// 解析薪资字符串为数字（如 "7-12K" → 12，"25-50K" → 50）
const parseSalaryMax = (range: string): number => {
  if (!range) return 0;
  const match = range.match(/(\d+)\s*[-~]\s*(\d+)/);
  if (match) return parseInt(match[2]);
  const single = range.match(/(\d+)/);
  return single ? parseInt(single[1]) : 0;
};

// 排序后的结果（基于筛选后的数据）
const sortedResults = computed(() => {
  const list = [...filteredResults.value];
  if (!sortBy.value) {
    return list; // 未选排序 → 保持后端返回的默认顺序
  }
  if (sortBy.value === 'match') {
    list.sort((a, b) => (b.similarity || 0) - (a.similarity || 0));
  } else if (sortBy.value === 'salary') {
    list.sort((a, b) => {
      const aMax = a.salary_max || parseSalaryMax(a.salary_range);
      const bMax = b.salary_max || parseSalaryMax(b.salary_range);
      return bMax - aMax;
    });
  } else if (sortBy.value === 'date') {
    list.sort((a, b) => {
      const aDate = a.date_posted ? new Date(a.date_posted).getTime() : 0;
      const bDate = b.date_posted ? new Date(b.date_posted).getTime() : 0;
      return bDate - aDate;
    });
  }
  return list;
});

// 计算分页结果
const paginatedResults = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  const end = start + pageSize.value;
  return sortedResults.value.slice(start, end);
});

// 进度条颜色

// 获取技能等级
const getSkillLevel = (skill: string) => {
  // 这里可以根据技能的重要性返回不同的等级
  const importantSkills = ['Python', 'Java', 'React', 'Vue', 'AI/ML', 'Docker', 'Kubernetes'];
  if (importantSkills.includes(skill)) return 'primary';
  return 'secondary';
};

// 处理城市选择：仅记录变化，不立即重新搜索
const handleCityChange = (cities: string[]) => {
  selectedCities.value = cities;
  currentPage.value = 1;
  if (searchQuery.value.trim()) filterDirty.value = true;
};

// 处理技能选择：仅记录变化，不立即重新搜索
const handleSkillChange = (skills: string[]) => {
  selectedSkills.value = skills;
  currentPage.value = 1;
  if (searchQuery.value.trim()) filterDirty.value = true;
};

// 手动确认应用筛选条件，重新搜索
const applyFilters = () => {
  filterDirty.value = false;
  searchMode.value === 'ai' ? performAISearch() : performSearch();
};

// 薪资筛选辅助：解析薪资最小值
const parseSalaryMin = (range: string): number => {
  if (!range) return 0;
  const match = range.match(/(\d+)\s*[-~]\s*(\d+)/);
  if (match) return parseInt(match[1]);
  return 0;
};

// 薪资输入变化（重置分页，前端实时过滤，无需重新搜索）
const onSalaryChange = () => { currentPage.value = 1; };
const clearSalary = () => {
  salaryMin.value = undefined;
  salaryMax.value = undefined;
  currentPage.value = 1;
};

// 薪资快捷预设
const salaryPresets = [
  { label: '不限',   min: undefined as number | undefined, max: undefined as number | undefined },
  { label: '< 10K',  min: 0,  max: 10  },
  { label: '10~20K', min: 10, max: 20  },
  { label: '20~30K', min: 20, max: 30  },
  { label: '30K +',  min: 30, max: undefined as number | undefined },
];
const applySalaryPreset = (p: { min?: number; max?: number }) => {
  salaryMin.value = p.min;
  salaryMax.value = p.max;
  currentPage.value = 1;
};

// 筛选后的结果（薪资范围在前端过滤；城市和技能已由重新搜索在后端处理）
const filteredResults = computed(() => {
  let list = searchResults.value;

  const fMin = salaryMin.value ?? 0;
  const fMax = salaryMax.value ?? 9999;
  if (salaryMin.value !== undefined || salaryMax.value !== undefined) {
    list = list.filter(job => {
      const jobMax = job.salary_max || parseSalaryMax(job.salary_range);
      const jobMin = job.salary_min || parseSalaryMin(job.salary_range);
      return jobMax >= fMin && jobMin <= fMax;
    });
  }

  return list;
});

// 薪资变化时重置分页
watch([salaryMin, salaryMax], () => { currentPage.value = 1; });

// 构建最终查询字符串（合并用户输入 + 选中技能）
const buildQuery = () => {
  const parts = [searchQuery.value.trim()];
  if (selectedSkills.value.length > 0) {
    parts.push(...selectedSkills.value);
  }
  return parts.filter(Boolean).join(' ');
};

// 执行搜索
const performSearch = async () => {
  if (!searchQuery.value.trim()) return;

  ragSummary.value = '';
  filterDirty.value = false;
  searchLoading.value = true;
  try {
    // 调用图谱增强搜索API
    const response = await jobApi.graphSearch({
      query: buildQuery(),
      city: selectedCities.value[0] || undefined
    });
    
    if (response.success) {
      const jobs = response.data.jobs || [];
      searchResults.value = jobs.map((job: any) => {
        const isGraph = job.source === 'graph';
        const isSkillMatch = isGraph && job.search_type === 'skill';
        const isTitleMatch = isGraph && job.search_type === 'title';
        const matchCount = job.match_count || 0;
        const totalSkills = job.total_skills || 1;
        const similarity = isSkillMatch
          ? Math.min(matchCount / totalSkills, 1)
          : (job.similarity || 0);
        return {
          id: job.job_id,
          title: job.title,
          company: job.company,
          city: job.city,
          salary_range: job.salary_range,
          experience: job.experience || '',
          education: job.education || '',
          skills: job.matched_skills || job.skills || [],
          match_count: isSkillMatch ? matchCount : undefined,
          total_skills: isSkillMatch ? totalSkills : undefined,
          search_type: job.search_type || (isGraph ? 'skill' : 'vector'),
          source: job.source,
          similarity,
          document: job.jd_text || job.document || '',
          date_posted: job.publish_date || job.date_posted || ''
        };
      });
      currentPage.value = 1;
    } else {
      throw new Error(response.message || '搜索失败');
    }
  } catch (error) {
    console.error('搜索失败:', error);
    // 如果图谱搜索失败，尝试使用RAG搜索
    try {
      const response = await jobApi.searchJobs({
        query: buildQuery(),
        city: selectedCities.value[0] || undefined
      });
      searchResults.value = (response.data?.retrieved_jobs || []).map((job: any) => {
        const range = job.salary_range || '面议';
        const m = range.match(/(\d+)\s*[-~]\s*(\d+)/);
        return {
          id: job.job_id,
          title: job.title || '未知职位',
          company: job.company || '未知公司',
          city: job.city || '未知城市',
          salary_range: range,
          salary_min: m ? parseInt(m[1]) : 0,
          salary_max: m ? parseInt(m[2]) : 0,
          experience: job.experience || '不限',
          education: job.education || '不限',
          skills: Array.isArray(job.skills) ? job.skills : [],
          document: job.document || '',
          similarity: job.similarity || 0,
          source: 'vector'
        };
      });
      currentPage.value = 1;
    } catch (ragError) {
      console.error('RAG搜索也失败，使用模拟数据:', ragError);
      // 使用模拟数据作为兜底
      searchResults.value = Array.from({ length: 25 }, (_, i) => ({
        id: `job_${i}`,
        title: `Python后端开发工程师 ${i+1}`,
        company: `某科技公司 ${i+1}`,
        city: selectedCities.value[0] || '北京',
        salary_min: 15 + i,
        salary_max: 25 + i,
        salary_range: `${15 + i}-${25 + i}K`,
        experience: ['1-3年', '3-5年', '5-10年'][i % 3],
        education: ['本科', '硕士'][i % 2],
        skills: ['Python', 'Django', 'MySQL', 'Redis', 'Docker', 'FastAPI', 'Vue', 'React'].slice(0, 4 + i % 3),
        document: `这是一个关于Python后端开发工程师的职位描述，要求熟悉Django框架，有${i+1}年以上工作经验...`,
        similarity: 0.7 + Math.random() * 0.25
      }));
      currentPage.value = 1;
    }
  } finally {
    searchLoading.value = false;
  }
};

// 懒加载：手动触发 LLM 摘要生成
// 后端 rag_service 会优先用本地 LLM，不可用时自动调 Qwen API 生成摘要
const generateSummary = async () => {
  if (summaryLoading.value || !searchQuery.value.trim()) return;
  summaryLoading.value = true;
  try {
    const response = await jobApi.searchJobs({
      query: buildQuery(),
      city: selectedCities.value[0] || undefined
    });
    const summary = response.data?.summary;
    ragSummary.value = summary || '摘要生成中遇到问题，请稍后重试（请确认后端 Qwen API Key 已配置）';
  } catch {
    ragSummary.value = '摘要生成失败，请稍后重试';
  } finally {
    summaryLoading.value = false;
  }
};

// 执行AI搜索（不等 LLM，先快速返回向量检索结果）
const performAISearch = async () => {
  if (!searchQuery.value.trim()) return;

  filterDirty.value = false;
  ragSummary.value = ''; // 清空旧摘要
  searchLoading.value = true;
  try {
    // 调用RAG搜索API（不带LLM总结，只取向量结果）
    const response = await jobApi.searchJobs({
      query: buildQuery(),
      city: selectedCities.value[0] || undefined
    });
    
    searchResults.value = (response.data?.retrieved_jobs || []).map((job: any) => {
      const range = job.salary_range || '面议';
      const m = range.match(/(\d+)\s*[-~]\s*(\d+)/);
      return {
        id: job.job_id,
        title: job.title || '未知职位',
        company: job.company || '未知公司',
        city: job.city || '未知城市',
        salary_range: range,
        salary_min: m ? parseInt(m[1]) : 0,
        salary_max: m ? parseInt(m[2]) : 0,
        experience: job.experience || '不限',
        education: job.education || '不限',
        skills: Array.isArray(job.skills) ? job.skills : [],
        document: job.document || '',
        similarity: job.similarity || 0,
        source: 'vector'
      };
    });
    currentPage.value = 1;
  } catch (error) {
    console.error('AI搜索失败:', error);
    // 使用模拟数据作为兜底
    searchResults.value = Array.from({ length: 20 }, (_, i) => ({
      id: `ai_job_${i}`,
      title: `AI应用工程师 ${i+1}`,
      company: `AI科技公司 ${i+1}`,
      city: selectedCities.value[0] || '深圳',
      salary_min: 20 + i,
      salary_max: 35 + i,
      salary_range: `${20 + i}-${35 + i}K`,
      experience: ['3-5年', '5-10年', '不限'][i % 3],
      education: ['本科', '硕士', '博士'][i % 3],
      skills: ['AI/ML', 'Python', 'TensorFlow', 'PyTorch', '深度学习', 'NLP', '计算机视觉'].slice(0, 3 + i % 4),
      document: `这是一个AI应用工程师的职位，专注于机器学习和深度学习技术的应用，要求有${i+1}年以上相关经验...`,
      similarity: 0.8 + Math.random() * 0.15
    }));
    currentPage.value = 1;
  } finally {
    searchLoading.value = false;
  }
};

// 收藏/取消收藏岗位
const toggleFavorite = async (job: Job) => {
  const token = localStorage.getItem('token');
  if (!token) {
    ElMessage.warning('请先登录才能收藏岗位');
    return;
  }
  const jobId = job.id || '';
  favoriteLoading.value = jobId;
  try {
    if (favoritedJobIds.value.has(jobId)) {
      await userApi.removeFavorite(jobId);
      favoritedJobIds.value.delete(jobId);
      ElMessage.success('已取消收藏');
    } else {
      const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}');
      await userApi.addFavorite({
        user_id: userInfo.id || 1,
        job_id: jobId,
        title: job.title,
        company: job.company || '',
        salary_range: job.salary_range || '',
        city: job.city || '',
        skills: job.skills || []
      });
      favoritedJobIds.value.add(jobId);
      ElMessage.success('收藏成功！可在个人中心查看');
    }
  } catch (error) {
    console.error('收藏操作失败:', error);
    ElMessage.error('操作失败，请稍后重试');
  } finally {
    favoriteLoading.value = null;
  }
};

// 分析岗位 - 跳转到匹配看板
const analyzeJob = (job: Job) => {
  const skillStr = (job.skills || []).join(', ');
  window.location.href = `/match?skills=${encodeURIComponent(skillStr)}&position=${encodeURIComponent(job.title)}`;
};

// 相似岗位：用 RAG 向量搜索
const similarLoading = ref<string | null>(null);
const similarDrawerJob = ref<Job | null>(null);
const similarJobs = ref<Job[]>([]);
const showSimilarDrawer = ref(false);

const findSimilarJobs = async (job: Job) => {
  similarLoading.value = job.id;
  similarDrawerJob.value = job;
  similarJobs.value = [];
  showSimilarDrawer.value = true;
  try {
    // 用岗位标题 + 技能拼成语义 query，走 RAG 向量检索
    const query = [job.title, ...(job.skills || []).slice(0, 5)].join(' ');
    const response = await jobApi.searchJobs({ query });
    const raw = response.data?.retrieved_jobs || [];
    // 排除自身
    similarJobs.value = raw
      .filter((j: any) => j.job_id !== job.id)
      .slice(0, 8)
      .map((j: any) => {
        const range = j.salary_range || '面议';
        const m = range.match(/(\d+)\s*[-~]\s*(\d+)/);
        return {
          id: j.job_id,
          title: j.title || '未知职位',
          company: j.company || '',
          city: j.city || '',
          salary_range: range,
          salary_min: m ? parseInt(m[1]) : 0,
          salary_max: m ? parseInt(m[2]) : 0,
          experience: j.experience || '不限',
          education: j.education || '不限',
          skills: j.skills || [],
          document: j.document || '',
          similarity: j.similarity || 0,
          source: 'vector' as const,
        };
      });
  } catch {
    ElMessage.error('获取相似岗位失败');
  } finally {
    similarLoading.value = null;
  }
};

// ---- AI 点评 ----
const aiReviewLoading = ref<string | null>(null);
const aiReviewMap = ref<Map<string, string>>(new Map());
const expandedDescIds = ref<Set<string>>(new Set());
function toggleDesc(id: string) {
  const s = new Set(expandedDescIds.value);
  s.has(id) ? s.delete(id) : s.add(id);
  expandedDescIds.value = s;
}

const renderJobReview = (text: string) => _renderMd(text);

const toggleAIReview = async (job: Job) => {
  if (aiReviewMap.value.has(job.id)) {
    aiReviewMap.value.delete(job.id);
    aiReviewMap.value = new Map(aiReviewMap.value);
    return;
  }
  aiReviewLoading.value = job.id;
  try {
    const prompt = buildJobReviewPrompt({
      jobTitle: job.title,
      company: job.company || '未知',
      city: job.city || '未知',
      salaryRange: job.salary_range || '薪资面议',
      experience: job.experience || '不限',
      education: job.education || '不限',
      jobSkills: job.skills || [],
      jobDocument: job.document || '',
      userSkills: userSkills.value
    });
    const res = await jobApi.chat({ message: prompt, session_id: `review_${job.id}_${Date.now()}` });
    const reply = res.data?.response || res.data?.data?.response || '暂无回复';
    aiReviewMap.value.set(job.id, reply);
    aiReviewMap.value = new Map(aiReviewMap.value);
  } catch {
    aiReviewMap.value.set(job.id, '⚠️ AI 服务暂时不可用');
    aiReviewMap.value = new Map(aiReviewMap.value);
  } finally {
    aiReviewLoading.value = null;
  }
};

// 用户已掌握的技能（从本地存储/Pinia获取）
const userSkills = computed<string[]>(() => {
  try {
    // 优先从 UserCenter 写入的技能缓存读取（最准确）
    const cached = localStorage.getItem('uc_skills_cache');
    if (cached) {
      const arr = JSON.parse(cached);
      if (Array.isArray(arr) && arr.length > 0) return arr;
    }
    // 降级：从 userInfo 读取（兼容登录时带技能的情况）
    const info = JSON.parse(localStorage.getItem('userInfo') || '{}');
    return (info.skills || []).map((s: any) => typeof s === 'string' ? s : s.name || '');
  } catch { return []; }
});

// 计算该岗位中用户已有的技能
const getUserSkillMatch = (job: Job) => {
  if (!userSkills.value.length || !job.skills?.length) return [];
  const userSet = new Set(userSkills.value.map((s: string) => s.toLowerCase()));
  return job.skills.filter((s: string) => userSet.has(s.toLowerCase())).slice(0, 4);
};

// 计算该岗位中用户还缺的技能
const getUserSkillGap = (job: Job) => {
  if (!job.skills?.length) return [];
  const userSet = new Set(userSkills.value.map((s: string) => s.toLowerCase()));
  return job.skills.filter((s: string) => !userSet.has(s.toLowerCase())).slice(0, 3);
};

// 两个岗位的共同技能
const getSharedSkills = (jobA: Job | null, jobB: Job) => {
  if (!jobA?.skills?.length || !jobB.skills?.length) return [];
  const setA = new Set(jobA.skills.map((s: string) => s.toLowerCase()));
  return jobB.skills.filter((s: string) => setA.has(s.toLowerCase()));
};

// 岗位 B 相比岗位 A 额外要求的技能
const getDiffSkills = (jobA: Job | null, jobB: Job) => {
  if (!jobA?.skills?.length || !jobB.skills?.length) return jobB.skills || [];
  const setA = new Set(jobA.skills.map((s: string) => s.toLowerCase()));
  return jobB.skills.filter((s: string) => !setA.has(s.toLowerCase()));
};

// 解析薪资中值
const parseSalaryMid = (range?: string): number => {
  if (!range) return 0;
  const m = range.match(/(\d+)\s*[-~]\s*(\d+)/);
  if (m) return (parseInt(m[1]) + parseInt(m[2])) / 2;
  return 0;
};

// 薪资差值（正数=sj更高，负数=sj更低）
const getSalaryDiff = (refJob: Job | null, sj: Job): number => {
  if (!refJob) return 0;
  const ref = parseSalaryMid(refJob.salary_range);
  const cur = parseSalaryMid(sj.salary_range);
  if (!ref || !cur) return 0;
  return Math.round(cur - ref);
};

// 市场薪资区间
const marketSalaryRange = computed(() => {
  if (!similarJobs.value.length) return '—';
  const vals = similarJobs.value
    .map(j => parseSalaryMid(j.salary_range))
    .filter(v => v > 0)
    .sort((a, b) => a - b);
  if (!vals.length) return '面议';
  return `${vals[0]}K ~ ${vals[vals.length - 1]}K`;
});

// 主要城市 Top2
const topCitiesText = computed(() => {
  if (!similarJobs.value.length) return '—';
  const count: Record<string, number> = {};
  similarJobs.value.forEach(j => {
    const c = j.city || '全国';
    count[c] = (count[c] || 0) + 1;
  });
  return Object.entries(count)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 2)
    .map(([c]) => c)
    .join(' / ');
});

// 搜索此类岗位（跳转到岗位搜索页）
const searchSimilarByTitle = (job: Job) => {
  showSimilarDrawer.value = false;
  window.location.href = `/search?q=${encodeURIComponent(job.title)}`;
};

// 从抽屉收藏岗位
const addToFavoriteFromDrawer = async (sj: Job) => {
  const token = localStorage.getItem('token');
  if (!token) { ElMessage.warning('请先登录才能收藏'); return; }
  try {
    const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}');
    await userApi.addFavorite({
      user_id: userInfo.id || 1,
      job_id: sj.id,
      title: sj.title,
      company: sj.company || '',
      salary_range: sj.salary_range || '',
      city: sj.city || '',
      skills: sj.skills || []
    });
    favoritedJobIds.value.add(sj.id);
    ElMessage.success('收藏成功！');
  } catch { ElMessage.error('收藏失败'); }
};

// 从抽屉跳到差距分析
const goToGapAnalysis = (sj: Job) => {
  const skillStr = (sj.skills || []).join(', ');
  window.location.href = `/match?skills=${encodeURIComponent(skillStr)}&position=${encodeURIComponent(sj.title)}`;
};

// 处理分页变化
const handlePageChange = (page: number) => {
  currentPage.value = page;
};

// 初始化：读取URL参数
const route = useRoute();
const appStore = useAppStore();

onMounted(() => {
  // 预加载技能列表（后台静默，不阻塞搜索）
  appStore.preloadSkills();

  if (route.query.q) {
    searchQuery.value = String(route.query.q);
    if (route.query.mode === 'ai') {
      performAISearch();
    } else {
      performSearch();
    }
  }
});
</script>

<style scoped lang="scss">
.job-search-page {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;

  .search-section {
    margin-bottom: 20px;
    padding: 24px;

    .search-controls {
      .search-row {
        display: flex;
        gap: 12px;
        align-items: center;

        :deep(.el-input) {
          flex: 1;
        }

        .search-submit-btn {
          flex-shrink: 0;
          height: 40px;
          padding: 0 24px;
          font-size: 15px;
          font-weight: 600;
          border: none;
          border-radius: 8px;
          background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
          color: white;
          cursor: pointer;
          transition: all 0.2s;
          display: flex;
          align-items: center;
          gap: 6px;

          &:hover {
            background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
          }
        }
      }

      .search-mode-bar {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-top: 12px;

        .mode-label {
          font-size: 13px;
          color: $text-secondary;
          white-space: nowrap;
        }

        .mode-toggle {
          display: flex;
          background: rgba(255, 255, 255, 0.06);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 8px;
          padding: 3px;
          gap: 2px;

          .mode-btn {
            display: flex;
            align-items: center;
            gap: 5px;
            padding: 5px 14px;
            border-radius: 6px;
            border: none;
            background: transparent;
            color: $text-secondary;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s;
            white-space: nowrap;

            &:hover {
              color: $text-primary;
              background: rgba(255, 255, 255, 0.08);
            }

            &.active {
              background: rgba(99, 102, 241, 0.25);
              color: #a5b4fc;
              font-weight: 600;
            }

            &.mode-btn--ai.active {
              background: rgba(236, 72, 153, 0.2);
              color: #f9a8d4;
            }
          }
        }

        .mode-hint {
          font-size: 12px;
          color: $text-secondary;
          opacity: 0.8;
        }
      }

    }
  }

  .filters-section {
    margin-bottom: 20px;
    position: relative;
    z-index: 100;

    .filter-panel {
      padding: 20px 24px;
      overflow: visible;

      // 常驻确定按钮容器
      .filter-item--confirm {
        display: flex;
        align-items: flex-end;
        padding-bottom: 2px;

        .filter-confirm-btn {
          position: relative;
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 8px 20px;
          border-radius: 8px;
          border: 1.5px solid rgba(139, 157, 195, 0.3);
          background: rgba(255, 255, 255, 0.05);
          color: $text-secondary;
          font-size: 13px;
          font-weight: 500;
          cursor: pointer;
          white-space: nowrap;
          transition: all 0.22s ease;

          &:hover:not(:disabled) {
            border-color: rgba(139, 157, 195, 0.6);
            color: $text-primary;
            background: rgba(255, 255, 255, 0.08);
          }

          // 有变更时变为醒目的琥珀色
          &.dirty {
            border-color: rgba(245, 158, 11, 0.6);
            background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(217, 119, 6, 0.1));
            color: #fbbf24;
            box-shadow: 0 0 12px rgba(245, 158, 11, 0.2);

            &:hover:not(:disabled) {
              background: linear-gradient(135deg, #f59e0b, #d97706);
              color: #fff;
              transform: translateY(-1px);
              box-shadow: 0 4px 16px rgba(245, 158, 11, 0.35);
            }
          }

          &.loading, &:disabled {
            opacity: 0.6;
            cursor: not-allowed;
          }

          // 红点提示
          .confirm-dot {
            position: absolute;
            top: -4px; right: -4px;
            width: 8px; height: 8px;
            border-radius: 50%;
            background: #f59e0b;
            border: 1.5px solid #0f1629;
            animation: pulse-dot 1.5s ease-in-out infinite;
          }
        }
      }

      // 辅助提示条
      .filter-dirty-bar {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-top: 10px;
        padding: 7px 12px;
        border-radius: 6px;
        background: rgba(245, 158, 11, 0.06);
        border: 1px solid rgba(245, 158, 11, 0.18);
        font-size: 12px;
        color: rgba(251, 191, 36, 0.75);
      }

      .filter-row {
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
        align-items: flex-start;

        .filter-item {
          display: flex;
          flex-direction: column;
          gap: 8px;
          flex: 1;
          min-width: 160px;

          .filter-label {
            font-size: 12px;
            font-weight: 600;
            color: $text-secondary;
            text-transform: uppercase;
            letter-spacing: 0.05em;
          }

          :deep(.el-select) { width: 100%; }

          .salary-range-widget {
            display: flex;
            flex-direction: column;
            gap: 8px;

            .salary-inputs {
              display: flex;
              align-items: center;
              gap: 6px;

              .salary-input-box {
                display: flex;
                align-items: center;
                flex: 1;
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 6px;
                padding: 0 8px;
                transition: border-color 0.2s;
                height: 32px;

                &:focus-within {
                  border-color: $primary-color;
                  background: rgba(99,102,241,0.08);
                }

                &.active {
                  border-color: rgba(99,102,241,0.4);
                }

                input {
                  flex: 1;
                  width: 0;
                  background: transparent;
                  border: none;
                  outline: none;
                  color: $text-primary;
                  font-size: 13px;

                  &::placeholder { color: rgba(255,255,255,0.25); }

                  // 隐藏 number 类型的上下箭头
                  &::-webkit-outer-spin-button,
                  &::-webkit-inner-spin-button { -webkit-appearance: none; }
                  -moz-appearance: textfield;
                }

                .salary-k {
                  font-size: 11px;
                  color: $text-secondary;
                  flex-shrink: 0;
                }
              }

              .salary-dash {
                color: rgba(255,255,255,0.3);
                font-size: 14px;
                flex-shrink: 0;
              }

              .salary-clear-btn {
                flex-shrink: 0;
                width: 22px;
                height: 22px;
                border-radius: 50%;
                border: none;
                background: rgba(255,255,255,0.08);
                color: $text-secondary;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 11px;
                transition: all 0.15s;

                &:hover {
                  background: rgba(239,68,68,0.2);
                  color: #f87171;
                }
              }
            }

            .salary-presets {
              display: flex;
              gap: 5px;
              flex-wrap: wrap;

              .salary-preset {
                padding: 3px 9px;
                border-radius: 10px;
                border: 1px solid rgba(255,255,255,0.1);
                background: rgba(255,255,255,0.04);
                color: $text-secondary;
                font-size: 11px;
                cursor: pointer;
                transition: all 0.15s;
                white-space: nowrap;

                &:hover {
                  border-color: rgba(99,102,241,0.4);
                  color: $text-primary;
                }

                &.active {
                  border-color: $primary-color;
                  background: rgba(99,102,241,0.18);
                  color: #a5b4fc;
                  font-weight: 600;
                }
              }
            }
          }

          &.filter-item--sort {
            min-width: 220px;

            .sort-options {
              display: flex;
              gap: 6px;
              flex-wrap: wrap;

              .sort-btn {
                display: flex;
                align-items: center;
                gap: 4px;
                padding: 6px 12px;
                border-radius: 20px;
                border: 1px solid rgba(255,255,255,0.12);
                background: rgba(255,255,255,0.05);
                color: $text-secondary;
                font-size: 13px;
                cursor: pointer;
                transition: all 0.2s;
                white-space: nowrap;

                &:hover {
                  border-color: rgba(99,102,241,0.5);
                  color: $text-primary;
                  background: rgba(99,102,241,0.1);
                }

                &.active {
                  border-color: $primary-color;
                  background: rgba(99,102,241,0.2);
                  color: #a5b4fc;
                  font-weight: 600;
                }
              }
            }
          }
        }
      }
    }
  }

  .results-section {
    .rag-limit-tip {
      display: flex; align-items: center; gap: 8px;
      padding: 10px 16px; margin-bottom: 12px;
      background: rgba(245, 158, 11, 0.08);
      border: 1px solid rgba(245, 158, 11, 0.2);
      border-radius: 8px;
      font-size: 13px; color: #d97706;
      .el-icon { color: #f59e0b; flex-shrink: 0; }
      strong { color: #fbbf24; }
    }

    .rag-summary {
      margin-bottom: 20px;
      padding: 18px 20px;
      border-radius: 12px;
      background: linear-gradient(135deg, rgba(236,72,153,0.08) 0%, rgba(139,92,246,0.08) 100%);
      border: 1px solid rgba(236,72,153,0.2);

      .rag-summary-header {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-bottom: 10px;
        font-size: 13px;
        font-weight: 600;
        color: #f9a8d4;

        .rag-icon {
          font-size: 15px;
        }

        .summary-generate-btn {
          margin-left: auto;
          padding: 3px 12px;
          border-radius: 12px;
          border: 1px solid rgba(236,72,153,0.4);
          background: rgba(236,72,153,0.12);
          color: #f9a8d4;
          font-size: 12px;
          cursor: pointer;
          transition: all 0.2s;

          &:hover {
            background: rgba(236,72,153,0.25);
            border-color: rgba(236,72,153,0.7);
          }
        }

        .summary-loading-icon {
          margin-left: auto;
          font-size: 16px;
          color: #f9a8d4;
        }
      }

      .rag-summary-text {
        font-size: 14px;
        color: $text-secondary;
        line-height: 1.7;
        margin: 0;
        white-space: pre-wrap;
      }

      .rag-summary-placeholder {
        font-size: 13px;
        color: rgba(255,255,255,0.3);
        margin: 0;
        font-style: italic;
      }
    }

    .results-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;

      .results-title {
        display: flex;
        align-items: baseline;
        gap: 10px;

        h2 {
          font-size: 1.1rem;
          color: $text-primary;
          margin: 0;
        }

        .results-count {
          font-size: 1rem;
          font-weight: 700;
          color: $primary-color;
        }

        .sort-hint {
          font-size: 0.85rem;
          color: $text-secondary;

          &--active {
            color: #22d3ee;
            font-weight: 500;
          }
        }

        .filter-hint {
          font-size: 0.82rem;
          color: $warning-color;
          opacity: 0.8;
        }
      }
    }

    .results-list {
      .job-card {
        margin-bottom: 20px;
        padding: 24px;
        transition: $transition-hover;

        &:hover {
          transform: translateY(-4px);
        }

        .job-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 16px;

          .job-title-info {
            flex: 1;
            min-width: 0;

            .job-title-row {
              display: flex;
              align-items: baseline;
              gap: 12px;
              margin-bottom: 8px;

              .job-title {
                font-size: 1.15rem;
                font-weight: 700;
                color: $text-primary;
                margin: 0;
                flex: 1;
                min-width: 0;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
              }

              .job-salary {
                flex-shrink: 0;
                font-size: 1rem;
                font-weight: 700;
                color: #f59e0b;
              }
            }

            .job-company-row {
              display: flex;
              align-items: center;
              gap: 5px;
              color: $text-regular;
              font-size: 0.88rem;
              flex-wrap: wrap;

              .company-name {
                font-weight: 500;
                color: $text-secondary;
              }

              .divider {
                color: rgba(255,255,255,0.2);
              }

              .source-badge {
                font-size: 11px;
                padding: 1px 7px;
                border-radius: 10px;
                font-weight: 600;
                letter-spacing: 0.02em;

                &.source-graph {
                  background: rgba(99,102,241,0.15);
                  color: #a5b4fc;
                  border: 1px solid rgba(99,102,241,0.3);
                }

                &.source-rag {
                  background: rgba(236,72,153,0.12);
                  color: #f9a8d4;
                  border: 1px solid rgba(236,72,153,0.25);
                }
              }
            }
          }

          .job-match {
            flex-shrink: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
            width: 80px;

            .match-score-ring {
              position: relative;
              width: 56px; height: 56px;
              border-radius: 50%;
              display: flex; align-items: center; justify-content: center;

              // 图谱匹配：蓝绿色
              &.ring-graph {
                background: conic-gradient(#22d3ee calc(var(--pct) * 1%), rgba(255,255,255,0.08) 0);
                .match-num { color: #67e8f9; }
              }
              // RAG 语义：紫色
              &.ring-rag {
                background: conic-gradient(#818cf8 calc(var(--pct) * 1%), rgba(255,255,255,0.08) 0);
                .match-num { color: #a5b4fc; }
              }
              // 默认（兜底）
              &:not(.ring-graph):not(.ring-rag) {
                background: conic-gradient(#6366f1 calc(var(--pct) * 1%), rgba(255,255,255,0.08) 0);
                .match-num { color: #a5b4fc; }
              }

              &::before {
                content: '';
                position: absolute; inset: 6px;
                border-radius: 50%;
                background: #1e2136;
              }

              .match-num {
                position: relative;
                font-size: 12px; font-weight: 700;
              }
            }

            // 职位名称匹配：图标徽章，不显示百分比
            .match-title-badge {
              width: 56px; height: 56px;
              border-radius: 50%;
              display: flex; flex-direction: column;
              align-items: center; justify-content: center;
              gap: 2px;
              background: rgba(251, 191, 36, 0.12);
              border: 2px solid rgba(251, 191, 36, 0.35);

              .match-title-icon { font-size: 20px; line-height: 1; }
              .match-title-text {
                font-size: 10px; font-weight: 600;
                color: #fbbf24; line-height: 1;
              }
            }

            .match-detail {
              font-size: 11px;
              color: $text-secondary;
              text-align: center;
              line-height: 1.3;
            }
          }
        }

        .job-details {
          display: flex;
          flex-direction: column;
          gap: 10px;
          margin-bottom: 16px;

          .job-tags-row {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 6px;

            .job-tag {
              display: inline-flex;
              align-items: center;
              gap: 3px;
              padding: 2px 9px;
              border-radius: 4px;
              font-size: 12px;
              font-weight: 500;

              &.tag-exp {
                background: rgba(59,130,246,0.12);
                color: #93c5fd;
                border: 1px solid rgba(59,130,246,0.2);
              }

              &.tag-edu {
                background: rgba(16,185,129,0.12);
                color: #6ee7b7;
                border: 1px solid rgba(16,185,129,0.2);
              }
            }

            .more-skills {
              font-size: 11px;
              color: $text-placeholder;
              padding: 2px 6px;
            }
          }

          // 技能匹配行：已具备 vs 可补充
          .skill-match-row {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 5px;
            margin-top: 6px;

            .match-label {
              font-size: 11px;
              font-weight: 600;
              white-space: nowrap;

              &.match-have { color: #34d399; }
              &.match-gap  { color: #fbbf24; }
            }

            .match-chip {
              font-size: 11px;
              padding: 2px 7px;
              border-radius: 10px;
              font-weight: 500;

              &.chip-have {
                background: rgba(52,211,153,0.12);
                color: #34d399;
                border: 1px solid rgba(52,211,153,0.25);
              }
              &.chip-gap {
                background: rgba(251,191,36,0.1);
                color: #fbbf24;
                border: 1px solid rgba(251,191,36,0.2);
              }
            }
          }

          .job-snippet-wrap {
            margin: 6px 0 0;

            .job-snippet {
              font-size: 12.5px;
              color: $text-secondary;
              line-height: 1.65;
              margin: 0;
              opacity: 0.75;
              word-break: break-all;
            }

            .snippet-toggle {
              background: none;
              border: none;
              padding: 2px 0;
              margin-top: 3px;
              font-size: 11.5px;
              color: rgba(99, 179, 237, 0.85);
              cursor: pointer;
              line-height: 1.4;
              transition: color 0.2s;

              &:hover {
                color: #63b3ed;
              }
            }
          }
        }

        .job-actions {
          display: flex;
          gap: 8px;
          justify-content: flex-end;
          align-items: center;
          flex-wrap: wrap;

          .favorite-btn {
            border-radius: 6px;
            &.el-button--warning {
              background: rgba($warning-color, 0.15);
              border-color: rgba($warning-color, 0.4);
              color: $warning-color;
            }
          }

          .similar-btn {
            border-radius: 6px;
            border-color: rgba(236,72,153,0.3);
            color: #f9a8d4;
            background: rgba(236,72,153,0.08);
            &:hover {
              border-color: rgba(236,72,153,0.6);
              background: rgba(236,72,153,0.15);
            }
          }

          .gap-btn {
            border-radius: 6px;
            border-color: rgba(99,102,241,0.35);
            color: #a5b4fc;
            background: rgba(99,102,241,0.08);
            &:hover {
              border-color: rgba(99,102,241,0.6);
              background: rgba(99,102,241,0.15);
            }
          }

          .ai-review-btn {
            border-radius: 6px;
            border-color: rgba(234,179,8,0.3);
            color: #fde047;
            background: rgba(234,179,8,0.07);
            &:hover {
              border-color: rgba(234,179,8,0.55);
              background: rgba(234,179,8,0.13);
            }
          }
        }

        // AI 点评展开区
        .ai-review-panel {
          margin-top: 14px;
          border-radius: 12px;
          background: linear-gradient(135deg, rgba(15,15,25,0.95) 0%, rgba(20,16,8,0.95) 100%);
          border: 1px solid rgba(234,179,8,0.2);
          box-shadow: 0 2px 16px rgba(234,179,8,0.05);
          overflow: hidden;

          .ai-review-header {
            display: flex;
            align-items: center;
            gap: 7px;
            padding: 9px 14px;
            background: rgba(234,179,8,0.08);
            border-bottom: 1px solid rgba(234,179,8,0.1);

            .ai-badge-small {
              font-size: 11px;
              color: #fde047;
              font-weight: 700;
              letter-spacing: 0.4px;

              &::before {
                content: '';
                display: inline-block;
                width: 5px;
                height: 5px;
                border-radius: 50%;
                background: #fde047;
                margin-right: 6px;
                vertical-align: middle;
                box-shadow: 0 0 5px rgba(253,224,71,0.5);
                animation: pulse-dot 2s ease-in-out infinite;
              }
            }
          }

          .ai-review-loading {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 14px 16px;
            color: rgba(255,255,255,0.5);
            font-size: 12.5px;

            .loading-dot {
              width: 6px;
              height: 6px;
              border-radius: 50%;
              background: #fde047;
              animation: bounce 1.2s infinite;
              &.d2 { animation-delay: 0.2s; }
              &.d3 { animation-delay: 0.4s; }
            }
          }

          .ai-review-content {
            padding: 12px 16px 14px;
            font-size: 13.5px;
            color: rgba(255,255,255,0.86);
            line-height: 1.8;

            :deep(.md-h3) {
              font-size: 13.5px; font-weight: 700; color: #fde047;
              margin: 10px 0 5px;
              padding: 4px 10px;
              background: rgba(234,179,8,0.07);
              border-left: 3px solid #fde047;
              border-radius: 0 5px 5px 0;
              &:first-child { margin-top: 0; }
            }
            :deep(.md-p) { margin: 4px 0; color: rgba(255,255,255,0.82); }
            :deep(.md-spacer) { height: 4px; }
            :deep(strong) { color: #fde047; font-weight: 700; }
            :deep(.md-code) {
              background: rgba(234,179,8,0.1);
              color: #fde047;
              padding: 1px 6px;
              border-radius: 4px;
              font-size: 12px;
            }
            :deep(.md-li-ul) {
              list-style: none;
              padding: 3px 0 3px 18px;
              position: relative;
              color: rgba(255,255,255,0.82);
              &::before {
                content: '';
                position: absolute;
                left: 5px;
                top: 50%;
                transform: translateY(-50%);
                width: 5px;
                height: 5px;
                border-radius: 50%;
                background: rgba(253,224,71,0.55);
              }
            }
            :deep(.md-li-ol) {
              list-style: none;
              display: flex;
              align-items: baseline;
              gap: 7px;
              padding: 3px 0;
              color: rgba(255,255,255,0.82);
              .md-ol-num {
                flex-shrink: 0;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 18px;
                height: 18px;
                border-radius: 50%;
                background: rgba(234,179,8,0.15);
                border: 1px solid rgba(234,179,8,0.25);
                color: #fde047;
                font-size: 10px;
                font-weight: 700;
              }
            }
          }
        }
      }
    }
    
    @keyframes bounce {
      0%, 80%, 100% { transform: translateY(0); opacity: 0.6; }
      40% { transform: translateY(-5px); opacity: 1; }
    }
    @keyframes pulse-dot {
      0%, 100% { opacity: 1; box-shadow: 0 0 5px rgba(253,224,71,0.5); }
      50% { opacity: 0.4; box-shadow: 0 0 2px rgba(253,224,71,0.1); }
    }

    // 相似岗位抽屉
    :deep(.el-drawer) {
      background: #0f1117 !important;
    }
    :deep(.el-drawer__body) {
      padding: 0;
      background: #0f1117;
      color: #e2e8f0;
      overflow-y: auto;
    }

    .similar-drawer-content {
      display: flex;
      flex-direction: column;
      min-height: 100%;

      // 顶部栏
      .drawer-top-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 18px 20px 14px;
        border-bottom: 1px solid rgba(255,255,255,0.07);
        position: sticky;
        top: 0;
        background: #0f1117;
        z-index: 10;

        .drawer-top-left {
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .drawer-tag {
          font-size: 10.5px;
          font-weight: 600;
          letter-spacing: 0.5px;
          color: #f9a8d4;
          background: rgba(236,72,153,0.1);
          border: 1px solid rgba(236,72,153,0.2);
          border-radius: 20px;
          padding: 2px 9px;
        }

        .drawer-title {
          font-size: 15px;
          font-weight: 700;
          color: #e2e8f0;
        }

        .drawer-close-btn {
          background: none;
          border: none;
          color: rgba(255,255,255,0.35);
          cursor: pointer;
          font-size: 16px;
          width: 30px; height: 30px;
          border-radius: 8px;
          display: flex; align-items: center; justify-content: center;
          transition: all 0.15s;
          &:hover { color: #e2e8f0; background: rgba(255,255,255,0.08); }
        }
      }

      // 参照岗位卡片
      .similar-source-card {
        margin: 16px 20px 0;
        background: rgba(99,102,241,0.08);
        border: 1px solid rgba(99,102,241,0.2);
        border-radius: 12px;
        padding: 14px 16px;

        .source-label {
          font-size: 10.5px;
          font-weight: 600;
          color: #818cf8;
          letter-spacing: 0.8px;
          text-transform: uppercase;
          margin-bottom: 5px;
        }
        .source-job-title {
          font-size: 16px;
          font-weight: 700;
          color: #e2e8f0;
          margin-bottom: 5px;
          line-height: 1.3;
        }
        .source-job-meta {
          display: flex; align-items: center; gap: 5px;
          font-size: 12.5px; color: #94a3b8;
          .sj-source-company { color: #c4cde0; }
          .source-salary { color: #f59e0b; font-weight: 600; }
          .divider { opacity: 0.4; }
        }
        .source-hint {
          margin-top: 8px; font-size: 11.5px; color: #64748b;
          line-height: 1.5; border-top: 1px solid rgba(255,255,255,0.05);
          padding-top: 8px;
        }
      }

      // 加载中
      .similar-loading {
        display: flex; align-items: center; justify-content: center;
        gap: 10px; padding: 60px 0;
        color: #94a3b8; font-size: 14px;

        .loading-ring-sm {
          width: 20px; height: 20px;
          border: 2px solid rgba(99,102,241,0.2);
          border-top-color: #6366f1;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }
      }

      // 空状态
      .similar-empty {
        display: flex; flex-direction: column; align-items: center;
        justify-content: center; gap: 12px; padding: 60px 20px;
        color: #64748b; font-size: 14px;
        .empty-icon-lg { font-size: 40px; opacity: 0.5; }
        p { margin: 0; }
        .search-more-btn {
          margin-top: 8px;
          padding: 8px 20px;
          background: rgba(99,102,241,0.1);
          border: 1px solid rgba(99,102,241,0.25);
          border-radius: 8px; color: #a5b4fc; font-size: 13px;
          cursor: pointer; transition: all 0.2s;
          &:hover { background: rgba(99,102,241,0.2); }
        }
      }

      // 结果区
      .similar-results {
        padding: 16px 20px 24px;
        flex: 1;

        // 市场概览
        .market-summary {
          display: flex; align-items: center;
          background: rgba(255,255,255,0.03);
          border: 1px solid rgba(255,255,255,0.06);
          border-radius: 10px; padding: 12px 16px;
          margin-bottom: 16px; gap: 16px;

          .ms-item {
            display: flex; flex-direction: column; align-items: center; flex: 1;
            .ms-val {
              font-size: 18px; font-weight: 700; color: #e2e8f0; line-height: 1;
              margin-bottom: 3px;
              &.ms-salary { font-size: 14px; color: #f59e0b; }
              &.ms-city { font-size: 13px; color: #a5b4fc; }
            }
            .ms-label { font-size: 11px; color: #64748b; }
          }

          .ms-divider { width: 1px; height: 32px; background: rgba(255,255,255,0.07); flex-shrink: 0; }
        }

        // 岗位列表
        .similar-list {
          display: flex; flex-direction: column; gap: 10px;

          .similar-item {
            padding: 14px 16px; border-radius: 12px;
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.06);
            transition: border-color 0.2s, background 0.2s;

            &:hover {
              background: rgba(255,255,255,0.055);
              border-color: rgba(99,102,241,0.3);
            }

            // 顶部：标题区 + 薪资区
            .si-top {
              display: flex; justify-content: space-between;
              align-items: flex-start; gap: 10px; margin-bottom: 10px;

              .si-title-area {
                display: flex; gap: 10px; align-items: flex-start; flex: 1; min-width: 0;

                .si-rank {
                  flex-shrink: 0; width: 22px; height: 22px;
                  background: rgba(99,102,241,0.18); color: #a5b4fc;
                  border-radius: 50%; font-size: 11px; font-weight: 700;
                  display: flex; align-items: center; justify-content: center;
                  margin-top: 2px;
                }

                .si-title {
                  font-size: 14.5px; font-weight: 700; color: #e2e8f0;
                  line-height: 1.3; margin-bottom: 4px;
                }

                .si-meta {
                  display: flex; align-items: center; flex-wrap: wrap; gap: 4px;
                  font-size: 12px; color: #64748b;
                  .si-company { color: #94a3b8; }
                  .si-city { color: #64748b; }
                  .si-dot { opacity: 0.4; }
                }
              }

              .si-salary-area {
                text-align: right; flex-shrink: 0;

                .si-salary {
                  font-size: 15px; font-weight: 700; color: #f59e0b; white-space: nowrap;
                }

                .si-salary-diff {
                  margin-top: 3px; font-size: 11px; font-weight: 600;
                  padding: 1px 7px; border-radius: 8px; white-space: nowrap;
                  &.diff-up {
                    background: rgba(34,197,94,0.1); color: #4ade80;
                    border: 1px solid rgba(34,197,94,0.2);
                  }
                  &.diff-down {
                    background: rgba(239,68,68,0.08); color: #f87171;
                    border: 1px solid rgba(239,68,68,0.15);
                  }
                }
              }
            }

            // 技能对比区
            .si-skills {
              display: flex; flex-wrap: wrap; align-items: center;
              gap: 5px; margin-bottom: 10px; min-height: 22px;

              .si-skill-label {
                font-size: 11px; font-weight: 600; color: #64748b; white-space: nowrap;
                &.si-skill-label-diff { color: #94a3b8; }
              }

              .si-skill-chip {
                font-size: 11px; padding: 2px 8px; border-radius: 10px;
                &.chip-shared {
                  background: rgba(52,211,153,0.08); color: #6ee7b7;
                  border: 1px solid rgba(52,211,153,0.18);
                }
                &.chip-diff {
                  background: rgba(251,191,36,0.07); color: #fbbf24;
                  border: 1px solid rgba(251,191,36,0.15);
                }
              }
            }

            // 操作按钮
            .si-actions {
              display: flex; gap: 8px; flex-wrap: wrap;

              .si-btn {
                font-size: 12px; padding: 5px 12px; border-radius: 7px;
                cursor: pointer; border: none; transition: all 0.18s; font-weight: 500;

                &.si-btn-primary {
                  background: rgba(99,102,241,0.12); color: #a5b4fc;
                  border: 1px solid rgba(99,102,241,0.25);
                  &:hover { background: rgba(99,102,241,0.22); }
                }
                &.si-btn-secondary {
                  background: rgba(255,255,255,0.05); color: #94a3b8;
                  border: 1px solid rgba(255,255,255,0.1);
                  &:hover { background: rgba(255,255,255,0.1); color: #e2e8f0; }
                }
                &.si-btn-fav {
                  background: rgba(245,158,11,0.07); color: #d97706;
                  border: 1px solid rgba(245,158,11,0.15);
                  &:hover { background: rgba(245,158,11,0.15); }
                  &.is-faved { background: rgba(245,158,11,0.18); color: #fbbf24; }
                }
              }
            }
          }
        }

        // 底部搜索更多
        .drawer-footer {
          margin-top: 16px; text-align: center;

          .search-all-btn {
            width: 100%; padding: 11px 0;
            background: rgba(99,102,241,0.08);
            border: 1.5px dashed rgba(99,102,241,0.3);
            border-radius: 10px; color: #818cf8; font-size: 13px;
            cursor: pointer; transition: all 0.2s;
            &:hover { background: rgba(99,102,241,0.15); border-style: solid; }
          }
        }
      }
    }

    .pagination-wrapper {
      display: flex;
      justify-content: center;
      margin-top: 30px;
    }
  }
}

@media (max-width: 768px) {
  .filter-row {
    flex-direction: column !important;
    gap: 15px !important;
  }

  .job-header {
    flex-direction: column !important;
    gap: 15px !important;
  }

  .job-match {
    width: 100% !important;
    text-align: left !important;
  }

  .job-details {
    flex-direction: column !important;
    gap: 12px !important;
  }

  .job-actions {
    justify-content: center !important;
  }
}
</style>