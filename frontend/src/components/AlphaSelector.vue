<template>
  <div class="alpha-selector">
    <!-- 已选标签展示区 -->
    <div class="selected-tags" v-if="selected.length">
      <SkillTag
        v-for="item in selected"
        :key="item"
        :label="item"
        closable
        @close="remove(item)"
        class="selected-tag"
      />
      <span class="clear-all" @click="selected = []">清空</span>
    </div>

    <!-- 下拉触发按钮 -->
    <div class="trigger-btn" ref="triggerRef" @click="toggleOpen">
      <el-icon><Location v-if="mode === 'city'" /><Cpu v-else /></el-icon>
      {{ mode === 'city' ? '城市' : '技能' }}
      <el-tag size="small" v-if="selected.length" type="primary">
        {{ selected.length }}
      </el-tag>
      <el-icon><ArrowDown /></el-icon>
    </div>

    <!-- 下拉面板：Teleport 到 body，彻底跳出所有 stacking context -->
    <Teleport to="body">
      <transition name="dropdown">
        <div
          v-if="open"
          class="selector-panel glass-card alpha-selector-teleport"
          :style="panelStyle"
        >
          <!-- 搜索框 -->
          <el-input
            v-model="query"
            :placeholder="`搜索${mode === 'city' ? '城市' : '技能'}...`"
            :prefix-icon="Search"
            clearable
            @input="filterItems"
          />

          <!-- 加载中提示 -->
          <div v-if="skillsLoading" class="skills-loading-hint">
            <el-icon class="is-loading"><Loading /></el-icon>
            正在从图数据库加载技能列表...
          </div>
          <div v-else-if="mode === 'skill' && dynamicSkills.length > 0" class="skills-count-hint">
            共 {{ dynamicSkills.length }} 个技能
          </div>

          <!-- 热门 -->
          <div class="hot-section">
            <span class="section-label">🔥 热门</span>
            <SkillTag
              v-for="item in hotItems"
              :key="item"
              :label="item"
              :type="selected.includes(item) ? 'primary' : 'info'"
              class="hot-tag"
              @click="toggle(item)"
            />
          </div>

          <el-divider />

          <!-- 字母索引 + 滚动列表 -->
          <div class="alpha-body">
            <!-- 左侧字母导航 -->
            <div class="alpha-index">
              <span
                v-for="letter in letters"
                :key="letter"
                @click="scrollTo(letter)"
                :class="{ active: activeLetter === letter }"
              >{{ letter }}</span>
            </div>
            <!-- 右侧列表 -->
            <div class="item-list" ref="listRef" @scroll="onScroll">
              <template v-for="(group, letter) in groupedItems" :key="letter">
                <div :id="`group-${letter}`" class="group-header">{{ letter }}</div>
                <div
                  v-for="item in group"
                  :key="item"
                  class="item-row"
                  :class="{ selected: selected.includes(item) }"
                  @click="toggle(item)"
                >
                  <el-icon v-if="selected.includes(item)"><Check /></el-icon>
                  {{ item }}
                </div>
              </template>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue';
import { ElMessage } from 'element-plus';
import { Location, Cpu, Search, ArrowDown, Check, Loading } from '@element-plus/icons-vue';
import SkillTag from '@/components/SkillTag.vue';
import { pinyin } from 'pinyin-pro';
import { jobApi } from '@/api/jobApi';
import { useAppStore } from '@/stores/app';

export interface AlphaSelectorProps {
  mode: 'city' | 'skill';
  max?: number;
}

const props = withDefaults(defineProps<AlphaSelectorProps>(), {
  max: 5
});

const emit = defineEmits<{
  'selection-change': [items: string[]]
}>();

// ── 城市数据（静态）────────────────────────────────────────
const CITIES = [
  '北京','长春','常德','成都','大连','东莞','佛山','福州',
  '广州','贵阳','哈尔滨','海口','合肥','呼和浩特',
  '开封','兰州','南昌','南京','苏州','上海','深圳',
  '太原','天津','武汉','无锡','芜湖','西安','厦门',
  '扬州','郑州','重庆','长沙'
];
const HOT_CITIES = ['北京','上海','广州','深圳','杭州','成都','天津','苏州'];

// ── 技能数据（从后端动态加载）────────────────────────────
const FALLBACK_SKILLS = [
  'AI/ML','Angular','AWS','C++','CSS','ChromaDB','Django','Docker',
  'FastAPI','Flutter','Go','Git','Java','JavaScript','Kubernetes',
  'LangChain','Linux','LLM','MongoDB','MySQL','Neo4j','Nginx',
  'Python','PyTorch','RAG','React','Redis','Spring Boot','SQL',
  'TypeScript','TensorFlow','Vue',
];
const HOT_SKILLS = ['Python','Java','React','Vue','Go','Docker','MySQL','Redis','FastAPI','AI/ML'];

const appStore = useAppStore();
const dynamicSkills = ref<string[]>([]);
const skillsLoading = ref(false);

const loadSkillsFromBackend = async () => {
  if (props.mode !== 'skill') return;
  // 优先使用 store 中已缓存的数据
  if (appStore.skillsLoaded && appStore.skillsList.length > 0) {
    dynamicSkills.value = appStore.skillsList;
    return;
  }
  if (dynamicSkills.value.length > 0) return;
  skillsLoading.value = true;
  try {
    await appStore.preloadSkills();
    if (appStore.skillsList.length > 0) {
      dynamicSkills.value = appStore.skillsList;
    } else {
      // 直接请求作为兜底
      const res = await jobApi.getSkillGraph({ limit: 500, min_demand: 0, edge_limit: 0 });
      if (res.data?.nodes?.length) {
        const names: string[] = res.data.nodes
          .map((n: any) => n.name || n.skill || n.id || '')
          .filter(Boolean)
          .sort();
        dynamicSkills.value = [...new Set(names)] as string[];
      }
    }
  } catch {
    // 静默失败，使用兜底列表
  } finally {
    skillsLoading.value = false;
  }
};

const ALL_ITEMS = computed(() => {
  if (props.mode === 'city') return CITIES;
  // store 已预加载 → 立即可用
  if (appStore.skillsLoaded && appStore.skillsList.length > 0) return appStore.skillsList;
  return dynamicSkills.value.length > 0 ? dynamicSkills.value : FALLBACK_SKILLS;
});
const hotItems = computed(() => props.mode === 'city' ? HOT_CITIES : HOT_SKILLS);

const query = ref('');
const open = ref(false);
const selected = ref<string[]>([]);
const listRef = ref<HTMLDivElement>();
const triggerRef = ref<HTMLDivElement>();
const activeLetter = ref('');
const panelStyle = ref<Record<string, string>>({});

const calcPanelPosition = () => {
  if (!triggerRef.value) return;
  const rect = triggerRef.value.getBoundingClientRect();
  const panelWidth = 400;
  // 防止超出右侧视口
  const left = Math.min(rect.left, window.innerWidth - panelWidth - 8);
  panelStyle.value = {
    position: 'fixed',
    top: `${rect.bottom + 8}px`,
    left: `${Math.max(8, left)}px`,
    width: `${panelWidth}px`,
    zIndex: '9999'
  };
};

const toggleOpen = async () => {
  open.value = !open.value;
  if (open.value) {
    await nextTick();
    calcPanelPosition();
    loadSkillsFromBackend(); // 首次打开时异步加载技能
  }
};

const closePanel = () => {
  open.value = false;
};

// 滚动时同步面板位置
const onWindowScroll = () => {
  if (open.value) calcPanelPosition();
};

// 点击外部关闭
const onDocumentMousedown = (e: MouseEvent) => {
  if (!open.value) return;
  const target = e.target as Node;
  if (triggerRef.value?.contains(target)) return;
  // 检查是否点击了 teleport 的面板内部
  const panel = document.querySelector('.alpha-selector-teleport');
  if (panel?.contains(target)) return;
  open.value = false;
};

onMounted(() => {
  window.addEventListener('scroll', onWindowScroll, true);
  document.addEventListener('mousedown', onDocumentMousedown);
});
onBeforeUnmount(() => {
  window.removeEventListener('scroll', onWindowScroll, true);
  document.removeEventListener('mousedown', onDocumentMousedown);
});

const filtered = computed(() =>
  query.value
    ? ALL_ITEMS.value.filter(i => i.toLowerCase().includes(query.value.toLowerCase()))
    : ALL_ITEMS.value
);

// 按拼音首字母分组
const groupedItems = computed(() => {
  const map: Record<string, string[]> = {};
  filtered.value.forEach(item => {
    // 获取第一个字符的拼音首字母
    let firstChar = item[0];
    // 如果是中文字符，转换为拼音首字母
    if (/[\u4e00-\u9fa5]/.test(firstChar)) {
      const pinyinResult = pinyin(firstChar, { toneType: 'none', type: 'array' });
      if (pinyinResult && pinyinResult[0]) {
        firstChar = pinyinResult[0][0].toUpperCase(); // 获取首字母并大写
      } else {
        firstChar = firstChar.toUpperCase(); // 如果转换失败，保持原样
      }
    } else {
      // 如果不是中文，直接取首字母并大写
      firstChar = firstChar.toUpperCase();
    }
    
    if (!map[firstChar]) map[firstChar] = [];
    map[firstChar].push(item);
  });
  return map;
});
const letters = computed(() => Object.keys(groupedItems.value).sort());

const toggle = (item: string) => {
  if (selected.value.includes(item)) {
    selected.value = selected.value.filter(i => i !== item);
  } else {
    if (selected.value.length >= props.max) {
      ElMessage.warning(`最多选择 ${props.max} 个`);
      return;
    }
    selected.value.push(item);
  }
};
const remove = (item: string) => { 
  selected.value = selected.value.filter(i => i !== item);
};
const scrollTo = async (letter: string) => {
  const el = document.getElementById(`group-${letter}`);
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    activeLetter.value = letter;
  }
};
const onScroll = () => {
  // 滚动时高亮当前分组字母
  for (const letter of letters.value) {
    const el = document.getElementById(`group-${letter}`);
    if (el && el.getBoundingClientRect().top >= 0) {
      activeLetter.value = letter;
      break;
    }
  }
};
const filterItems = () => {
  // 过滤逻辑已经在computed中实现
};

// 选择变化时对外 emit
watch(selected, (val) => {
  emit('selection-change', [...val]);
}, { deep: true });

defineExpose({
  selected,
  setSelected: (items: string[]) => {
    selected.value = items;
  }
});
</script>

<style scoped lang="scss">
.alpha-selector {
  position: relative;
  display: inline-block;

  .selected-tags {
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    flex-wrap: wrap;

    .selected-tag {
      margin: 2px 4px 2px 0;
    }

    .clear-all {
      margin-left: 8px;
      font-size: 12px;
      color: $primary-color;
      cursor: pointer;
      user-select: none;

      &:hover {
        text-decoration: underline;
      }
    }
  }

  .trigger-btn {
    display: flex;
    align-items: center;
    padding: 8px 12px;
    background: $bg-secondary;
    border: 1px solid $border-color;
    border-radius: 6px;
    cursor: pointer;
    transition: $transition-base;

    &:hover {
      border-color: $primary-color;
      background: rgba($primary-color, 0.1);
    }

    .el-icon {
      margin-right: 4px;
    }

    .el-tag {
      margin: 0 6px;
    }
  }

  .selector-panel {
    max-height: 500px;
    overflow: hidden;

    :deep(.el-input) {
      margin: 12px;
    }

    .skills-loading-hint, .skills-count-hint {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 2px 12px 6px;
      font-size: 12px;
      color: rgba(255,255,255,0.4);
    }

    .hot-section {
      padding: 0 12px 12px;
      .section-label {
        display: block;
        margin-bottom: 8px;
        font-size: 14px;
        color: $text-secondary;
      }
      .hot-tag {
        margin: 0 6px 6px 0;
        cursor: pointer;
      }
    }

    .alpha-body {
      display: flex;
      height: 300px;

      .alpha-index {
        width: 40px;
        padding: 8px 0;
        background: rgba(255, 255, 255, 0.03);
        display: flex;
        flex-direction: column;
        align-items: center;

        span {
          flex: 0 0 auto;
          padding: 4px;
          font-size: 12px;
          cursor: pointer;
          border-radius: 4px;
          width: 24px;
          height: 24px;
          display: flex;
          align-items: center;
          justify-content: center;

          &:hover,
          &.active {
            background: $primary-color;
            color: white;
          }
        }
      }

      .item-list {
        flex: 1;
        overflow-y: auto;
        padding: 8px 0;

        .group-header {
          padding: 8px 12px;
          background: rgba(255, 255, 255, 0.05);
          font-weight: bold;
          font-size: 14px;
        }

        .item-row {
          padding: 8px 12px;
          cursor: pointer;
          transition: $transition-base;
          display: flex;
          align-items: center;

          &:hover {
            background: rgba(255, 255, 255, 0.1);
          }

          &.selected {
            background: rgba($primary-color, 0.2);
            color: $primary-color;
          }

          .el-icon {
            margin-right: 6px;
          }
        }
      }
    }
  }

  .dropdown-enter-active,
  .dropdown-leave-active {
    transition: opacity 0.3s, transform 0.3s;
  }

  .dropdown-enter-from,
  .dropdown-leave-to {
    opacity: 0;
    transform: translateY(-10px);
  }
}

</style>

<!-- Teleport 出去的面板，不能用 scoped，需要全局样式 -->
<style lang="scss">
.alpha-selector-teleport {
  &.selector-panel {
    max-height: 500px;
    overflow: hidden;
    border-radius: 12px;
    background: rgba(15, 23, 42, 0.95);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);

    .el-input {
      margin: 12px;
      width: calc(100% - 24px);
    }

    .hot-section {
      padding: 0 12px 12px;
      .section-label {
        display: block;
        margin-bottom: 8px;
        font-size: 14px;
        color: rgba(255, 255, 255, 0.6);
      }
      .hot-tag {
        margin: 0 6px 6px 0;
        cursor: pointer;
      }
    }

    .alpha-body {
      display: flex;
      height: 280px;

      .alpha-index {
        width: 40px;
        padding: 8px 0;
        background: rgba(255, 255, 255, 0.03);
        display: flex;
        flex-direction: column;
        align-items: center;
        overflow-y: auto;

        span {
          flex: 0 0 auto;
          padding: 4px;
          font-size: 12px;
          cursor: pointer;
          border-radius: 4px;
          width: 24px;
          height: 24px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: rgba(255, 255, 255, 0.7);

          &:hover,
          &.active {
            background: #6366f1;
            color: white;
          }
        }
      }

      .item-list {
        flex: 1;
        overflow-y: auto;
        padding: 8px 0;

        .group-header {
          padding: 8px 12px;
          background: rgba(255, 255, 255, 0.05);
          font-weight: bold;
          font-size: 14px;
          color: rgba(255, 255, 255, 0.8);
        }

        .item-row {
          padding: 8px 12px;
          cursor: pointer;
          transition: background 0.2s;
          display: flex;
          align-items: center;
          color: rgba(255, 255, 255, 0.85);

          &:hover {
            background: rgba(255, 255, 255, 0.1);
          }

          &.selected {
            background: rgba(99, 102, 241, 0.2);
            color: #6366f1;
          }

          .el-icon {
            margin-right: 6px;
          }
        }
      }
    }
  }

  // Teleport 的过渡动画
  &.dropdown-enter-active,
  &.dropdown-leave-active {
    transition: opacity 0.25s, transform 0.25s;
  }

  &.dropdown-enter-from,
  &.dropdown-leave-to {
    opacity: 0;
    transform: translateY(-8px);
  }
}
</style>