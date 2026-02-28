<template>
  <div class="chat-page">

    <!-- 左侧边栏 -->
    <div class="chat-sidebar">
      <!-- AI 身份卡 -->
      <div class="ai-identity">
        <div class="ai-avatar-lg">
          <span class="ai-avatar-char">智</span>
          <span class="ai-online-dot"></span>
        </div>
        <div class="ai-identity-info">
          <div class="ai-name">智聘助手</div>
          <div class="ai-model">Qwen3.5-Plus · RAG · 图谱</div>
        </div>
      </div>

      <!-- Tab 切换：历史对话 / 快速提问 -->
      <div class="sidebar-tabs">
        <button
          :class="['stab', { active: !showSuggestions }]"
          @click="showSuggestions = false"
        >
          历史对话
          <span v-if="sessions.length" class="stab-count">{{ sessions.length }}</span>
        </button>
        <button
          :class="['stab', { active: showSuggestions }]"
          @click="showSuggestions = true"
        >
          快速提问
        </button>
      </div>

      <!-- 历史对话列表 -->
      <div class="history-list" v-if="!showSuggestions">
        <div v-if="sessions.length === 0" class="history-empty">
          <div class="he-icon">💬</div>
          <div class="he-text">暂无历史记录</div>
          <div class="he-hint">发送消息后自动保存</div>
        </div>
        <div
          v-for="sess in sessions"
          :key="sess.id"
          class="history-item"
          :class="{ active: sess.id === sessionId }"
          @click="switchToSession(sess.id)"
        >
          <div class="hi-body">
            <div class="hi-title">{{ sess.title }}</div>
            <div class="hi-meta">
              {{ formatSessionTime(sess.timestamp) }}
              <span class="hi-sep">·</span>
              {{ sess.messageCount }} 问
            </div>
          </div>
          <button
            class="hi-del"
            @click.stop="deleteSession(sess.id)"
            title="删除该对话"
          >✕</button>
        </div>
      </div>

      <!-- 快速提问建议 -->
      <div class="suggestion-section" v-else>
        <div class="suggestion-group" v-for="group in suggestionGroups" :key="group.title">
          <div class="group-title">{{ group.title }}</div>
          <button
            v-for="q in group.questions"
            :key="q"
            class="suggestion-btn"
            @click="sendSuggestion(q)"
            :disabled="isLoading"
          >
            {{ q }}
          </button>
        </div>
      </div>

      <!-- 快捷：简历分析 -->
      <button
        v-if="hasResume"
        class="resume-quick-btn"
        :disabled="isLoading"
        @click="sendResumeToAI"
        title="将我的简历发给 AI 进行分析"
      >
        📄 AI 分析我的简历
      </button>
      <div v-else class="resume-quick-hint">
        <span>在个人中心填写简历后，</span><br/>
        <span>可快速让 AI 帮你分析</span>
      </div>

      <!-- 底部：新对话 + 状态 -->
      <div class="sidebar-footer">
        <button class="new-session-btn" @click="clearChat">
          <span>＋</span> 新对话
        </button>
        <div class="session-stats">
          <span>{{ messages.filter(m=>!m.typing).length }} 条 · 已自动保存</span>
        </div>
      </div>
    </div>

    <!-- 主聊天区 -->
    <div class="chat-main">

      <!-- 顶部栏 -->
      <div class="chat-topbar">
        <div class="topbar-left">
          <span class="topbar-title">AI 智能助手</span>
          <div class="topbar-tags">
            <span class="tag-chip">Qwen3.5-Plus</span>
            <span class="tag-chip">RAG</span>
            <span class="tag-chip">Neo4j</span>
          </div>
        </div>
        <div class="topbar-status">
          <span class="status-dot" :class="{ loading: isLoading }"></span>
          <span class="status-text">{{ isLoading ? 'AI 思考中...' : '在线' }}</span>
        </div>
      </div>

      <!-- 消息区 -->
      <div class="chat-messages" ref="messagesContainerRef">

        <!-- 欢迎屏（无消息时显示） -->
        <div v-if="messages.length === 0" class="welcome-screen">
          <div class="welcome-avatar">
            <span class="welcome-ai-char">智</span>
          </div>
          <h2 class="welcome-title">你好，我是智聘助手</h2>
          <p class="welcome-desc">
            我熟悉中国 IT 就业市场，可以帮你搜索岗位、分析技能差距、了解薪资行情
          </p>
          <div class="welcome-cards">
            <div
              v-for="card in welcomeCards"
              :key="card.title"
              class="welcome-card"
              @click="sendSuggestion(card.example)"
            >
              <span class="wc-icon">{{ card.icon }}</span>
              <div class="wc-body">
                <div class="wc-title">{{ card.title }}</div>
                <div class="wc-example">{{ card.example }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 消息列表 -->
        <template v-else>
          <div
            v-for="(msg, index) in messages"
            :key="index"
            :class="['msg-row', msg.role === 'user' ? 'msg-user' : 'msg-ai']"
            @mouseenter="hoveredIndex = index"
            @mouseleave="hoveredIndex = -1"
          >
            <!-- AI 头像（assistant 消息左侧） -->
            <div v-if="msg.role === 'assistant'" class="msg-avatar msg-avatar-ai">
              <span class="avatar-char">智</span>
            </div>
            <!-- 用户头像（user 消息右侧：row-reverse 下放在 msg-col 之前，反转后显示在右） -->
            <div v-if="msg.role === 'user'" class="msg-avatar msg-avatar-user">
              <span class="avatar-char">我</span>
            </div>

            <div class="msg-col">
              <div class="msg-bubble" :class="{ 'msg-bubble--analysis': msg.isAutoAnalysis }">
                <!-- AI 消息头：模型标签 + 数据来源标签 -->
                <div v-if="msg.role === 'assistant'" class="msg-ai-header">
                  <span class="msg-model-tag">智聘助手</span>
                  <!-- 自动追加的综合分析标签 -->
                  <span v-if="msg.isAutoAnalysis" class="msg-source-tag tag-analysis">
                    🤖 AI 综合分析
                  </span>
                  <!-- 图谱标签（Neo4j 精确匹配） -->
                  <span
                    v-else-if="msg.sourceType === 'graph'"
                    class="msg-source-tag tag-graph"
                    :class="{ expanded: expandedSourceIdx === index }"
                    @click="toggleSource(index)"
                    title="点击查看检索详情"
                  >🔷 图谱检索 {{ expandedSourceIdx === index ? '▲' : '▼' }}</span>
                  <!-- RAG 标签（ChromaDB 语义搜索） -->
                  <span
                    v-else-if="msg.sourceType === 'rag'"
                    class="msg-source-tag tag-rag"
                    :class="{ expanded: expandedSourceIdx === index }"
                    @click="toggleSource(index)"
                    title="点击查看检索详情"
                  >🔶 RAG 检索 {{ expandedSourceIdx === index ? '▲' : '▼' }}</span>
                  <!-- LLM 标签（纯模型回答，无检索） -->
                  <span
                    v-else-if="msg.sourceType === 'llm'"
                    class="msg-source-tag tag-llm"
                  >💬 模型回答</span>
                </div>

                <!-- 来源详情面板（图谱/RAG 点击展开） -->
                <div
                  v-if="msg.sourceType && msg.sourceType !== 'llm' && expandedSourceIdx === index"
                  class="rag-source-panel"
                  :class="{ 'panel-graph': msg.sourceType === 'graph' }"
                >
                  <div class="rsp-title">
                    {{ msg.sourceType === 'graph' ? '🔷 Neo4j 技能图谱检索' : '🔶 ChromaDB RAG 语义检索' }}
                  </div>
                  <div class="rsp-body">
                    <span v-if="msg.sourceType === 'graph'" class="rsp-badge badge-graph">Neo4j 图数据库</span>
                    <span v-if="msg.sourceType === 'graph'" class="rsp-badge badge-graph">Cypher 精确匹配</span>
                    <span v-if="msg.sourceType === 'rag'" class="rsp-badge">ChromaDB 向量库</span>
                    <span v-if="msg.sourceType === 'rag'" class="rsp-badge">m3e-base 语义嵌入</span>
                    <span v-if="parseSourceCount(msg.content)" class="rsp-count">
                      命中 {{ parseSourceCount(msg.content) }} 条岗位数据
                    </span>
                  </div>
                  <div class="rsp-desc">
                    <span v-if="msg.sourceType === 'graph'">
                      通过技能节点关系遍历（Job → REQUIRES → Skill），按技能命中数精确排序
                    </span>
                    <span v-else>
                      基于语义向量相似度召回，结合 Qwen3.5-Plus 生成摘要
                    </span>
                  </div>
                </div>

                <!-- 思考中动画（等待第一个 token 期间） -->
                <div v-if="msg.thinking" class="msg-thinking">
                  <div class="thinking-ring"></div>
                  <span class="thinking-label">{{ msg.toolStatus || loadingStageText }}</span>
                  <span v-if="showThinkingTimer" class="thinking-timer">{{ thinkingSeconds }}s</span>
                </div>
                <!-- 消息内容 -->
                <div
                  v-else
                  class="msg-text"
                  :class="{ 'msg-text-ai': msg.role === 'assistant' }"
                  v-html="msg.role === 'assistant' ? renderMarkdown(msg.displayContent) : escapeHtml(msg.displayContent)"
                ></div>
                <!-- 打字机光标 -->
                <span v-if="msg.typing && !msg.thinking" class="typing-cursor">▌</span>
                <div class="msg-time">{{ msg.timestamp }}</div>
              </div>

              <!-- 消息操作栏（AI 消息 hover 时显示，仅在内容已生成后） -->
              <div
                v-if="msg.role === 'assistant' && !msg.thinking && msg.content && hoveredIndex === index"
                class="msg-actions"
              >
                <button class="ma-btn" @click="copyMessage(msg, index)" :title="copiedIndex === index ? '已复制' : '复制回复'">
                  <span v-if="copiedIndex === index">✓</span>
                  <span v-else>📋</span>
                </button>
                <button
                  class="ma-btn"
                  :class="{ 'ma-active': feedbackMap[index] === 'like' }"
                  @click="feedbackMsg(index, 'like')"
                  title="有帮助"
                >👍</button>
                <button
                  class="ma-btn"
                  :class="{ 'ma-active': feedbackMap[index] === 'dislike' }"
                  @click="feedbackMsg(index, 'dislike')"
                  title="没帮助"
                >👎</button>
              </div>
            </div>

          </div>
        </template>

        <!-- AI 等待气泡：HTTP 连接前的极短过渡，由独立气泡控制 -->
        <div v-if="isLoading" class="msg-row msg-ai msg-row-pending">
          <div class="msg-avatar msg-avatar-ai">
            <span class="avatar-char">智</span>
          </div>
          <div class="msg-bubble">
            <div class="msg-ai-header">
              <span class="msg-model-tag">智聘助手</span>
            </div>
            <div class="msg-thinking">
              <div class="thinking-ring"></div>
              <span class="thinking-label">{{ loadingStageText }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区 -->
      <div class="chat-input-area">
        <!-- 模式选择器 -->
        <div class="mode-selector">
          <button
            v-for="m in modeOptions"
            :key="m.value"
            class="mode-btn"
            :class="{ active: selectedMode === m.value }"
            :title="m.tip"
            @click="selectedMode = m.value"
          >
            <span class="mode-icon">{{ m.icon }}</span>
            <span class="mode-label">{{ m.label }}</span>
          </button>
        </div>
        <div class="input-row">
          <textarea
            ref="inputRef"
            v-model="inputMessage"
            class="chat-textarea"
            placeholder="输入你的问题，例如：我会Python和Django，适合什么岗位？"
            rows="1"
            maxlength="1000"
            @keydown.enter.exact.prevent="handleSend"
            @input="autoResize"
          ></textarea>
          <button
            class="send-btn"
            :class="{ active: canSend, stop: isLoading }"
            :disabled="!canSend && !isLoading"
            @click="isLoading ? stopGeneration() : handleSend()"
          >
            <span v-if="isLoading" class="stop-icon"></span>
            <span v-else class="send-icon">↑</span>
          </button>
        </div>
        <div class="input-hint">
          <span>Enter 发送 · Shift+Enter 换行</span>
          <span class="char-count">{{ inputMessage.length }} / 1000</span>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onActivated, onDeactivated, nextTick, computed, reactive } from 'vue';
import { jobApi } from '@/api/jobApi';
import { renderMarkdown } from '@/utils/aiPrompt';

// ── 消息
interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;         // 最终完整内容
  displayContent: string;  // 打字机当前显示内容
  timestamp: string;
  useRag?: boolean;        // 保留兼容，实际来源用 sourceType
  sourceType?: 'graph' | 'rag' | 'llm' | null;  // 实际数据来源
  typing?: boolean;        // 是否正在流式输出
  thinking?: boolean;      // 是否正在等待第一个 token（"思考中"）
  toolStatus?: string;     // 工具调用进度（临时，不存入消息正文）
  isAutoAnalysis?: boolean; // 是否为图谱/RAG 检索后自动追加的 AI 综合分析
}

const inputMessage = ref('');
const messages = ref<ChatMessage[]>([]);
const isLoading = ref(false);

// ── 检索模式选择器
const selectedMode = ref<'auto' | 'graph' | 'rag' | 'llm'>('auto');
const modeOptions: Array<{ value: 'auto' | 'graph' | 'rag' | 'llm'; label: string; icon: string; tip: string }> = [
  { value: 'auto',  label: '自动',  icon: '🤖', tip: '智能识别最合适的检索方式' },
  { value: 'graph', label: '图谱',  icon: '🔷', tip: '强制使用 Neo4j 技能图谱检索' },
  { value: 'rag',   label: 'RAG',   icon: '🔶', tip: '强制使用 ChromaDB 语义检索' },
  { value: 'llm',   label: '模型',  icon: '💬', tip: '仅使用大模型知识回答，不检索数据库' },
];

// ── 停止生成
const activeReader = ref<ReadableStreamDefaultReader<Uint8Array> | null>(null);
const stopGeneration = () => {
  if (activeReader.value) {
    activeReader.value.cancel().catch(() => {});
    activeReader.value = null;
  }
  stopLoadingStages();
  stopThinkingTimer();
  isLoading.value = false;
};

// ── 发送按钮可用状态
const canSend = computed(() => inputMessage.value.trim().length > 0 && !isLoading.value);

// ── 消息操作栏
const hoveredIndex = ref(-1);
const copiedIndex = ref(-1);
const feedbackMap = reactive<Record<number, 'like' | 'dislike'>>({});

const copyMessage = async (msg: ChatMessage, index: number) => {
  try {
    await navigator.clipboard.writeText(msg.content);
    copiedIndex.value = index;
    setTimeout(() => { copiedIndex.value = -1; }, 2000);
  } catch {
    // 降级：创建临时 textarea
    const el = document.createElement('textarea');
    el.value = msg.content;
    document.body.appendChild(el);
    el.select();
    document.execCommand('copy');
    document.body.removeChild(el);
    copiedIndex.value = index;
    setTimeout(() => { copiedIndex.value = -1; }, 2000);
  }
};

const feedbackMsg = (index: number, type: 'like' | 'dislike') => {
  feedbackMap[index] = feedbackMap[index] === type ? undefined as any : type;
};

// ── RAG 来源展开
const expandedSourceIdx = ref(-1);
const toggleSource = (index: number) => {
  expandedSourceIdx.value = expandedSourceIdx.value === index ? -1 : index;
};

// 从消息内容中解析岗位数量（如"找到 **8** 个相关岗位"）
const parseSourceCount = (content: string): number | null => {
  const m = content.match(/找到\s*\*{0,2}(\d+)\*{0,2}\s*个/);
  return m ? parseInt(m[1]) : null;
};
const messagesContainerRef = ref<HTMLElement | null>(null);
const inputRef = ref<HTMLTextAreaElement | null>(null);
const thinkingSeconds = ref(0);
// computed 避免在模板 attribute 中直接写 >= 运算符（含 > 字符，会触发 vite-plugin-vue-devtools 解析错误）
const showThinkingTimer = computed(() => thinkingSeconds.value >= 6);
let thinkingTimer: ReturnType<typeof setInterval> | null = null;

const startThinkingTimer = () => {
  thinkingSeconds.value = 0;
  thinkingTimer = setInterval(() => { thinkingSeconds.value++; }, 1000);
};
const stopThinkingTimer = () => {
  if (thinkingTimer) { clearInterval(thinkingTimer); thinkingTimer = null; }
  thinkingSeconds.value = 0;
};

// 维持整个页面生命周期的 session（确保上下文连贯）
const sessionId = ref(`chat_${Date.now()}`);

// ── 加载阶段提示
const LOADING_STAGES = [
  { text: '正在理解你的问题...', progress: 10 },
  { text: '正在检索岗位数据库...', progress: 30 },
  { text: '正在查询技能图谱...', progress: 50 },
  { text: '正在分析匹配度...', progress: 68 },
  { text: '正在生成回复...', progress: 85 },
  { text: '即将完成...', progress: 95 },
];
const loadingStageIdx = ref(0);
const loadingStageText = ref(LOADING_STAGES[0].text);
const loadingProgress = ref(LOADING_STAGES[0].progress);
let stageTimer: ReturnType<typeof setInterval> | null = null;

const startLoadingStages = () => {
  loadingStageIdx.value = 0;
  loadingStageText.value = LOADING_STAGES[0].text;
  loadingProgress.value = LOADING_STAGES[0].progress;
  let idx = 0;
  stageTimer = setInterval(() => {
    idx = Math.min(idx + 1, LOADING_STAGES.length - 1);
    loadingStageIdx.value = idx;
    loadingStageText.value = LOADING_STAGES[idx].text;
    loadingProgress.value = LOADING_STAGES[idx].progress;
    if (idx === LOADING_STAGES.length - 1) clearInterval(stageTimer!);
  }, 1400);
};

const stopLoadingStages = () => {
  if (stageTimer) { clearInterval(stageTimer); stageTimer = null; }
};

// ── 打字机效果（根据文本长度动态调整速度）
const typeMessage = async (msg: ChatMessage) => {
  msg.typing = true;
  msg.displayContent = '';
  const text = msg.content;
  // 文本越长，每帧写越多字符，确保在约 2.5 秒内呈现完毕
  const targetDuration = 2200; // ms
  const fps = 60;
  const totalFrames = (targetDuration / 1000) * fps;
  const chunkSize = Math.max(2, Math.ceil(text.length / totalFrames));
  let i = 0;
  return new Promise<void>((resolve) => {
    const tick = () => {
      if (i >= text.length) {
        msg.displayContent = text; // 确保完整
        msg.typing = false;
        resolve();
        return;
      }
      i = Math.min(i + chunkSize, text.length);
      msg.displayContent = text.slice(0, i);
      scrollToBottom();
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
};

// ── 时间
const currentTime = () => {
  const now = new Date();
  return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
};

// ── 转义用户消息（防 XSS）
const escapeHtml = (text: string) =>
  text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>');

// ── 欢迎卡片
const welcomeCards = [
  { icon: '🔍', title: '岗位搜索', example: '我会Vue和Node.js，北京有哪些适合我的岗位？' },
  { icon: '📊', title: '技能差距', example: '想转Python后端，我还需要学哪些技能？' },
  { icon: '💰', title: '薪资行情', example: 'Java架构师的平均薪资是多少？' },
  { icon: '🚀', title: '学习路径', example: '从前端转全栈，推荐一个学习路径' },
];

// ── 侧边栏建议问题
const suggestionGroups = [
  {
    title: '🔍 岗位搜索',
    questions: [
      '帮我找Python后端工程师岗位',
      '成都有哪些前端开发职位？',
      '推荐匹配Java技能的岗位',
    ]
  },
  {
    title: '📊 技能分析',
    questions: [
      '我会React、TypeScript，技能够用吗？',
      '云原生方向需要掌握哪些技术？',
      '数据工程师必备技能有哪些？',
    ]
  },
  {
    title: '💰 市场行情',
    questions: [
      'Go语言工程师薪资行情',
      '算法工程师和后端工程师薪资对比',
      'AI方向岗位需求趋势如何？',
    ]
  }
];

// ── 自动调整输入框高度
const autoResize = () => {
  const el = inputRef.value;
  if (!el) return;
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 140) + 'px';
};

// ── 滚动到底部
const scrollToBottom = async () => {
  await nextTick();
  if (messagesContainerRef.value) {
    messagesContainerRef.value.scrollTop = messagesContainerRef.value.scrollHeight;
  }
};

// ── 图谱/RAG 检索完成后自动追加 LLM 综合分析
const triggerAutoAnalysis = async (originalQuery: string) => {
  if (isLoading.value) return;

  const prompt =
    `根据刚才针对「${originalQuery}」的岗位检索结果，请给出简洁的综合分析：\n` +
    `1. 岗位主要技能要求与趋势\n` +
    `2. 薪资区间与市场竞争度判断\n` +
    `3. 针对该方向求职者的提升建议（优先补充哪些技能）\n` +
    `请直接给出分析，不需要重复展示岗位列表。`;

  const analysisMsg: ChatMessage = {
    role: 'assistant',
    content: '',
    displayContent: '',
    timestamp: currentTime(),
    useRag: false,
    sourceType: 'llm',
    typing: true,
    thinking: true,
    toolStatus: undefined,
    isAutoAnalysis: true,
  };

  isLoading.value = true;
  startLoadingStages();
  startThinkingTimer();
  messages.value.push(analysisMsg);
  const rAnalysis = messages.value[messages.value.length - 1] as ChatMessage;
  await scrollToBottom();

  try {
    const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    const token = localStorage.getItem('token');
    const res = await fetch(`${API_BASE}/api/agent/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ message: prompt, session_id: sessionId.value, mode: 'llm' }),
    });

    if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

    const reader = res.body.getReader();
    activeReader.value = reader;
    const decoder = new TextDecoder();
    let buffer = '';
    let firstToken = false;
    let skipNext = false;

    outer: while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';

      for (const line of lines) {
        if (!line.trim()) continue;
        if (line.startsWith('event: ')) {
          skipNext = line.includes('session') || line.includes('status');
          continue;
        }
        if (!line.startsWith('data: ')) continue;
        if (skipNext) { skipNext = false; continue; }
        const payload = line.slice(6);
        if (payload === '[DONE]') {
          stopLoadingStages(); stopThinkingTimer();
          isLoading.value = false;
          rAnalysis.thinking = false; rAnalysis.typing = false;
          break outer;
        }
        const chunk = payload.replace(/\\n/g, '\n');
        if (!firstToken) {
          firstToken = true;
          stopLoadingStages(); stopThinkingTimer();
          isLoading.value = false;
          rAnalysis.thinking = false;
        }
        rAnalysis.content += chunk;
        rAnalysis.displayContent = rAnalysis.content;
        scrollToBottom();
      }
    }
    if (!rAnalysis.content.trim()) {
      rAnalysis.content = '⚠️ AI 分析暂时不可用，请稍后重试。';
      rAnalysis.displayContent = rAnalysis.content;
    }
  } catch {
    if (!rAnalysis.content.trim()) {
      rAnalysis.content = '⚠️ AI 综合分析暂时不可用，请稍后重试。';
      rAnalysis.displayContent = rAnalysis.content;
    }
  } finally {
    stopLoadingStages(); stopThinkingTimer();
    isLoading.value = false;
    rAnalysis.thinking = false; rAnalysis.typing = false;
    activeReader.value = null;
    saveHistory();
  }
};

// ── 发送消息（SSE 流式优先，降级为普通请求）
const handleSend = async () => {
  if (!inputMessage.value.trim() || isLoading.value) return;

  const userMessage = inputMessage.value.trim();
  messages.value.push({ role: 'user', content: userMessage, displayContent: userMessage, timestamp: currentTime() });
  inputMessage.value = '';
  if (inputRef.value) inputRef.value.style.height = 'auto';
  isLoading.value = true;
  startLoadingStages();
  startThinkingTimer();
  await scrollToBottom();

  // AI 消息气泡占位（HTTP 连接前就显示思考动画）
  const newMsg: ChatMessage = {
    role: 'assistant',
    content: '',
    displayContent: '',
    timestamp: currentTime(),
    useRag: false,
    sourceType: null,
    typing: true,
    thinking: true,
    toolStatus: undefined,
  };

  let streamSuccess = false;
  let msgPushed = false;
  // rMsg 指向 Vue 响应式代理版本（push 后获取），对它的赋值才能触发模板实时更新
  // 注意：直接对 newMsg（原始对象）赋值会绕过 Vue 3 的 Proxy，最多延迟 1.4s 才渲染
  let rMsg: ChatMessage = newMsg;

  const pushMsgBubble = async () => {
    if (!msgPushed) {
      msgPushed = true;
      isLoading.value = false;  // 切换到气泡内的 thinking 动画
      messages.value.push(newMsg);
      // 拿 Vue 响应式代理（必须在 push 后获取）
      rMsg = messages.value[messages.value.length - 1] as ChatMessage;
      await scrollToBottom();
    }
  };

  try {
    const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    const token = localStorage.getItem('token');
    const res = await fetch(`${API_BASE}/api/agent/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      body: JSON.stringify({ message: userMessage, session_id: sessionId.value, mode: selectedMode.value })
    });

    if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

    // HTTP 连接建立 → 隐藏等待气泡，显示 AI 气泡的 thinking 动画
    await pushMsgBubble();
    streamSuccess = true;

    const reader = res.body.getReader();
    activeReader.value = reader;    // 保存供 stopGeneration() 取消用
    const decoder = new TextDecoder();
    let buffer = '';
    let firstTextToken = false;      // 标记是否收到第一个真实文本 token
    let skipNextData = false;        // 跳过 session/status 事件的 data 行
    let pendingToolStatus = false;   // 下一个 data 行是工具状态文字
    let pendingSource = false;       // 下一个 data 行是数据来源类型
    let pendingError = false;        // 下一个 data 行是错误信息，直接渲染给用户

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';

      for (const line of lines) {
        if (!line.trim()) {
          // 空行 = SSE 事件分隔符，重置所有标志
          skipNextData = false;
          pendingToolStatus = false;
          pendingError = false;
          continue;
        }

        // ── event 行：根据类型决定如何处理后续 data ──
        if (line.startsWith('event: ')) {
          const evtType = line.slice(7).trim();
          if (evtType === 'session' || evtType === 'status') {
            skipNextData = true;      // 这两类事件的 data 行不是正文，跳过
            continue;
          }
          if (evtType === 'tool_status') {
            pendingToolStatus = true; // 下一个 data 是工具进度，更新思考动画文字
            continue;
          }
          if (evtType === 'source') {
            skipNextData = false;
            pendingToolStatus = false;
            // 下一个 data 行是来源类型（graph/rag/llm），单独处理
            pendingSource = true;
            continue;
          }
          if (evtType === 'error') {
            skipNextData = false;
            pendingToolStatus = false;
            pendingSource = false;
            pendingError = true;    // 下一行 data 是错误内容，展示给用户
            stopLoadingStages();
            stopThinkingTimer();
            isLoading.value = false;
            rMsg.thinking = false;
            rMsg.typing = false;
          }
          continue;
        }

        // ── data 行 ──
        if (line.startsWith('data: ')) {
          if (skipNextData) {
            skipNextData = false;
            continue;   // 跳过 session/status 的 data 行
          }

          if (pendingToolStatus) {
            pendingToolStatus = false;
            const statusText = line.slice(6).trim();
            // 通过响应式代理赋值，立即触发模板更新（直接改 newMsg 不会触发）
            rMsg.toolStatus = statusText || undefined;
            continue;
          }

          if (pendingSource) {
            pendingSource = false;
            const src = line.slice(6).trim() as 'graph' | 'rag' | 'llm';
            rMsg.sourceType = src || null;
            rMsg.useRag = src === 'rag';   // 保持 useRag 兼容
            continue;
          }

          if (pendingError) {
            pendingError = false;
            const errText = line.slice(6).trim();
            if (errText && errText !== '[DONE]') {
              rMsg.content = errText;
              rMsg.displayContent = errText;
            }
            continue;
          }

          const payload = line.slice(6);
          if (payload === '[DONE]') {
            stopLoadingStages();
            stopThinkingTimer();
            isLoading.value = false;
            rMsg.thinking = false;
            rMsg.toolStatus = undefined;
            rMsg.typing = false;
            break;
          }
          const chunk = payload.replace(/\\n/g, '\n');

          if (!firstTextToken) {
            // 第一个真实文本 token：停止 loading，切换为内容模式，清除工具状态
            firstTextToken = true;
            stopLoadingStages();
            stopThinkingTimer();
            isLoading.value = false;
            rMsg.thinking = false;
            rMsg.toolStatus = undefined;
          }

          rMsg.content += chunk;
          rMsg.displayContent = rMsg.content;
          scrollToBottom();
        }
      }
    }

    // 流结束兜底：如果内容为空（后端无输出或异常），显示错误提示而非空白气泡
    stopLoadingStages();
    stopThinkingTimer();
    isLoading.value = false;
    rMsg.thinking = false;
    rMsg.typing = false;
    if (!rMsg.content.trim()) {
      rMsg.content = '抱歉，AI 助手未能生成回复。请检查后端服务是否正常运行，或稍后再试。';
      rMsg.displayContent = rMsg.content;
    }

    // 图谱/RAG 检索成功后，延迟 600ms 自动追加 LLM 综合分析
    if ((rMsg.sourceType === 'graph' || rMsg.sourceType === 'rag') && rMsg.content.trim()) {
      setTimeout(() => triggerAutoAnalysis(userMessage), 600);
    }

  } catch {
    // 降级：流式失败时用普通请求兜底
    if (!streamSuccess) {
      try {
        const response = await jobApi.chat({ message: userMessage, session_id: sessionId.value });
        const dataPayload = (response as any)?.data || response;
        const aiText = dataPayload?.response || dataPayload?.data?.response || '抱歉，未收到有效回复';
        newMsg.content = aiText;
        newMsg.displayContent = '';
        newMsg.useRag = !!(dataPayload?.rag_trace);
        stopLoadingStages();
        stopThinkingTimer();
        isLoading.value = false;
        newMsg.thinking = false;
        await pushMsgBubble();
        await typeMessage(rMsg);
        return;
      } catch {
        newMsg.content = '抱歉，AI 服务暂时繁忙，请稍后再试。';
        newMsg.displayContent = newMsg.content;
        newMsg.thinking = false;
        await pushMsgBubble();
      }
    }
    stopLoadingStages();
    stopThinkingTimer();
    isLoading.value = false;
    rMsg.thinking = false;
    rMsg.typing = false;
  } finally {
    stopLoadingStages();
    stopThinkingTimer();
    isLoading.value = false;
    activeReader.value = null;
    saveHistory(); // finally 统一保存，避免重复调用
  }
};

// ── 点击建议问题
const sendSuggestion = (q: string) => {
  if (isLoading.value) return;
  inputMessage.value = q;
  handleSend();
};

// ── 多会话历史持久化 ─────────────────────────────────────────────
interface SessionSummary {
  id: string;
  title: string;       // 取第一条用户消息前20字
  timestamp: number;
  messageCount: number; // 用户消息数（问了几个问题）
}

const SESSIONS_INDEX_KEY = 'chat_sessions_v1';
const MAX_SESSIONS = 20;        // 最多保存20条会话
const MAX_STORED_MESSAGES = 60; // 每条会话最多60条消息

const sessions = ref<SessionSummary[]>([]);
const showSuggestions = ref(false); // 侧边栏 tab：false=历史，true=快速提问

// 加载会话索引
const loadSessions = () => {
  try {
    const raw = localStorage.getItem(SESSIONS_INDEX_KEY);
    if (raw) {
      const data = JSON.parse(raw);
      if (Array.isArray(data)) sessions.value = data;
    }
  } catch { /* 格式异常忽略 */ }
};

// 保存当前会话的消息 + 更新索引
const saveHistory = () => {
  const toSave = messages.value
    .filter(m => !m.typing && !m.thinking)
    .map(m => ({
      role: m.role,
      content: m.content,
      displayContent: m.content,
      timestamp: m.timestamp,
      sourceType: m.sourceType ?? null,
      isAutoAnalysis: m.isAutoAnalysis ?? false,
    }))
    .slice(-MAX_STORED_MESSAGES);

  if (toSave.length === 0) return;

  // 按 sessionId 存消息
  localStorage.setItem(`chat_msg_${sessionId.value}`, JSON.stringify(toSave));

  // 更新索引
  const firstUser = toSave.find(m => m.role === 'user');
  const rawTitle = firstUser?.content ?? '新对话';
  const title = rawTitle.length > 20 ? rawTitle.slice(0, 20) + '…' : rawTitle;

  const idx = sessions.value.findIndex(s => s.id === sessionId.value);
  const summary: SessionSummary = {
    id: sessionId.value,
    title,
    timestamp: Date.now(),
    messageCount: toSave.filter(m => m.role === 'user').length,
  };
  if (idx >= 0) {
    sessions.value[idx] = summary;
  } else {
    sessions.value.unshift(summary);
    // 超出上限时删除最旧的会话数据
    if (sessions.value.length > MAX_SESSIONS) {
      const removed = sessions.value.splice(MAX_SESSIONS);
      removed.forEach(s => localStorage.removeItem(`chat_msg_${s.id}`));
    }
  }
  localStorage.setItem(SESSIONS_INDEX_KEY, JSON.stringify(sessions.value));
};

// 切换到某条历史会话
const switchToSession = (id: string) => {
  if (isLoading.value) return;
  try {
    const raw = localStorage.getItem(`chat_msg_${id}`);
    if (!raw) return;
    const data = JSON.parse(raw) as ChatMessage[];
    if (Array.isArray(data) && data.length > 0) {
      messages.value = data;
      sessionId.value = id;
      nextTick(() => scrollToBottom());
    }
  } catch { /* 格式异常忽略 */ }
};

// 删除某条历史会话
const deleteSession = (id: string) => {
  localStorage.removeItem(`chat_msg_${id}`);
  sessions.value = sessions.value.filter(s => s.id !== id);
  localStorage.setItem(SESSIONS_INDEX_KEY, JSON.stringify(sessions.value));
  // 删除的是当前会话则清空界面
  if (id === sessionId.value) {
    messages.value = [];
    sessionId.value = `chat_${Date.now()}`;
  }
};

// 初次加载：迁移旧格式 + 加载最近一条会话
const loadHistory = () => {
  loadSessions();
  // 迁移旧格式（chat_history_v1 → 新格式）
  const oldRaw = localStorage.getItem('chat_history_v1');
  if (oldRaw) {
    try {
      const oldData = JSON.parse(oldRaw) as ChatMessage[];
      if (Array.isArray(oldData) && oldData.length > 0) {
        messages.value = oldData;
        saveHistory(); // 存入新格式
        localStorage.removeItem('chat_history_v1');
        return;
      }
    } catch { /* 忽略 */ }
  }
  // 加载最近一条会话
  if (sessions.value.length > 0) {
    switchToSession(sessions.value[0].id);
  }
};

// 格式化会话时间
const formatSessionTime = (ts: number): string => {
  const d = new Date(ts);
  const diffMs = Date.now() - ts;
  const diffDays = Math.floor(diffMs / 86400000);
  if (diffDays === 0) {
    return `今天 ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
  }
  if (diffDays === 1) return '昨天';
  if (diffDays < 7) return `${diffDays} 天前`;
  return `${d.getMonth() + 1}/${d.getDate()}`;
};

// ── 清空 / 新对话
const clearChat = () => {
  // 保存当前会话再新建
  if (messages.value.filter(m => !m.typing && !m.thinking).length > 0) {
    saveHistory();
  }
  stopLoadingStages();
  messages.value = [];
  isLoading.value = false;
  sessionId.value = `chat_${Date.now()}`;
};

// ── 快捷：发送简历给 AI 分析
// 用 ref 而非 computed，因为 localStorage 不是响应式数据，
// computed 只会计算一次；在 onMounted/onActivated 里手动刷新
const hasResume = ref(false);
const refreshHasResume = () => {
  hasResume.value = (localStorage.getItem('resume_raw_text') || '').trim().length > 50;
};
const sendResumeToAI = () => {
  if (isLoading.value) return;
  const resumeText = localStorage.getItem('resume_raw_text') || '';
  if (!resumeText.trim()) return;
  inputMessage.value =
    `请帮我分析以下简历，给出综合评分、优势、不足以及针对 AI/后端方向的改进建议：\n\n${resumeText.slice(0, 2000)}`;
  handleSend();
};

onMounted(async () => {
  loadHistory();
  refreshHasResume();
  inputRef.value?.focus();
  // 来自 MatchDashboard 的跨页面跳转消息（首次挂载走这里）
  const pending = localStorage.getItem('chat_pending_message');
  if (pending) {
    localStorage.removeItem('chat_pending_message');
    // 读取并应用跨页面指定的模式（如 MatchDashboard 规划类问题指定 llm）
    const pendingMode = localStorage.getItem('chat_pending_mode') as 'auto' | 'graph' | 'rag' | 'llm' | null;
    if (pendingMode) {
      localStorage.removeItem('chat_pending_mode');
      selectedMode.value = pendingMode;
    }
    await nextTick();
    inputMessage.value = pending;
    handleSend();
  }
});

// keep-alive 唤醒时：滚动到最新消息 + 重新聚焦 + 处理跨页面跳转消息
onActivated(async () => {
  await nextTick();
  if (messagesContainerRef.value) {
    messagesContainerRef.value.scrollTop = messagesContainerRef.value.scrollHeight;
  }
  refreshHasResume(); // 每次激活重新检查简历状态，保证按钮及时出现
  inputRef.value?.focus();
  // MatchDashboard 等跨页面跳转带来的待发消息（keep-alive 复活走这里）
  const pending = localStorage.getItem('chat_pending_message');
  if (pending) {
    localStorage.removeItem('chat_pending_message');
    const pendingMode = localStorage.getItem('chat_pending_mode') as 'auto' | 'graph' | 'rag' | 'llm' | null;
    if (pendingMode) {
      localStorage.removeItem('chat_pending_mode');
      selectedMode.value = pendingMode;
    }
    await nextTick();
    inputMessage.value = pending;
    handleSend();
  }
});

// keep-alive 休眠时：清理所有后台定时器 + 取消 SSE 流，避免资源空转
onDeactivated(() => {
  stopLoadingStages();
  stopThinkingTimer();
  if (activeReader.value) {
    activeReader.value.cancel().catch(() => {});
    activeReader.value = null;
  }
  isLoading.value = false;
});
</script>

<style scoped lang="scss">
.chat-page {
  display: flex;
  height: calc(100vh - 64px);
  overflow: hidden;
  background: transparent;

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // 左侧边栏
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  .chat-sidebar {
    width: 240px;
    flex-shrink: 0;
    background: rgba(255,255,255,0.03);
    border-right: 1px solid rgba(255,255,255,0.07);
    display: flex;
    flex-direction: column;
    padding: 20px 16px;
    gap: 20px;
    overflow-y: auto;

    // AI 身份
    .ai-identity {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 14px;
      background: rgba(99,102,241,0.08);
      border: 1px solid rgba(99,102,241,0.2);
      border-radius: 12px;

      .ai-avatar-lg {
        position: relative;
        width: 44px; height: 44px;
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        flex-shrink: 0;
        box-shadow: 0 0 0 3px rgba(99,102,241,0.2);

        .ai-avatar-char {
          font-size: 18px; font-weight: 800;
          color: #fff; letter-spacing: 0;
          line-height: 1; user-select: none;
        }

        .ai-online-dot {
          position: absolute; bottom: 1px; right: 1px;
          width: 10px; height: 10px;
          background: #22c55e; border-radius: 50%;
          border: 2px solid #0f1117;
          box-shadow: 0 0 6px #22c55e;
        }
      }

      .ai-identity-info {
        .ai-name {
          font-size: 14px; font-weight: 700; color: #e2e8f0;
          margin-bottom: 2px;
        }
        .ai-model {
          font-size: 11px; color: #64748b;
        }
      }
    }

    // Tab 切换（历史 / 快速提问）
    .sidebar-tabs {
      display: flex; gap: 4px;
      padding: 0 4px; margin-bottom: 4px; flex-shrink: 0;

      .stab {
        flex: 1; padding: 6px 8px;
        border: none; border-radius: 8px; cursor: pointer;
        font-size: 12px; font-weight: 500;
        background: transparent; color: #64748b;
        transition: all 0.15s;
        display: flex; align-items: center; justify-content: center; gap: 4px;

        &:hover { background: rgba(255,255,255,0.06); color: #94a3b8; }
        &.active { background: rgba(99,102,241,0.15); color: #a5b4fc; }

        .stab-count {
          font-size: 10px; min-width: 16px; height: 16px; line-height: 16px;
          text-align: center; border-radius: 8px;
          background: rgba(99,102,241,0.25); color: #a5b4fc; padding: 0 4px;
        }
      }
    }

    // 历史对话列表
    .history-list {
      flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 2px;
      padding-right: 2px;

      &::-webkit-scrollbar { width: 3px; }
      &::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 2px; }

      .history-empty {
        flex: 1; display: flex; flex-direction: column;
        align-items: center; justify-content: center; gap: 6px;
        padding: 24px 0; color: #475569;

        .he-icon { font-size: 28px; opacity: 0.5; }
        .he-text { font-size: 13px; font-weight: 500; color: #475569; }
        .he-hint { font-size: 11px; color: #334155; }
      }

      .history-item {
        display: flex; align-items: center; gap: 6px;
        padding: 8px 10px; border-radius: 8px; cursor: pointer;
        border: 1px solid transparent;
        transition: all 0.15s;

        &:hover {
          background: rgba(255,255,255,0.05);
          border-color: rgba(255,255,255,0.06);
          .hi-del { opacity: 1; }
        }
        &.active {
          background: rgba(99,102,241,0.1);
          border-color: rgba(99,102,241,0.2);
          .hi-title { color: #a5b4fc; }
        }

        .hi-body {
          flex: 1; min-width: 0;

          .hi-title {
            font-size: 12.5px; font-weight: 500; color: #cbd5e1;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
            line-height: 1.4;
          }
          .hi-meta {
            font-size: 10.5px; color: #475569; margin-top: 2px;
            display: flex; align-items: center; gap: 4px;
            .hi-sep { opacity: 0.5; }
          }
        }

        .hi-del {
          flex-shrink: 0; width: 18px; height: 18px; border-radius: 4px;
          border: none; background: transparent; color: #475569;
          font-size: 10px; cursor: pointer; opacity: 0; transition: all 0.15s;
          display: flex; align-items: center; justify-content: center;
          &:hover { background: rgba(239,68,68,0.15); color: #f87171; opacity: 1 !important; }
        }
      }
    }

    // 建议问题
    .suggestion-section {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 16px;

      .suggestion-group {
        .group-title {
          font-size: 11px; font-weight: 600; color: #64748b;
          letter-spacing: 0.5px; text-transform: uppercase;
          margin-bottom: 7px; padding: 0 2px;
        }

        .suggestion-btn {
          display: block; width: 100%;
          text-align: left; padding: 8px 12px;
          margin-bottom: 5px;
          background: rgba(255,255,255,0.03);
          border: 1px solid rgba(255,255,255,0.07);
          border-radius: 8px;
          color: #94a3b8; font-size: 12.5px;
          cursor: pointer; transition: all 0.18s;
          white-space: nowrap; overflow: hidden; text-overflow: ellipsis;

          &:hover:not(:disabled) {
            background: rgba(99,102,241,0.1);
            border-color: rgba(99,102,241,0.25);
            color: #a5b4fc;
          }
          &:disabled { opacity: 0.4; cursor: default; }
        }
      }
    }

    // 底部
    // 简历快捷按钮
    .resume-quick-btn {
      width: 100%;
      padding: 10px 14px;
      background: rgba(16,185,129,0.08);
      border: 1px solid rgba(16,185,129,0.25);
      border-radius: 10px;
      color: #34d399; font-size: 13px; font-weight: 600;
      cursor: pointer; transition: all 0.18s; text-align: left;
      &:hover:not(:disabled) {
        background: rgba(16,185,129,0.15);
        border-color: rgba(16,185,129,0.45);
      }
      &:disabled { opacity: 0.4; cursor: not-allowed; }
    }

    .resume-quick-hint {
      font-size: 11px; color: #374151; text-align: center;
      padding: 8px 0; line-height: 1.6;
    }

    .sidebar-footer {
      padding-top: 12px;
      border-top: 1px solid rgba(255,255,255,0.07);
      display: flex;
      align-items: center;
      justify-content: space-between;

      .new-session-btn {
        display: flex; align-items: center; gap: 5px;
        padding: 7px 14px;
        background: rgba(99,102,241,0.1);
        border: 1px solid rgba(99,102,241,0.25);
        border-radius: 8px; color: #a5b4fc; font-size: 13px;
        cursor: pointer; transition: all 0.18s;
        &:hover { background: rgba(99,102,241,0.2); }
      }

      .session-stats {
        font-size: 11.5px; color: #475569;
      }
    }
  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // 主聊天区
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  .chat-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
    overflow: hidden;

    // 顶部栏
    .chat-topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 24px;
      height: 52px;
      border-bottom: 1px solid rgba(255,255,255,0.07);
      background: rgba(255,255,255,0.02);
      flex-shrink: 0;
      overflow: hidden;

      .topbar-left {
        display: flex; align-items: center; gap: 10px;
        min-width: 0; flex: 1; overflow: hidden;

        .topbar-title {
          font-size: 15px; font-weight: 700; color: #e2e8f0;
          white-space: nowrap; flex-shrink: 0;
        }

        .topbar-tags {
          display: flex; gap: 6px; flex-shrink: 0;

          .tag-chip {
            font-size: 10.5px; padding: 2px 8px;
            background: rgba(99,102,241,0.1);
            border: 1px solid rgba(99,102,241,0.2);
            border-radius: 20px; color: #a5b4fc;
            white-space: nowrap;
          }
        }
      }

      .topbar-status {
        display: flex; align-items: center; gap: 6px;
        font-size: 12px; color: #64748b; flex-shrink: 0; margin-left: 12px;

        .status-dot {
          width: 7px; height: 7px;
          border-radius: 50%; background: #22c55e;
          box-shadow: 0 0 5px #22c55e;
          &.loading {
            background: #f59e0b; box-shadow: 0 0 5px #f59e0b;
            animation: pulse-dot 1s ease-in-out infinite;
          }
        }
      }
    }

    // 消息区
    .chat-messages {
      flex: 1;
      overflow-y: auto;
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 20px;
      scroll-behavior: smooth;

      // 欢迎屏
      .welcome-screen {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        flex: 1;
        padding: 40px 20px;
        text-align: center;

        .welcome-avatar {
          width: 72px; height: 72px;
          margin: 0 auto 20px;
          background: linear-gradient(135deg, #6366f1, #8b5cf6);
          border-radius: 50%;
          display: flex; align-items: center; justify-content: center;
          box-shadow: 0 0 0 6px rgba(99,102,241,0.12), 0 8px 24px rgba(99,102,241,0.3);
          animation: float 3s ease-in-out infinite;

          .welcome-ai-char {
            font-size: 28px; font-weight: 800;
            color: #fff; letter-spacing: 0;
            line-height: 1; user-select: none;
          }
        }

        .welcome-title {
          font-size: 22px; font-weight: 700; color: #e2e8f0;
          margin: 0 0 10px;
        }

        .welcome-desc {
          font-size: 14px; color: #64748b; max-width: 420px;
          line-height: 1.6; margin: 0 0 28px;
        }

        .welcome-cards {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
          width: 100%;
          max-width: 560px;

          .welcome-card {
            display: flex; align-items: flex-start; gap: 12px;
            padding: 14px 16px;
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            cursor: pointer; transition: all 0.2s;
            text-align: left;

            &:hover {
              background: rgba(99,102,241,0.1);
              border-color: rgba(99,102,241,0.3);
              transform: translateY(-2px);
            }

            .wc-icon { font-size: 20px; flex-shrink: 0; }

            .wc-body {
              .wc-title { font-size: 13px; font-weight: 600; color: #e2e8f0; margin-bottom: 4px; }
              .wc-example { font-size: 11.5px; color: #64748b; line-height: 1.4; }
            }
          }
        }
      }

      // 消息行
      .msg-row {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        animation: msg-in 0.22s ease both;

        &.msg-user {
          flex-direction: row-reverse;

          .msg-col { align-items: flex-end; }

          .msg-bubble {
            max-width: 60%;
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            border: none;
            border-radius: 18px 4px 18px 18px;

            .msg-text { color: #fff; }
            .msg-time { color: rgba(255,255,255,0.5); }
          }
        }

        &.msg-ai {
          .msg-bubble {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 4px 18px 18px 18px;
          }
        }

        // 气泡列（气泡 + 操作栏的垂直容器）
        .msg-col {
          display: flex;
          flex-direction: column;
          align-items: flex-start;
          gap: 4px;
          min-width: 0;
        }

        // 消息操作栏
        .msg-actions {
          display: flex;
          align-items: center;
          gap: 4px;
          padding: 2px 4px;

          .ma-btn {
            display: flex; align-items: center; justify-content: center;
            width: 28px; height: 28px;
            border: none; border-radius: 7px;
            background: rgba(255,255,255,0.05);
            cursor: pointer; font-size: 13px;
            color: #64748b; transition: all 0.15s;

            &:hover { background: rgba(99,102,241,0.15); color: #a5b4fc; }
            &.ma-active { background: rgba(99,102,241,0.2); color: #818cf8; }
          }
        }


        .msg-avatar {
          width: 34px; height: 34px;
          border-radius: 50%;
          display: flex; align-items: center; justify-content: center;
          flex-shrink: 0; margin-top: 2px;

          &.msg-avatar-ai {
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            box-shadow: 0 0 0 2px rgba(99,102,241,0.2);
          }
          &.msg-avatar-user {
            background: rgba(255,255,255,0.1);
            border: 1.5px solid rgba(255,255,255,0.12);
          }
          .avatar-char {
            font-size: 13px; font-weight: 700;
            color: #fff; letter-spacing: 0;
            line-height: 1; user-select: none;
          }
        }

        .msg-bubble {
          max-width: 75%;
          padding: 12px 16px;

          .msg-ai-header {
            display: flex; align-items: center; gap: 6px; margin-bottom: 6px;

            .msg-model-tag {
              font-size: 11px; font-weight: 600; color: #818cf8;
            }
            // 来源标签（图谱/RAG/LLM 三种）
            .msg-source-tag {
              font-size: 10px; padding: 1px 7px;
              border-radius: 10px; user-select: none; transition: all 0.15s;

              &.tag-graph {
                background: rgba(56,189,248,0.1); color: #7dd3fc;
                border: 1px solid rgba(56,189,248,0.25);
                cursor: pointer;
                &:hover { background: rgba(56,189,248,0.18); }
                &.expanded { background: rgba(56,189,248,0.2); border-color: rgba(56,189,248,0.4); }
              }
              &.tag-rag {
                background: rgba(251,146,60,0.1); color: #fdba74;
                border: 1px solid rgba(251,146,60,0.25);
                cursor: pointer;
                &:hover { background: rgba(251,146,60,0.18); }
                &.expanded { background: rgba(251,146,60,0.2); border-color: rgba(251,146,60,0.4); }
              }
              &.tag-llm {
                background: rgba(148,163,184,0.1); color: #94a3b8;
                border: 1px solid rgba(148,163,184,0.2);
              }
              &.tag-analysis {
                background: rgba(139,92,246,0.12); color: #c4b5fd;
                border: 1px solid rgba(139,92,246,0.3);
                animation: analysis-pulse 2s ease-in-out 3;
              }
            }
          }

          // 自动追加 AI 综合分析气泡的左侧高亮边框
          &.msg-bubble--analysis {
            border-left: 3px solid rgba(139,92,246,0.5);
            background: rgba(139,92,246,0.04);
          }

          // 来源详情面板（图谱/RAG 点击展开）
          .rag-source-panel {
            margin: 0 0 8px;
            padding: 10px 14px;
            background: rgba(251,146,60,0.05);
            border: 1px solid rgba(251,146,60,0.15);
            border-radius: 10px;
            animation: msg-in 0.15s ease both;

            &.panel-graph {
              background: rgba(56,189,248,0.05);
              border-color: rgba(56,189,248,0.15);
              .rsp-title { color: #7dd3fc; }
            }
            .rsp-title {
              font-size: 11.5px; font-weight: 600; color: #fdba74; margin-bottom: 7px;
            }
            .rsp-body {
              display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 6px;

              .rsp-badge {
                font-size: 10.5px; padding: 2px 8px;
                background: rgba(251,146,60,0.08);
                border: 1px solid rgba(251,146,60,0.2);
                border-radius: 20px; color: #fdba74;
                &.badge-graph {
                  background: rgba(56,189,248,0.08);
                  border-color: rgba(56,189,248,0.2);
                  color: #7dd3fc;
                }
              }
              .rsp-count {
                font-size: 10.5px; padding: 2px 8px;
                background: rgba(99,102,241,0.1);
                border: 1px solid rgba(99,102,241,0.2);
                border-radius: 20px; color: #a5b4fc;
              }
            }
            .rsp-desc {
              font-size: 11px; color: #64748b; line-height: 1.5;
            }
          }

          .msg-text {
            font-size: 14px; line-height: 1.75; color: #e2e8f0;
            word-break: break-word;

            // Markdown 元素样式
            :deep(.md-h3) { font-size: 14px; font-weight: 700; color: #a5b4fc; margin: 12px 0 6px; padding: 5px 10px; background: rgba(99,102,241,0.08); border-left: 3px solid #6366f1; border-radius: 0 6px 6px 0; &:first-child { margin-top: 0; } }
            :deep(.md-h4) { font-size: 13.5px; font-weight: 600; color: #c4b5fd; margin: 10px 0 5px; }
            :deep(.md-p) { margin: 5px 0; }
            :deep(.md-spacer) { height: 5px; }
            :deep(strong) { color: #c4b5fd; font-weight: 700; }
            :deep(em) { color: #94a3b8; font-style: italic; }
            :deep(.md-code) { background: rgba(99,102,241,0.15); color: #a5b4fc; padding: 1px 6px; border-radius: 4px; font-size: 12.5px; font-family: 'Consolas', monospace; }
            :deep(.md-quote) { margin: 7px 0; padding: 7px 12px; border-left: 3px solid rgba(99,102,241,0.5); background: rgba(99,102,241,0.06); border-radius: 0 6px 6px 0; color: #94a3b8; font-style: italic; }
            :deep(.md-li-ul) { list-style: none; padding: 3px 0 3px 18px; position: relative; &::before { content: ''; position: absolute; left: 5px; top: 50%; transform: translateY(-50%); width: 5px; height: 5px; border-radius: 50%; background: rgba(99,102,241,0.7); } }
            :deep(.md-li-ol) { list-style: none; display: flex; align-items: baseline; gap: 8px; padding: 4px 0; .md-ol-num { flex-shrink: 0; display: inline-flex; align-items: center; justify-content: center; width: 19px; height: 19px; border-radius: 50%; background: rgba(99,102,241,0.18); border: 1px solid rgba(99,102,241,0.3); color: #a5b4fc; font-size: 10px; font-weight: 700; } }
            :deep(.md-table-wrap) { overflow-x: auto; margin: 10px 0; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08); }
            :deep(.md-table) { width: 100%; border-collapse: collapse; font-size: 13px; th { padding: 8px 12px; background: rgba(99,102,241,0.1); color: #a5b4fc; font-weight: 700; border-bottom: 1px solid rgba(255,255,255,0.08); } td { padding: 7px 12px; color: #cbd5e1; border-bottom: 1px solid rgba(255,255,255,0.05); } tr:last-child td { border-bottom: none; } }
            // 工具调用状态行（以 emoji 开头的进度行）
            :deep(.md-p):has-text { }
            &.msg-text-ai {
              // 分割线
              :deep(hr), :deep(.md-hr) {
                border: none;
                border-top: 1px dashed rgba(99,102,241,0.25);
                margin: 10px 0;
              }
            }
          }

          .msg-time {
            font-size: 11px; color: #475569;
            text-align: right; margin-top: 6px;
          }
        }
      }

      // 打字机光标
      .typing-cursor {
        display: inline-block;
        color: #6366f1; font-size: 14px;
        animation: cursor-blink 0.8s step-end infinite;
        vertical-align: middle; margin-left: 1px;
      }

      // ── 思考中旋转圈（Cursor / 豆包风格）
      .msg-thinking {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 4px 0;

        .thinking-ring {
          width: 17px; height: 17px; flex-shrink: 0;
          border-radius: 50%;
          border: 2px solid rgba(99, 102, 241, 0.18);
          border-top-color: #818cf8;
          border-right-color: rgba(99, 102, 241, 0.55);
          animation: thinking-spin 0.72s cubic-bezier(0.4, 0, 0.2, 1) infinite;
        }

        .thinking-label {
          font-size: 13px;
          color: rgba(255, 255, 255, 0.45);
          letter-spacing: 0.2px;
          transition: color 0.3s;
        }

        .thinking-timer {
          font-size: 11px;
          color: rgba(255, 255, 255, 0.2);
          margin-left: 2px;
        }
      }

      // 等待气泡（HTTP 连接前短暂显示）
      .msg-row-pending {
        opacity: 0.7;
        .msg-avatar-ai {
          background: rgba(99, 102, 241, 0.3) !important;
          .avatar-char { color: #818cf8 !important; }
        }
      }
    }

    @keyframes thinking-spin {
      from { transform: rotate(0deg); }
      to   { transform: rotate(360deg); }
    }

    // 输入区
    .chat-input-area {
      flex-shrink: 0;
      padding: 16px 24px 20px;
      border-top: 1px solid rgba(255,255,255,0.07);
      background: rgba(255,255,255,0.02);

      // ── 模式选择器 ────────────────────────────────────
      .mode-selector {
        display: flex;
        gap: 6px;
        margin-bottom: 10px;
        align-items: center;

        &::before {
          content: '检索方式';
          font-size: 11px;
          color: #64748b;
          margin-right: 4px;
          white-space: nowrap;
        }

        .mode-btn {
          display: flex;
          align-items: center;
          gap: 4px;
          padding: 4px 10px;
          border-radius: 20px;
          border: 1px solid rgba(255,255,255,0.1);
          background: rgba(255,255,255,0.04);
          color: #94a3b8;
          font-size: 12px;
          cursor: pointer;
          transition: all .18s ease;

          .mode-icon { font-size: 13px; }
          .mode-label { letter-spacing: .3px; }

          &:hover {
            border-color: rgba(139,92,246,0.5);
            color: #c4b5fd;
            background: rgba(139,92,246,0.08);
          }

          &.active {
            background: rgba(139,92,246,0.2);
            border-color: rgba(139,92,246,0.6);
            color: #e2d9fb;
            font-weight: 600;
          }
        }
      }

      .input-row {
        display: flex; gap: 10px; align-items: flex-end;

        .chat-textarea {
          flex: 1;
          resize: none;
          padding: 12px 16px;
          background: rgba(255,255,255,0.05);
          border: 1.5px solid rgba(255,255,255,0.1);
          border-radius: 14px;
          color: #e2e8f0; font-size: 14px; line-height: 1.6;
          outline: none; transition: border-color 0.2s;
          font-family: inherit;
          max-height: 140px; overflow-y: auto;

          &::placeholder { color: #475569; }
          &:focus {
            border-color: rgba(99,102,241,0.5);
            box-shadow: 0 0 0 3px rgba(99,102,241,0.08);
          }
        }

        .send-btn {
          width: 44px; height: 44px; border-radius: 12px;
          border: none; cursor: pointer;
          display: flex; align-items: center; justify-content: center;
          background: rgba(255,255,255,0.08);
          transition: all 0.2s; flex-shrink: 0;

          .send-icon {
            font-size: 18px; font-weight: 700; color: #475569; line-height: 1;
          }

          // 停止图标（红色实心方块）
          .stop-icon {
            width: 14px; height: 14px;
            background: #fff;
            border-radius: 3px;
            display: block;
          }

          &.active {
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            box-shadow: 0 4px 12px rgba(99,102,241,0.3);
            .send-icon { color: #fff; }
          }
          // 生成中：红色底 + 停止图标
          &.stop {
            background: rgba(239,68,68,0.15);
            border: 1.5px solid rgba(239,68,68,0.3);
            cursor: pointer;
            &:hover { background: rgba(239,68,68,0.25); transform: scale(1.05); }
            .stop-icon { background: #f87171; }
          }
          &:hover.active { transform: scale(1.06); }
          &:disabled:not(.stop) { cursor: not-allowed; }
        }
      }

      .input-hint {
        display: flex; justify-content: space-between;
        margin-top: 7px; padding: 0 4px;
        font-size: 11.5px; color: #334155;

        .char-count { color: #334155; }
      }
    }
  }
}

// 关键帧
@keyframes msg-in {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes cursor-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}
@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-5px); }
}
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
@keyframes analysis-pulse {
  0%, 100% { box-shadow: none; }
  50% { box-shadow: 0 0 6px rgba(139,92,246,0.5); }
}

// 响应式
@media (max-width: 900px) {
  .chat-page {
    .chat-sidebar { display: none; }
    .chat-messages { padding: 16px; }
    .msg-bubble { max-width: 85% !important; }
    .welcome-cards { grid-template-columns: 1fr !important; }
    .topbar-tags { display: none !important; }
  }
}
</style>
