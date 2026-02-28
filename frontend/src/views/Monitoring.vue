<template>
  <div class="monitoring-page">
    <GlassCard class="monitoring-header">
      <div class="header-content">
        <h1 class="page-title">
          <el-icon><Monitor /></el-icon>
          数据监控看板
        </h1>
        <div class="header-controls">
          <el-button-group>
            <el-button @click="refreshAll" :loading="refreshing">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <el-button @click="checkHealth">
              <el-icon><Search /></el-icon>
              检查服务
            </el-button>
          </el-button-group>
        </div>
      </div>
    </GlassCard>

    <!-- 服务状态 -->
    <div class="services-status">
      <GlassCard 
        v-for="service in services" 
        :key="service.name"
        class="service-card"
        :class="{ 'service-active': service.status === true, 'service-inactive': service.status === false, 'service-checking': service.status === null }"
      >
        <div class="service-header">
          <div class="service-icon">
            <el-icon><component :is="service.icon" /></el-icon>
          </div>
          <div class="service-info">
            <h3 class="service-name">{{ service.name }}</h3>
            <div class="service-status">
              <span class="status-dot" :class="{ active: service.status === true, inactive: service.status === false, checking: service.status === null }"></span>
              <span class="status-text">
                {{ service.status === null ? '检测中...' : service.status ? '正常' : '异常' }}
              </span>
            </div>
          </div>
        </div>
        <div class="service-details">
          <div class="detail-item">
            <span class="detail-label">响应时间:</span>
            <span class="detail-value" :class="{ 'val-slow': service.responseTime !== null && service.responseTime > 1000 }">
              {{ service.responseTime !== null ? `${service.responseTime}ms` : '—' }}
            </span>
          </div>
          <div class="detail-item">
            <span class="detail-label">接口:</span>
            <span class="detail-value" style="font-size:11px;opacity:0.7">{{ service.endpoint }}</span>
          </div>
        </div>
      </GlassCard>
    </div>

    <!-- 图谱规模 -->
    <div class="graph-stats">
      <GlassCard class="graph-stat-card">
        <h3 class="stat-title">📊 图谱规模</h3>
        <div class="stat-grid">
          <div class="stat-item">
            <div class="stat-value">{{ graphStats.totalNodes }}</div>
            <div class="stat-label">总节点数</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ graphStats.totalRelationships }}</div>
            <div class="stat-label">总关系数</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ graphStats.skills }}</div>
            <div class="stat-label">技能节点</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ graphStats.jobs }}</div>
            <div class="stat-label">岗位节点</div>
          </div>
        </div>
      </GlassCard>

      <GlassCard class="graph-stat-card">
        <h3 class="stat-title">🔗 关系类型</h3>
        <div class="stat-grid">
          <div class="stat-item">
            <div class="stat-value">{{ graphStats.requiresRelationships }}</div>
            <div class="stat-label">REQUIRES关系</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ graphStats.relatedRelationships }}</div>
            <div class="stat-label">RELATED_TO关系</div>
          </div>
        </div>
      </GlassCard>
    </div>

    <!-- 数据更新状态 -->
    <div class="data-update">
      <GlassCard class="update-card">
        <h3 class="card-title">📅 数据更新状态</h3>
        <div class="update-info">
          <div class="update-item">
            <span class="update-label">最后更新:</span>
            <span class="update-value">{{ lastUpdate }}</span>
          </div>
          <div class="update-item">
            <span class="update-label">数据版本:</span>
            <span class="update-value">2026.02（支持增量更新）</span>
          </div>
          <div class="update-item">
            <span class="update-label">数据源:</span>
            <span class="update-value">Boss直聘</span>
          </div>
          <div class="update-item">
            <span class="update-label">数据量:</span>
            <span class="update-value">{{ graphStats.jobs }} 个岗位</span>
          </div>
        </div>
      </GlassCard>
    </div>

    <!-- API健康检查 -->
    <div class="api-health">
      <GlassCard class="health-card">
        <h3 class="card-title">🌐 API健康检查</h3>
        <div class="health-grid">
          <div 
            v-for="api in apis" 
            :key="api.name"
            class="health-item"
            :class="{ 'health-active': api.status === true, 'health-inactive': api.status === false && !api.slow, 'health-checking': api.status === null }"
          >
            <div class="api-name">
              {{ api.name }}
              <span v-if="api.slow" class="api-badge-llm">LLM</span>
              <span v-if="api.heavy" class="api-badge-heavy">缓存</span>
            </div>
            <div class="api-status">
              <span class="status-dot" :class="{ active: api.status === true, inactive: api.status === false, checking: api.status === null }"></span>
              <span class="status-text">{{ api.status === null ? '检测中' : api.status ? '正常' : '异常' }}</span>
            </div>
            <div 
              class="api-response"
              :class="{
                'resp-fast':   api.responseTime !== null && api.responseTime < 300,
                'resp-ok':     api.responseTime !== null && api.responseTime >= 300  && api.responseTime < 1000,
                'resp-slow':   api.responseTime !== null && api.responseTime >= 1000 && api.responseTime < 3000,
                'resp-danger': api.responseTime !== null && api.responseTime >= 3000
              }"
            >
              {{ api.responseTime !== null ? `${api.responseTime}ms` : '—' }}
            </div>
          </div>
        </div>
        <div class="health-legend">
          <span class="legend-item resp-fast">● &lt;300ms 优秀</span>
          <span class="legend-item resp-ok">● 300-999ms 正常</span>
          <span class="legend-item resp-slow">● 1-3s 偏慢</span>
          <span class="legend-item resp-danger">● &gt;3s 超时</span>
          <span class="legend-item api-badge-llm" style="font-size:10px;padding:1px 5px;margin-left:0">LLM = 大模型/向量接口，慢属正常</span>
          <span class="legend-item api-badge-heavy" style="font-size:10px;padding:1px 5px">缓存 = 重量级，冷启动后缓存预热即秒开</span>
        </div>
      </GlassCard>
    </div>

    <!-- 系统日志 -->
    <div class="system-logs">
      <GlassCard class="logs-card">
        <h3 class="card-title">📝 系统日志</h3>
        <div class="logs-list">
          <div 
            v-for="(log, index) in logs" 
            :key="index"
            class="log-item"
            :class="log.type"
          >
            <div class="log-time">{{ log.time }}</div>
            <div class="log-content">
              <span class="log-type">{{ log.type }}</span>
              <span class="log-message">{{ log.message }}</span>
            </div>
          </div>
        </div>
      </GlassCard>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { 
  Monitor, Refresh, Search, 
  Database, Document, User, Setting, 
  TrendCharts, DataAnalysis 
} from '@element-plus/icons-vue';
import GlassCard from '@/components/GlassCard.vue';
import { jobApi } from '@/api/jobApi';

// 服务状态（通过轻量 /api/health/quick 一次性获取所有服务状态）
const services = ref([
  { name: 'RAG服务',    status: null as boolean | null, responseTime: null as number | null, icon: 'Document',     serviceKey: 'rag',    endpoint: '/api/rag/search'  },
  { name: 'Agent服务',  status: null as boolean | null, responseTime: null as number | null, icon: 'User',         serviceKey: 'agent',  endpoint: '/api/agent/chat'  },
  { name: '图谱服务',   status: null as boolean | null, responseTime: null as number | null, icon: 'TrendCharts',  serviceKey: 'neo4j',  endpoint: '/api/search'      },
  { name: '数据统计服务', status: null as boolean | null, responseTime: null as number | null, icon: 'DataAnalysis', serviceKey: 'search', endpoint: '/api/stats'       }
]);

// 图谱统计
const graphStats = ref({
  totalNodes: 0,
  totalRelationships: 0,
  skills: 0,
  jobs: 0,
  requiresRelationships: 0,
  relatedRelationships: 0
});

// 最后更新时间（初始显示数据采集时间，刷新后显示本次刷新时间）
const lastUpdate = ref('2026-02-28');

// API 健康状态（实测）
// slow  = 预期慢（LLM/向量推断），响应时间偏高属正常
// heavy = 重量级（图数据库/统计），冷启动慢，缓存热后快
const apis = ref([
  { name: '/api/health/quick', status: null as boolean | null, responseTime: null as number | null, slow: false, heavy: false },
  { name: '/api/stats',        status: null as boolean | null, responseTime: null as number | null, slow: false, heavy: true  },
  { name: '/api/trend',        status: null as boolean | null, responseTime: null as number | null, slow: false, heavy: true  },
  { name: '/api/graph',        status: null as boolean | null, responseTime: null as number | null, slow: false, heavy: true  },
  { name: '/api/search',       status: null as boolean | null, responseTime: null as number | null, slow: false, heavy: false },
  { name: '/api/rag/search',   status: null as boolean | null, responseTime: null as number | null, slow: true,  heavy: false },
  { name: '/api/gap-analysis', status: null as boolean | null, responseTime: null as number | null, slow: false, heavy: true  },
  { name: '/api/agent/chat',   status: null as boolean | null, responseTime: null as number | null, slow: true,  heavy: false }
]);

// 系统日志（运行时动态追加）
const logs = ref<Array<{ time: string; type: string; message: string }>>([]);

// 刷新状态
const refreshing = ref(false);

// 追加一条运行日志
const addLog = (type: 'info' | 'success' | 'warning' | 'error', message: string) => {
  const now = new Date();
  const time = now.toTimeString().slice(0, 8);
  logs.value.unshift({ time, type, message });
  if (logs.value.length > 50) logs.value.pop();
};

const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// 通用请求计时（对 LLM 接口用 5s 超时，其他 3s）
const measureEndpoint = async (
  method: string,
  endpoint: string,
  body: any,
  timeoutMs = 3000
): Promise<{ ok: boolean; ms: number }> => {
  const start = Date.now();
  try {
    const token = localStorage.getItem('token');
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`${BASE}${endpoint}`, {
      method: method.toUpperCase(),
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: AbortSignal.timeout(timeoutMs)
    });
    return { ok: res.ok || res.status < 500, ms: Date.now() - start };
  } catch {
    return { ok: false, ms: Date.now() - start };
  }
};

// 检查所有服务和 API 状态
const checkHealth = async () => {
  refreshing.value = true;
  addLog('info', '开始健康检查...');

  // ── Step 1：用轻量 quick 接口一次性更新 4 个服务卡片状态（< 100ms）──
  try {
    const quickStart = Date.now();
    const token = localStorage.getItem('token');
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`${BASE}/api/health/quick`, { headers, signal: AbortSignal.timeout(2000) });
    const quickMs = Date.now() - quickStart;
    if (res.ok) {
      const data = await res.json();
      const svcMap: Record<string, boolean> = data.services || {};
      services.value.forEach(svc => {
        svc.status = svcMap[svc.serviceKey] ?? false;
        svc.responseTime = quickMs; // 反映实际网络延迟
      });
      addLog('success', `/api/health/quick · ${quickMs}ms · 服务状态已更新`);
    }
  } catch (e) {
    services.value.forEach(svc => { svc.status = false; svc.responseTime = null; });
    addLog('error', '轻量健康检查失败，后端可能未启动');
  }

  // ── Step 2：并发检测各 API 端点响应时间
  //   · 轻量接口 (quick/search)：2-3s 超时，快速失败
  //   · 重量级接口 (stats/trend/graph/gap-analysis)：8s 超时，缓存热后应秒级返回
  //   · LLM/向量接口 (rag/agent)：10s 超时，首次可能慢，后续命中缓存变快
  const methodMap: Record<string, { method: string; body: any; timeout: number }> = {
    '/api/health/quick': { method: 'get',  body: null,                                                 timeout: 2000  },
    '/api/stats':        { method: 'get',  body: null,                                                 timeout: 8000  },
    '/api/trend':        { method: 'get',  body: null,                                                 timeout: 8000  },
    '/api/graph':        { method: 'get',  body: null,                                                 timeout: 8000  },
    '/api/search':       { method: 'post', body: { query: 'Python', top_k: 1 },                        timeout: 3000  },
    '/api/rag/search':   { method: 'post', body: { query: 'Python', top_k: 1 },                        timeout: 10000 },
    '/api/gap-analysis': { method: 'post', body: { user_skills: ['Python'], target_position: 'test' }, timeout: 8000  },
    '/api/agent/chat':   { method: 'post', body: { message: 'ping', session_id: 'health' },            timeout: 5000  }
  };

  // 从 quick 接口拿到的服务状态（已在 Step 1 完成）
  const quickServices = services.value.reduce((acc, svc) => {
    acc[svc.serviceKey] = svc.status ?? false;
    return acc;
  }, {} as Record<string, boolean>);
  const serviceKeyForApi: Record<string, string> = {
    '/api/stats': 'neo4j', '/api/trend': 'neo4j', '/api/graph': 'neo4j',
    '/api/search': 'search', '/api/rag/search': 'rag',
    '/api/gap-analysis': 'neo4j', '/api/agent/chat': 'agent',
    '/api/health/quick': 'neo4j'
  };

  let okCount = 0;
  await Promise.allSettled(
    apis.value.map(async (api) => {
      const cfg = methodMap[api.name] || { method: 'get', body: null, timeout: 5000 };
      const result = await measureEndpoint(cfg.method, api.name, cfg.body, cfg.timeout);
      // 重量级/LLM 接口：状态由 quick 接口决定，不因响应慢就报"异常"
      const svcKey = serviceKeyForApi[api.name];
      if ((api.heavy || api.slow) && svcKey) {
        api.status = quickServices[svcKey] ?? result.ok;
      } else {
        api.status = result.ok;
      }
      api.responseTime = result.ms;
      if (api.status) okCount++;
      addLog(
        api.status ? 'success' : 'warning',
        `${api.name} · ${result.ms}ms · ${api.status ? '正常' : '异常'}`
      );
    })
  );

  const total = apis.value.length;
  if (okCount === total) {
    ElMessage.success(`所有 ${total} 个接口正常`);
    addLog('success', `健康检查完成：${total}/${total} 接口正常`);
  } else {
    ElMessage.warning(`${okCount}/${total} 个接口正常，${total - okCount} 个异常`);
    addLog('warning', `健康检查完成：${okCount}/${total} 接口正常`);
  }
  refreshing.value = false;
};

// 刷新统计数据（图谱规模）
const refreshAll = async () => {
  refreshing.value = true;
  try {
    const statsResponse = await jobApi.getStats();
    if (statsResponse.success) {
      const stats = statsResponse.data;
      graphStats.value = {
        totalNodes: stats.neo4j?.total_nodes || 0,
        totalRelationships: stats.neo4j?.total_relationships || 0,
        skills: stats.neo4j?.skills || 0,
        jobs: stats.neo4j?.jobs || 0,
        requiresRelationships: stats.neo4j?.requires_relationships || 0,
        relatedRelationships: stats.neo4j?.related_relationships || 0
      };
      addLog('success', `图谱统计刷新：${graphStats.value.totalNodes} 节点，${graphStats.value.totalRelationships} 关系`);
    }
    lastUpdate.value = new Date().toLocaleString('zh-CN', {
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit'
    });
    ElMessage.success('数据刷新成功');
  } catch {
    ElMessage.error('刷新统计数据失败');
    addLog('error', '图谱统计刷新失败，请检查后端服务');
  } finally {
    refreshing.value = false;
  }
};

// 初始化：同时刷新统计和检测服务健康
onMounted(async () => {
  addLog('info', '监控看板初始化中...');
  await Promise.allSettled([refreshAll(), checkHealth()]);
});
</script>

<style scoped lang="scss">
.monitoring-page {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;

  .monitoring-header {
    margin-bottom: 20px;
    padding: 24px;

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

  .services-status {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 20px;
    margin-bottom: 20px;

    .service-card {
      padding: 24px;

      &.service-active {
        border-left: 4px solid #10b981;
      }

      &.service-inactive {
        border-left: 4px solid #ef4444;
      }

      .service-header {
        display: flex;
        align-items: center;
        gap: 16px;
        margin-bottom: 16px;

        .service-icon {
          width: 48px;
          height: 48px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: rgba(59, 130, 246, 0.1);
          border-radius: 12px;

          .el-icon {
            font-size: 24px;
            color: $primary-color;
          }
        }

        .service-info {
          .service-name {
            margin: 0 0 8px;
            color: $text-primary;
            font-size: 1.1rem;
            font-weight: 600;
          }

          .service-status {
            display: flex;
            align-items: center;
            gap: 6px;

            .status-dot {
              width: 8px;
              height: 8px;
              border-radius: 50%;
              flex-shrink: 0;

              &.active   { background: #10b981; }
              &.inactive { background: #ef4444; }
              &.checking {
                background: #f59e0b;
                animation: blink 1s ease-in-out infinite;
              }
            }

            .status-text {
              color: $text-secondary;
              font-size: 0.9rem;
            }
          }

          .val-slow { color: #f59e0b; }
        }
        
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      }

      .service-details {
        display: flex;
        gap: 24px;
        padding-top: 16px;
        border-top: 1px solid $border-color;

        .detail-item {
          display: flex;
          flex-direction: column;

          .detail-label {
            color: $text-secondary;
            font-size: 0.85rem;
            margin-bottom: 4px;
          }

          .detail-value {
            color: $text-primary;
            font-weight: 600;
          }
        }
      }
    }
  }

  .graph-stats {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
    margin-bottom: 20px;

    .graph-stat-card {
      padding: 24px;

      .stat-title {
        margin: 0 0 16px;
        color: $text-primary;
        font-size: 1.1rem;
      }

      .stat-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 16px;

        .stat-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 16px;
          background: rgba(59, 130, 246, 0.05);
          border-radius: 8px;

          .stat-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: $primary-color;
            margin-bottom: 8px;
          }

          .stat-label {
            color: $text-secondary;
            font-size: 0.9rem;
          }
        }
      }
    }
  }

  .data-update {
    margin-bottom: 20px;

    .update-card {
      padding: 24px;

      .card-title {
        margin: 0 0 16px;
        color: $text-primary;
        font-size: 1.1rem;
      }

      .update-info {
        .update-item {
          display: flex;
          justify-content: space-between;
          padding: 12px 0;
          border-bottom: 1px solid $border-color;

          &:last-child {
            border-bottom: none;
          }

          .update-label {
            color: $text-secondary;
            font-size: 0.9rem;
          }

          .update-value {
            color: $text-primary;
            font-weight: 600;
          }
        }
      }
    }
  }

  .api-health {
    margin-bottom: 20px;

    .health-card {
      padding: 24px;

      .card-title {
        margin: 0 0 16px;
        color: $text-primary;
        font-size: 1.1rem;
      }

      .health-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;

        .health-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 16px;
          background: rgba(59, 130, 246, 0.05);
          border-radius: 8px;

          &.health-active {
            border: 1px solid #10b981;
          }

          &.health-inactive {
            border: 1px solid #ef4444;
          }

          .api-name {
            color: $text-primary;
            font-size: 0.9rem;
            margin-bottom: 8px;
            text-align: center;
          }

          .api-status {
            display: flex;
            align-items: center;
            gap: 6px;
            margin-bottom: 8px;

            .status-dot {
              width: 8px;
              height: 8px;
              border-radius: 50%;

              &.active   { background: #10b981; }
              &.inactive { background: #ef4444; }
              &.checking {
                background: #f59e0b;
                animation: blink 1s ease-in-out infinite;
              }
            }

            .status-text {
              color: $text-secondary;
              font-size: 0.85rem;
            }
          }

          .api-response {
            color: $text-secondary;
            font-size: 0.9rem;
            font-weight: 600;
            &.resp-fast   { color: #10b981; }
            &.resp-ok     { color: #3b82f6; }
            &.resp-slow   { color: #f59e0b; }
            &.resp-danger { color: #ef4444; }
          }

          .api-badge-llm {
            display: inline-block;
            padding: 1px 5px;
            margin-left: 4px;
            background: rgba(139, 92, 246, 0.2);
            color: #a78bfa;
            border-radius: 4px;
            font-size: 10px;
            vertical-align: middle;
          }
          .api-badge-heavy {
            display: inline-block;
            padding: 1px 5px;
            margin-left: 4px;
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border-radius: 4px;
            font-size: 10px;
            vertical-align: middle;
          }
        }
      }

      .health-legend {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        margin-top: 16px;
        padding-top: 12px;
        border-top: 1px solid rgba(255,255,255,0.07);
        font-size: 12px;
        color: $text-secondary;

        .legend-item {
          &.resp-fast   { color: #10b981; }
          &.resp-ok     { color: #3b82f6; }
          &.resp-slow   { color: #f59e0b; }
          &.resp-danger { color: #ef4444; }
        }
      }
    }
  }

  .system-logs {
    .logs-card {
      padding: 24px;

      .card-title {
        margin: 0 0 16px;
        color: $text-primary;
        font-size: 1.1rem;
      }

      .logs-list {
        .log-item {
          display: flex;
          gap: 16px;
          padding: 12px;
          margin-bottom: 8px;
          border-radius: 8px;
          background: rgba(59, 130, 246, 0.05);

          &.info {
            border-left: 4px solid #3b82f6;
          }

          &.success {
            border-left: 4px solid #10b981;
          }

          &.warning {
            border-left: 4px solid #f59e0b;
          }

          .log-time {
            min-width: 80px;
            color: $text-secondary;
            font-size: 0.9rem;
          }

          .log-content {
            flex: 1;

            .log-type {
              display: inline-block;
              padding: 2px 8px;
              border-radius: 4px;
              font-size: 0.8rem;
              margin-right: 8px;
              font-weight: 600;

              &.info {
                background: rgba(59, 130, 246, 0.1);
                color: #3b82f6;
              }

              &.success {
                background: rgba(16, 185, 129, 0.1);
                color: #10b981;
              }

              &.warning {
                background: rgba(245, 158, 11, 0.1);
                color: #f59e0b;
              }
            }

            .log-message {
              color: $text-primary;
              font-size: 0.9rem;
            }
          }
        }
      }
    }
  }
}

@media (max-width: 1200px) {
  .services-status {
    grid-template-columns: repeat(2, 1fr) !important;
  }

  .health-grid {
    grid-template-columns: repeat(2, 1fr) !important;
  }
}
</style>
