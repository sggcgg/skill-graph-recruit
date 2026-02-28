<template>
  <div class="graph-page">
    <GlassCard class="graph-header">
      <div class="header-content">
        <h1 class="page-title">
          <el-icon><User /></el-icon>
          技能知识图谱
        </h1>
        <div class="header-controls">
          <el-input
            v-model="searchSkill"
            placeholder="搜索技能..."
            :prefix-icon="Search"
            style="width: 200px;"
            clearable
            @keyup.enter="handleSearch"
            @clear="handleSearchClear"
          />
          <el-button
            type="primary"
            style="margin-right: 16px;"
            @click="handleSearch"
          >
            搜索
          </el-button>
          <el-select v-model="layoutType" placeholder="布局类型" style="width: 120px; margin-right: 8px;">
            <el-option label="力导向" value="force" />
            <el-option label="圆形" value="circle" />
            <el-option label="网格" value="grid" />
          </el-select>
          <el-select v-model="graphLimit" placeholder="节点数量" style="width: 120px; margin-right: 8px;" @change="fetchGraphData">
            <el-option label="前 50 个" :value="50" />
            <el-option label="前 100 个" :value="100" />
            <el-option label="前 200 个" :value="200" />
            <el-option label="前 500 个" :value="500" />
          </el-select>
          <el-button @click="exportGraph">
            <el-icon><Download /></el-icon>
            导出
          </el-button>
        </div>
      </div>
    </GlassCard>

    <div class="graph-main">
      <!-- 控制面板 -->
      <GlassCard class="control-panel">
        <div class="panel-section">
          <h3>🎨 显示选项</h3>
          <div class="option-item">
            <el-checkbox v-model="showConnections">显示关联</el-checkbox>
          </div>
          <div class="option-item">
            <el-checkbox v-model="showWeights">显示权重</el-checkbox>
          </div>
          <div class="option-item">
            <el-checkbox v-model="enableAnimation">动画效果</el-checkbox>
          </div>
        </div>

        <div class="panel-section">
          <h3>🔍 筛选</h3>
          <div class="option-item">
            <span>技能类型:</span>
            <el-radio-group v-model="skillFilter" size="small">
              <el-radio-button label="all">全部</el-radio-button>
              <el-radio-button label="language">编程语言</el-radio-button>
              <el-radio-button label="framework">框架/库</el-radio-button>
              <el-radio-button label="tool">工具</el-radio-button>
              <el-radio-button label="domain">领域</el-radio-button>
            </el-radio-group>
          </div>
        </div>

        <div class="panel-section">
          <h3>📊 统计</h3>
          <div class="stats-item">
            节点: <span class="stat-value">{{ nodeCount }}</span>
          </div>
          <div class="stats-item">
            关系: <span class="stat-value">{{ edgeCount }}</span>
          </div>
          <div class="stats-item">
            平均度: <span class="stat-value">{{ averageDegree.toFixed(2) }}</span>
          </div>
        </div>
      </GlassCard>

      <!-- 图谱可视化区域 -->
      <GlassCard class="graph-container">
        <div id="knowledge-graph" class="graph-canvas"></div>
      </GlassCard>

      <!-- 节点详情面板 -->
      <GlassCard v-if="selectedNode" class="detail-panel">
        <div class="detail-header">
          <h3>{{ selectedNode.name }}</h3>
          <el-button type="danger" @click="selectedNode = null" circle>
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
        <div class="detail-content">
          <div class="detail-row">
            <span class="label">类型:</span>
            <span class="value">{{ selectedNode.category }}</span>
          </div>
          <div class="detail-row">
            <span class="label">关联技能:</span>
            <div class="value">
              <SkillTag
                v-for="related in selectedNode.related"
                :key="related.name"
                :label="related.name"
                :level="related.level"
              />
            </div>
          </div>
          <div class="detail-row">
            <span class="label">岗位数量:</span>
            <span class="value">{{ selectedNode.jobCount }} 个</span>
          </div>
          <div class="detail-row">
            <span class="label">平均薪资:</span>
            <span class="value">{{ selectedNode.avgSalary }}K</span>
          </div>
          <div class="detail-actions">
            <AIButton ai-type="graph" @click="exploreLearningPath(selectedNode)">
              <template #icon>
                <el-icon><Reading /></el-icon>
              </template>
              匹配看板分析
            </AIButton>
            <button class="ai-intro-btn" @click="fetchAIIntro(selectedNode)" :disabled="aiIntroLoading">
              <span v-if="aiIntroLoading" class="spin-dot"></span>
              <span v-else>✨</span>
              {{ aiIntroLoading ? 'AI 分析中...' : 'AI 介绍此技能' }}
            </button>
          </div>

          <!-- AI 技能介绍结果 -->
          <div v-if="aiIntroResult || aiIntroLoading" class="ai-intro-panel">
            <div class="ai-intro-header">
              <span class="ai-label">✨ Qwen3.5-Plus</span>
              <button v-if="aiIntroResult" class="close-btn" @click="aiIntroResult = ''; aiIntroSkill = ''">✕</button>
            </div>
            <div v-if="aiIntroLoading" class="ai-intro-skeleton">
              <div class="sk-line w85"></div>
              <div class="sk-line w65"></div>
              <div class="sk-line w90"></div>
              <div class="sk-line w55"></div>
            </div>
            <div v-else class="ai-intro-content" v-html="renderIntro(aiIntroResult)"></div>
          </div>
        </div>
      </GlassCard>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, nextTick, watch } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { User, Search, Download, Close, Reading } from '@element-plus/icons-vue';
import * as d3 from 'd3';
import GlassCard from '@/components/GlassCard.vue';
import SkillTag from '@/components/SkillTag.vue';
import AIButton from '@/components/AIButton.vue';
import { jobApi } from '@/api/jobApi';
import { renderMarkdown as _renderMd, buildSkillIntroPrompt } from '@/utils/aiPrompt';

const router = useRouter();

// 控制变量
const searchSkill = ref('');
const layoutType = ref('force');
const showConnections = ref(true);
const showWeights = ref(true);
const enableAnimation = ref(true);
const graphLimit = ref(100);
const skillFilter = ref('all');

// 图谱数据（allNodes/allEdges 保存完整数据，nodes/edges 是筛选后的视图）
const allNodes = ref<any[]>([]);
const allEdges = ref<any[]>([]);
const nodes = ref<any[]>([]);
const edges = ref<any[]>([]);
const selectedNode = ref<any>(null);
const loading = ref(false);

// 统计数据
const nodeCount = computed(() => nodes.value.length);
const edgeCount = computed(() => edges.value.length);
const averageDegree = computed(() => {
  if (nodes.value.length === 0) return 0;
  return (edges.value.length * 2) / nodes.value.length;
});

// 将 category 原始字符串映射为前端枚举值
const mapCategory = (c: string): string => {
  if (!c) return 'domain';
  if (c.includes('语言') || c.toLowerCase() === 'language') return 'language';
  if (c.includes('框架') || c.includes('库') || c.toLowerCase().includes('framework')) return 'framework';
  if (c.includes('工具') || c.includes('数据库') || c.includes('平台') || c.toLowerCase() === 'tool') return 'tool';
  return 'domain';
};

// 从后端获取图谱数据（优先 /api/graph，降级 /api/trend，再降级 mock）
const fetchGraphData = async () => {
  loading.value = true;
  try {
    // 优先调用专用图谱接口，返回更多节点
    const response = await jobApi.getSkillGraph({
      limit: graphLimit.value,
      min_demand: 1,
      edge_limit: Math.min(graphLimit.value * 3, 5000),
    });

    if (response.success && response.data?.nodes?.length) {
      const { nodes: rawNodes, edges: rawEdges } = response.data;

      // 按需求量决定节点视觉大小
      const maxDemand = Math.max(...rawNodes.map((n: any) => n.demand_count || 1), 1);

      const graphNodes = rawNodes.map((skill: any, index: number) => ({
        id: `skill_${index}`,
        name: skill.skill,
        category: mapCategory(skill.category || ''),
        categoryLabel: skill.category || '其他',
        jobCount: skill.demand_count || 0,
        avgSalary: skill.avg_salary || skill.avg_salary_k || 0,
        degree: Math.max((skill.demand_count / maxDemand) * 20, 4),
      }));

      const nameToId = new Map(graphNodes.map((n: any) => [n.name, n.id]));

      const graphEdges = rawEdges
        .map((e: any) => {
          const srcId = nameToId.get(e.skill1);
          const tgtId = nameToId.get(e.skill2);
          if (!srcId || !tgtId) return null;
          return {
            source: srcId,
            target: tgtId,
            weight: Math.max(e.co_count / 50000, 0.2),
            coCount: e.co_count,
          };
        })
        .filter(Boolean);

      allNodes.value = graphNodes;
      allEdges.value = graphEdges;
      applyFilter();
    } else {
      // 降级：使用 /api/trend 的热门技能
      const trendResp = await jobApi.getTrend();
      const trendData = trendResp.success ? trendResp.data : null;
      if (trendData?.hot_skills?.length) {
        const graphNodes = trendData.hot_skills.map((skill: any, index: number) => ({
          id: `skill_${index}`,
          name: skill.skill,
          category: mapCategory(skill.category || ''),
          categoryLabel: skill.category,
          jobCount: skill.demand_count,
          avgSalary: skill.avg_salary_k || 0,
          degree: Math.max(skill.hot_score / 10, 1),
        }));
        const nameToId = new Map(graphNodes.map((n: any) => [n.name, n.id]));
        const graphEdges = (trendData.skill_combos || []).map((combo: any) => {
          const srcId = nameToId.get(combo.skill1);
          const tgtId = nameToId.get(combo.skill2);
          if (!srcId || !tgtId) return null;
          return { source: srcId, target: tgtId, weight: Math.max(combo.co_count / 10000, 0.3), coCount: combo.co_count };
        }).filter(Boolean);
        allNodes.value = graphNodes;
        allEdges.value = graphEdges;
        applyFilter();
      } else {
        generateMockData();
      }
    }
  } catch (error) {
    console.error('获取图谱数据失败，使用模拟数据:', error);
    generateMockData();
  } finally {
    loading.value = false;
    await nextTick();
    safeDrawGraph();
  }
};

// 安全绘制：等容器有实际尺寸后再绘制
const safeDrawGraph = () => {
  const container = document.getElementById('knowledge-graph');
  if (!container) return;
  const w = container.clientWidth;
  const h = container.clientHeight;
  if (w > 0 && h > 0) {
    drawGraph();
  } else {
    // 容器尺寸还没计算完，等下一帧
    requestAnimationFrame(safeDrawGraph);
  }
};

// 模拟图谱数据
const generateMockData = () => {
  // 技能节点数据
  const mockNodes = [
    { id: '1', name: 'Python', category: 'language', jobCount: 45231, avgSalary: 18.5, degree: 12, categoryLabel: '编程语言' },
    { id: '2', name: 'JavaScript', category: 'language', jobCount: 38921, avgSalary: 16.8, degree: 10, categoryLabel: '编程语言' },
    { id: '3', name: 'Java', category: 'language', jobCount: 35678, avgSalary: 19.2, degree: 9, categoryLabel: '编程语言' },
    { id: '4', name: 'React', category: 'framework', jobCount: 28765, avgSalary: 17.5, degree: 8, categoryLabel: '框架/库' },
    { id: '5', name: 'Vue', category: 'framework', jobCount: 22345, avgSalary: 16.2, degree: 7, categoryLabel: '框架/库' },
    { id: '6', name: 'Django', category: 'framework', jobCount: 18902, avgSalary: 17.8, degree: 6, categoryLabel: '框架/库' },
    { id: '7', name: 'Docker', category: 'tool', jobCount: 31567, avgSalary: 18.9, degree: 8, categoryLabel: '工具' },
    { id: '8', name: 'Kubernetes', category: 'tool', jobCount: 15678, avgSalary: 22.3, degree: 5, categoryLabel: '工具' },
    { id: '9', name: 'MySQL', category: 'tool', jobCount: 35678, avgSalary: 16.5, degree: 7, categoryLabel: '工具' },
    { id: '10', name: 'Redis', category: 'tool', jobCount: 24567, avgSalary: 17.2, degree: 6, categoryLabel: '工具' },
    { id: '11', name: 'AI/ML', category: 'domain', jobCount: 19876, avgSalary: 25.6, degree: 9, categoryLabel: '领域' },
    { id: '12', name: 'Node.js', category: 'framework', jobCount: 21345, avgSalary: 17.0, degree: 6, categoryLabel: '框架/库' },
    { id: '13', name: 'Go', category: 'language', jobCount: 15678, avgSalary: 20.5, degree: 5, categoryLabel: '编程语言' },
    { id: '14', name: 'TypeScript', category: 'language', jobCount: 28765, avgSalary: 18.0, degree: 7, categoryLabel: '编程语言' },
    { id: '15', name: 'PostgreSQL', category: 'tool', jobCount: 16789, avgSalary: 17.8, degree: 5, categoryLabel: '工具' }
  ];

  // 关系边数据
  const mockEdges = [
    { source: '1', target: '6', weight: 0.8, coCount: 28000 },
    { source: '1', target: '10', weight: 0.7, coCount: 22000 },
    { source: '2', target: '4', weight: 0.9, coCount: 25000 },
    { source: '2', target: '5', weight: 0.8, coCount: 20000 },
    { source: '2', target: '12', weight: 0.85, coCount: 23000 },
    { source: '4', target: '14', weight: 0.75, coCount: 18000 },
    { source: '5', target: '14', weight: 0.7, coCount: 15000 },
    { source: '6', target: '9', weight: 0.8, coCount: 22000 },
    { source: '7', target: '8', weight: 0.6, coCount: 12000 },
    { source: '9', target: '10', weight: 0.7, coCount: 18000 },
    { source: '1', target: '11', weight: 0.6, coCount: 14000 },
    { source: '3', target: '13', weight: 0.5, coCount: 10000 },
    { source: '2', target: '14', weight: 0.9, coCount: 26000 },
    { source: '9', target: '15', weight: 0.6, coCount: 11000 }
  ];

  allNodes.value = mockNodes;
  allEdges.value = mockEdges;
  applyFilter();
};

// 初始化图谱
const initGraph = () => {
  fetchGraphData();
};

// 计算各布局的初始位置
const applyLayoutPositions = (nodeList: any[], width: number, height: number, layout: string) => {
  const n = nodeList.length;
  if (n === 0) return;

  if (layout === 'circle') {
    const r = Math.min(width, height) * 0.38;
    const cx = width / 2, cy = height / 2;
    nodeList.forEach((d, i) => {
      const angle = (2 * Math.PI * i) / n - Math.PI / 2;
      d.x = d.fx = cx + r * Math.cos(angle);
      d.y = d.fy = cy + r * Math.sin(angle);
    });
  } else if (layout === 'grid') {
    const cols = Math.ceil(Math.sqrt(n));
    const rows = Math.ceil(n / cols);
    const padX = width / (cols + 1);
    const padY = height / (rows + 1);
    nodeList.forEach((d, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      d.x = d.fx = padX * (col + 1);
      d.y = d.fy = padY * (row + 1);
    });
  } else {
    // force 模式：清除固定位置，让物理模拟自由运行
    nodeList.forEach(d => { d.fx = null; d.fy = null; });
  }
};

// 绘制图谱
const drawGraph = () => {
  const container = document.getElementById('knowledge-graph');
  if (!container) return;

  const width = container.clientWidth;
  const height = container.clientHeight;

  // 清空容器
  container.innerHTML = '';

  // 深拷贝节点和边，防止 D3 mutation 污染 nodes/edges ref
  const simNodes: any[] = nodes.value.map(n => ({ ...n }));
  const simEdges: any[] = edges.value.map(e => ({ ...e }));

  // 根据当前布局设置初始位置
  applyLayoutPositions(simNodes, width, height, layoutType.value);

  // 创建SVG（支持缩放/平移）
  const svg = d3.select(container)
    .append('svg')
    .attr('width', '100%')
    .attr('height', '100%')
    .attr('viewBox', `0 0 ${width} ${height}`)
    .style('background', 'transparent');

  const g = svg.append('g');

  svg.call(
    d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.2, 5])
      .on('zoom', (event) => g.attr('transform', event.transform))
  );

  // 创建力导向模拟（圆形/网格布局时降低力的强度，保持固定位置）
  const isFixed = layoutType.value !== 'force';
  const simulation = d3.forceSimulation(simNodes)
    .force('link', d3.forceLink(simEdges).id((d: any) => d.id).distance((d: any) => d.weight * 80))
    .force('charge', d3.forceManyBody().strength(isFixed ? -10 : -400))
    .force('center', isFixed ? null : d3.forceCenter(width / 2, height / 2))
    .force('collide', d3.forceCollide((d: any) =>
      (showWeights.value ? Math.max(d.degree * 2.8, 10) : 18) + 8
    ));

  if (isFixed) simulation.alphaDecay(0.3); // 快速收敛

  // 绘制边
  const linkGroup = g.append('g').attr('class', 'links');
  const links = linkGroup.selectAll('.link')
    .data(simEdges)
    .enter()
    .append('line')
    .attr('class', 'link')
    .attr('stroke', '#94a3b8')
    .attr('stroke-width', (d: any) => Math.max(d.weight, 0.5))
    .attr('opacity', showConnections.value ? 0.5 : 0);

  // 绘制节点
  const nodeGroup = g.append('g').attr('class', 'nodes');
  const nodesD3 = nodeGroup.selectAll('.node')
    .data(simNodes)
    .enter()
    .append('g')
    .attr('class', 'node')
    .call(d3.drag<SVGGElement, any>()
      .on('start', (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x; d.fy = d.y;
      })
      .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y; })
      .on('end', (event, d) => {
        if (!event.active) simulation.alphaTarget(0);
        // force 模式拖完松开；fixed 模式保持位置
        if (layoutType.value === 'force') { d.fx = null; d.fy = null; }
      })
    )
    .on('click', (_event, d) => selectNode(d));

  // 节点半径计算（受 showWeights 控制）
  const nodeR = (d: any) => showWeights.value
    ? Math.max(d.degree * 2.8, 10)   // 按需求量缩放，范围约 10~56px
    : 18;                              // 不显示权重时统一大小

  // 边粗细计算（受 showWeights 控制）
  const linkW = (d: any) => showWeights.value
    ? Math.max(d.weight * 5, 1)       // 按共现次数缩放
    : 1.5;                             // 不显示权重时统一粗细

  // 更新边粗细
  links.attr('stroke-width', linkW);

  // 节点圆形
  nodesD3.append('circle')
    .attr('r', nodeR)
    .attr('fill', (d: any) => {
      if (d.category === 'language') return '#3b82f6';
      if (d.category === 'framework') return '#8b5cf6';
      if (d.category === 'tool') return '#10b981';
      return '#f59e0b';
    })
    .attr('stroke', 'rgba(255,255,255,0.6)')
    .attr('stroke-width', 2)
    .style('filter', 'drop-shadow(0 2px 6px rgba(0,0,0,0.4))');

  // 需求量徽章（showWeights 时在重要节点上显示岗位数）
  if (showWeights.value) {
    nodesD3
      .filter((d: any) => d.jobCount > 0)
      .append('text')
      .attr('class', 'demand-badge')
      .attr('dy', (d: any) => nodeR(d) + 14)
      .attr('text-anchor', 'middle')
      .attr('fill', 'rgba(255,255,255,0.55)')
      .attr('font-size', '9px')
      .text((d: any) => d.jobCount > 0 ? `${d.jobCount}岗` : '')
      .attr('pointer-events', 'none');
  }

  // 节点标签
  nodesD3.append('text')
    .attr('dy', (d: any) => -nodeR(d) - 5)
    .attr('text-anchor', 'middle')
    .attr('fill', '#fff')
    .attr('font-size', (d: any) => showWeights.value ? `${Math.min(Math.max(d.degree * 0.6 + 9, 10), 15)}px` : '12px')
    .attr('font-weight', 'bold')
    .text((d: any) => d.name)
    .attr('pointer-events', 'none');

  // 每帧更新位置
  simulation.on('tick', () => {
    links
      .attr('x1', (d: any) => d.source.x)
      .attr('y1', (d: any) => d.source.y)
      .attr('x2', (d: any) => d.target.x)
      .attr('y2', (d: any) => d.target.y);
    nodesD3.attr('transform', (d: any) => `translate(${d.x},${d.y})`);
  });

  simulation.alpha(1).restart();
  (window as any).graphSimulation = simulation;

  // 若动画效果关闭，等一帧后停止模拟并固定节点
  if (!enableAnimation.value) {
    requestAnimationFrame(() => {
      simulation.stop();
      simNodes.forEach((d: any) => { d.fx = d.x; d.fy = d.y; });
    });
  }
};

// 切换布局时重新绘制
watch(layoutType, () => {
  safeDrawGraph();
});

// 搜索技能：高亮匹配节点，暗化其余节点
const handleSearch = () => {
  const keyword = searchSkill.value.trim().toLowerCase();
  const container = document.getElementById('knowledge-graph');
  if (!container) return;

  if (!keyword) {
    // 清空搜索，恢复所有节点
    d3.select(container).selectAll('.node circle').attr('opacity', 1);
    d3.select(container).selectAll('.node text').attr('opacity', 1);
    d3.select(container).selectAll('.link').attr('opacity', showConnections.value ? 0.5 : 0);
    return;
  }

  // 匹配的节点 id 集合
  const matchedIds = new Set(
    nodes.value
      .filter((n: any) => n.name.toLowerCase().includes(keyword))
      .map((n: any) => n.id)
  );

  if (matchedIds.size === 0) {
    ElMessage.warning(`未找到包含 "${searchSkill.value}" 的技能节点`);
    return;
  }

  // 与匹配节点直接相连的边/节点也半高亮
  const relatedIds = new Set<string>();
  edges.value.forEach((e: any) => {
    const srcId = typeof e.source === 'object' ? e.source.id : e.source;
    const tgtId = typeof e.target === 'object' ? e.target.id : e.target;
    if (matchedIds.has(srcId)) relatedIds.add(tgtId);
    if (matchedIds.has(tgtId)) relatedIds.add(srcId);
  });

  // 高亮节点
  d3.select(container).selectAll<SVGGElement, any>('.node')
    .each(function(d) {
      const isMatch = matchedIds.has(d.id);
      const isRelated = relatedIds.has(d.id);
      d3.select(this).select('circle')
        .attr('opacity', isMatch ? 1 : isRelated ? 0.6 : 0.15)
        .attr('stroke', isMatch ? '#fbbf24' : 'rgba(255,255,255,0.6)')
        .attr('stroke-width', isMatch ? 3 : 2);
      d3.select(this).select('text')
        .attr('opacity', isMatch ? 1 : isRelated ? 0.6 : 0.1);
    });

  // 高亮边
  d3.select(container).selectAll<SVGLineElement, any>('.link')
    .attr('opacity', (d: any) => {
      const srcId = typeof d.source === 'object' ? d.source.id : d.source;
      const tgtId = typeof d.target === 'object' ? d.target.id : d.target;
      return (matchedIds.has(srcId) || matchedIds.has(tgtId)) ? 0.8 : 0.05;
    });

  ElMessage.success(`找到 ${matchedIds.size} 个匹配节点`);
};

// 清空搜索时恢复正常显示
const handleSearchClear = () => {
  searchSkill.value = '';
  handleSearch();
};

// 选择节点
const selectNode = (node: any) => {
  selectedNode.value = node;
};

// 探索学习路径 → 跳转到匹配看板，带上目标技能
const exploreLearningPath = (node: any) => {
  if (!node?.name) return;
  router.push({ path: '/match', query: { targetSkill: node.name } });
};

// ---- AI 技能介绍 ----
const aiIntroLoading = ref(false);
const aiIntroResult = ref('');
const aiIntroSkill = ref('');

const renderIntro = (text: string) => _renderMd(text);

const fetchAIIntro = async (node: any) => {
  if (!node?.name) return;
  if (aiIntroSkill.value === node.name && aiIntroResult.value) {
    aiIntroResult.value = '';
    aiIntroSkill.value = '';
    return;
  }
  aiIntroLoading.value = true;
  aiIntroResult.value = '';
  aiIntroSkill.value = node.name;
  try {
    const prompt = buildSkillIntroPrompt({
      skillName: node.name,
      category: node.category || '技术技能',
      jobCount: node.jobCount,
      avgSalary: node.avgSalary,
      relatedSkills: (node.related || []).map((r: any) => r.name || r)
    });
    const res = await jobApi.chat({ message: prompt, session_id: `intro_${node.name}_${Date.now()}` });
    aiIntroResult.value = res.data?.response || res.data?.data?.response || '暂无回复';
  } catch {
    aiIntroResult.value = '⚠️ AI 服务暂时不可用，请稍后重试';
  } finally {
    aiIntroLoading.value = false;
  }
};

// 导出图谱（SVG 格式下载）
const exportGraph = () => {
  const svgElement = document.querySelector('#knowledge-graph svg');
  if (svgElement) {
    const serializer = new XMLSerializer();
    let source = serializer.serializeToString(svgElement);
    
    // 添加命名空间
    if (!source.match(/^<svg[^>]+xmlns="http\:\/\/www\.w3\.org\/2000\/svg"/)) {
      source = source.replace(/^<svg/, '<svg xmlns="http://www.w3.org/2000/svg"');
    }
    
    // 创建下载链接
    const blob = new Blob([source], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'skill-graph.svg';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
};

// 监听窗口大小变化
const handleResize = () => {
  safeDrawGraph();
};

// 将边还原为干净的字符串 ID（防止 D3 mutation 污染 allEdges）
const cleanEdgeId = (v: any): string =>
  typeof v === 'object' && v !== null ? String(v.id) : String(v);

// 根据技能类型筛选节点和边（每次产生全新对象，避免 D3 mutation 问题）
const applyFilter = () => {
  const allNodesClean = allNodes.value;
  if (skillFilter.value === 'all') {
    nodes.value = allNodesClean.map(n => ({ ...n }));
    edges.value = allEdges.value.map(e => ({
      ...e,
      source: cleanEdgeId(e.source),
      target: cleanEdgeId(e.target),
    }));
  } else {
    const filtered = allNodesClean.filter(n => n.category === skillFilter.value);
    const filteredIds = new Set(filtered.map(n => String(n.id)));
    nodes.value = filtered.map(n => ({ ...n }));
    edges.value = allEdges.value
      .filter(e => {
        const srcId = cleanEdgeId(e.source);
        const tgtId = cleanEdgeId(e.target);
        return filteredIds.has(srcId) && filteredIds.has(tgtId);
      })
      .map(e => ({
        ...e,
        source: cleanEdgeId(e.source),
        target: cleanEdgeId(e.target),
      }));
  }
};

// 技能类型筛选 watch → 重新过滤并重绘
watch(skillFilter, () => {
  applyFilter();
  safeDrawGraph();
});

// 显示关联 watch → 直接操作 SVG link 透明度
watch(showConnections, (val) => {
  const container = document.getElementById('knowledge-graph');
  if (!container) return;
  d3.select(container).selectAll('.link')
    .attr('opacity', val ? 0.5 : 0);
});

// 显示权重 watch → 切换节点大小、边粗细、需求量徽章
watch(showWeights, (val) => {
  const container = document.getElementById('knowledge-graph');
  if (!container) return;

  const nodeR = (d: any) => val ? Math.max(d.degree * 2.8, 10) : 18;
  const linkW = (d: any) => val ? Math.max(d.weight * 5, 1) : 1.5;
  const fontSize = (d: any) => val
    ? `${Math.min(Math.max(d.degree * 0.6 + 9, 10), 15)}px`
    : '12px';

  const svg = d3.select(container);

  // 平滑过渡更新节点大小
  svg.selectAll<SVGCircleElement, any>('.node circle')
    .transition().duration(450)
    .attr('r', nodeR);

  // 更新节点标签位置 + 字号
  svg.selectAll<SVGTextElement, any>('.node text:not(.demand-badge)')
    .transition().duration(450)
    .attr('dy', (d: any) => -nodeR(d) - 5)
    .attr('font-size', fontSize);

  // 更新边粗细
  svg.selectAll<SVGLineElement, any>('.link')
    .transition().duration(450)
    .attr('stroke-width', linkW);

  // 切换需求量徽章
  if (val) {
    // 添加需求量文字（跳过已存在的）
    svg.selectAll<SVGGElement, any>('.node')
      .filter((d: any) => d.jobCount > 0)
      .each(function(d: any) {
        const g = d3.select(this);
        if (g.select('.demand-badge').empty()) {
          g.append('text')
            .attr('class', 'demand-badge')
            .attr('dy', nodeR(d) + 14)
            .attr('text-anchor', 'middle')
            .attr('fill', 'rgba(255,255,255,0.55)')
            .attr('font-size', '9px')
            .attr('pointer-events', 'none')
            .text(`${d.jobCount}岗`);
        }
      });
  } else {
    svg.selectAll('.demand-badge').remove();
  }

  // 更新碰撞半径（重启模拟让位置重新调整）
  const sim = (window as any).graphSimulation;
  if (sim) {
    sim.force('collide', d3.forceCollide((d: any) => nodeR(d) + 8));
    sim.alpha(0.3).restart();
  }
});

// 动画效果 watch → 启停物理模拟
watch(enableAnimation, (val) => {
  const sim = (window as any).graphSimulation;
  if (!sim) return;
  if (val) {
    sim.alphaTarget(0.3).restart();
    setTimeout(() => sim.alphaTarget(0), 2000); // 动一段时间后自然停止
  } else {
    sim.stop();
    // 固定所有节点当前位置
    nodes.value.forEach((d: any) => { d.fx = d.x; d.fy = d.y; });
  }
});

onMounted(() => {
  initGraph();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
});
</script>

<style scoped lang="scss">
.graph-page {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
  height: calc(100vh - 130px);
  display: flex;
  flex-direction: column;

  .graph-header {
    margin-bottom: 20px;
    padding: 20px;

    .header-content {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .page-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 1.5rem;
        color: $text-primary;

        .el-icon {
          color: $primary-color;
        }
      }

      .header-controls {
        display: flex;
        align-items: center;
        gap: 12px;
      }
    }
  }

  .graph-main {
    display: grid;
    grid-template-columns: 250px 1fr 300px;
    gap: 20px;
    flex: 1;

    .control-panel {
      padding: 20px;
      height: fit-content;

      .panel-section {
        margin-bottom: 24px;

        h3 {
          margin: 0 0 12px;
          color: $text-primary;
          font-size: 1rem;
          border-bottom: 1px solid $border-color;
          padding-bottom: 6px;
        }

        .option-item {
          margin-bottom: 12px;
          display: flex;
          align-items: center;
          gap: 8px;

          .el-radio-group {
            margin-left: 8px;
          }
        }

        .stats-item {
          margin-bottom: 8px;
          display: flex;
          justify-content: space-between;

          .stat-value {
            color: $primary-color;
            font-weight: 500;
          }
        }
      }
    }

    .graph-container {
      padding: 0;
      overflow: hidden;
      min-height: 560px;

      .graph-canvas {
        width: 100%;
        height: 560px;
        min-height: 560px;
      }
    }

    .detail-panel {
      padding: 20px;
      height: fit-content;

      .detail-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        padding-bottom: 12px;
        border-bottom: 1px solid $border-color;

        h3 {
          margin: 0;
          color: $text-primary;
          font-size: 1.2rem;
        }
      }

      .detail-content {
        .detail-row {
          margin-bottom: 16px;
          display: flex;
          flex-wrap: wrap;
          align-items: flex-start;

          .label {
            font-weight: 500;
            color: $text-secondary;
            min-width: 80px;
            margin-right: 8px;
          }

          .value {
            color: $text-regular;
            flex: 1;

            .skill-tag {
              margin: 2px 4px 2px 0;
            }
          }
        }

        .detail-actions {
          margin-top: 16px;
          display: flex;
          flex-direction: column;
          gap: 8px;

          .ai-intro-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            width: 100%;
            padding: 8px 0;
            border-radius: 8px;
            border: 1px solid rgba(234,179,8,0.35);
            background: rgba(234,179,8,0.07);
            color: #fde047;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;

            &:hover:not(:disabled) {
              background: rgba(234,179,8,0.15);
              border-color: rgba(234,179,8,0.6);
              box-shadow: 0 0 10px rgba(234,179,8,0.18);
            }
            &:disabled { opacity: 0.55; cursor: default; }

            .spin-dot {
              width: 8px;
              height: 8px;
              border-radius: 50%;
              border: 2px solid #fde047;
              border-top-color: transparent;
              animation: spin 0.8s linear infinite;
            }
          }
        }

        // AI 技能介绍面板
        .ai-intro-panel {
          margin-top: 14px;
          border-radius: 10px;
          background: rgba(234,179,8,0.05);
          border: 1px solid rgba(234,179,8,0.18);
          overflow: hidden;

          .ai-intro-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 14px;
            background: rgba(234,179,8,0.08);
            border-bottom: 1px solid rgba(234,179,8,0.12);

            .ai-label {
              font-size: 11px;
              color: #fde047;
              font-weight: 700;
              letter-spacing: 0.3px;
            }
            .close-btn {
              background: none;
              border: none;
              color: rgba(255,255,255,0.4);
              cursor: pointer;
              font-size: 12px;
              padding: 1px 5px;
              border-radius: 3px;
              &:hover { color: #fff; background: rgba(255,255,255,0.08); }
            }
          }

          .ai-intro-skeleton {
            padding: 14px;
            display: flex;
            flex-direction: column;
            gap: 9px;

            .sk-line {
              height: 11px;
              border-radius: 5px;
              background: linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.09) 50%, rgba(255,255,255,0.04) 75%);
              background-size: 200% 100%;
              animation: shimmer 1.4s infinite;
              &.w85 { width: 85%; }
              &.w65 { width: 65%; }
              &.w90 { width: 90%; }
              &.w55 { width: 55%; }
            }
          }

          .ai-intro-content {
            padding: 14px;
            font-size: 12.5px;
            color: rgba(255,255,255,0.88);
            line-height: 1.75;

            :deep(.intro-h3) { font-size: 13px; font-weight: 700; color: #fde047; margin: 10px 0 4px; }
            :deep(.intro-h4) { font-size: 12.5px; font-weight: 600; color: #fcd34d; margin: 8px 0 3px; }
            :deep(strong) { color: #fde047; }
            :deep(code) {
              background: rgba(234,179,8,0.12);
              color: #fde047;
              padding: 1px 5px;
              border-radius: 3px;
              font-size: 11.5px;
            }
            :deep(li) {
              list-style: none;
              padding-left: 14px;
              position: relative;
              margin: 2px 0;
              &::before { content: '▸'; position: absolute; left: 0; color: #fbbf24; font-size: 10px; }
              &.ol::before { content: none; }
              .on {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 16px;
                height: 16px;
                border-radius: 50%;
                background: rgba(234,179,8,0.15);
                color: #fde047;
                font-size: 10px;
                font-weight: 700;
                margin-right: 5px;
              }
            }
          }
        }
      }
    }
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@media (max-width: 1200px) {
  .graph-main {
    grid-template-columns: 1fr !important;
  }
}
</style>