<template>
  <div class="api-test">
    <GlassCard class="test-card">
      <h2>API 连接测试</h2>
      
      <div class="test-section">
        <h3>后端服务状态</h3>
        <div class="status-indicators">
          <div class="status-item">
            <span class="status-dot" :class="{ active: healthStatus.services.rag }"></span>
            <span>RAG服务: {{ healthStatus.services.rag ? '正常' : '异常' }}</span>
          </div>
          <div class="status-item">
            <span class="status-dot" :class="{ active: healthStatus.services.agent }"></span>
            <span>Agent服务: {{ healthStatus.services.agent ? '正常' : '异常' }}</span>
          </div>
          <div class="status-item">
            <span class="status-dot" :class="{ active: healthStatus.services.skill_extractor }"></span>
            <span>技能抽取服务: {{ healthStatus.services.skill_extractor ? '正常' : '异常' }}</span>
          </div>
        </div>
        <el-button type="primary" @click="checkHealth">刷新状态</el-button>
      </div>

      <div class="test-section">
        <h3>用户认证测试</h3>
        <div class="input-group">
          <el-input v-model="loginCredentials.username" placeholder="用户名" />
          <el-input v-model="loginCredentials.password" type="password" placeholder="密码" />
          <el-button type="primary" @click="testLogin">测试登录</el-button>
        </div>
      </div>

      <div class="test-section">
        <h3>用户数据测试</h3>
        <el-button type="success" @click="testGetProfile">获取用户资料</el-button>
        <el-button type="success" @click="testGetResume">获取用户简历</el-button>
        <el-button type="success" @click="testGetFavorites">获取收藏岗位</el-button>
      </div>

      <div class="test-section">
        <h3>AI功能测试</h3>
        <div class="input-group">
          <el-input v-model="chatMessage" placeholder="输入聊天消息" />
          <el-button type="warning" @click="testChat">测试AI对话</el-button>
        </div>
      </div>

      <div class="test-section">
        <h3>测试结果</h3>
        <div class="result-log">
          <pre>{{ testLog }}</pre>
        </div>
      </div>
    </GlassCard>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue';
import GlassCard from '@/components/GlassCard.vue';
import { userApi } from '@/api/userApi';
import { jobApi } from '@/api/jobApi';

// 健康状态
const healthStatus = reactive({
  status: 'unknown',
  services: {
    rag: false,
    agent: false,
    skill_extractor: false
  }
});

// 登录凭据
const loginCredentials = reactive({
  username: 'testuser',
  password: 'testpass'
});

// 聊天消息
const chatMessage = ref('你好');

// 测试日志
const testLog = ref('');

// 添加到日志
const addToLog = (message: string) => {
  testLog.value = `[${new Date().toLocaleTimeString()}] ${message}\n${testLog.value}`;
};

// 检查健康状态
const checkHealth = async () => {
  try {
    const response = await jobApi.healthCheck();
    if (response.success) {
      Object.assign(healthStatus, response.data);
      addToLog('✅ 健康检查成功: ' + JSON.stringify(response.data));
    } else {
      addToLog('❌ 健康检查失败: ' + response.message);
    }
  } catch (error) {
    console.error('健康检查失败:', error);
    addToLog('❌ 健康检查失败: ' + (error as Error).message);
  }
};

// 测试登录
const testLogin = async () => {
  try {
    addToLog('🔄 尝试登录...');
    const response = await userApi.login(loginCredentials);
    if (response.access_token) {
      localStorage.setItem('token', response.access_token);
      localStorage.setItem('userInfo', JSON.stringify(response.user));
      addToLog('✅ 登录成功: ' + JSON.stringify(response.user));
    } else {
      addToLog('❌ 登录失败: ' + response.message);
    }
  } catch (error) {
    console.error('登录失败:', error);
    addToLog('❌ 登录失败: ' + (error as Error).message);
  }
};

// 测试获取用户资料
const testGetProfile = async () => {
  try {
    addToLog('🔄 获取用户资料...');
    const response = await userApi.getProfile();
    if (response.success) {
      addToLog('✅ 获取用户资料成功: ' + JSON.stringify(response.data));
    } else {
      addToLog('❌ 获取用户资料失败: ' + response.message);
    }
  } catch (error) {
    console.error('获取用户资料失败:', error);
    addToLog('❌ 获取用户资料失败: ' + (error as Error).message);
  }
};

// 测试获取用户简历
const testGetResume = async () => {
  try {
    addToLog('🔄 获取用户简历...');
    const response = await userApi.getResume();
    if (response.success) {
      addToLog('✅ 获取用户简历成功: ' + JSON.stringify(response.data));
    } else {
      addToLog('❌ 获取用户简历失败: ' + response.message);
    }
  } catch (error) {
    console.error('获取用户简历失败:', error);
    addToLog('❌ 获取用户简历失败: ' + (error as Error).message);
  }
};

// 测试获取收藏岗位
const testGetFavorites = async () => {
  try {
    addToLog('🔄 获取收藏岗位...');
    const response = await userApi.getFavorites();
    if (response.success) {
      addToLog('✅ 获取收藏岗位成功: ' + JSON.stringify(response.data));
    } else {
      addToLog('❌ 获取收藏岗位失败: ' + response.message);
    }
  } catch (error) {
    console.error('获取收藏岗位失败:', error);
    addToLog('❌ 获取收藏岗位失败: ' + (error as Error).message);
  }
};

// 测试AI对话
const testChat = async () => {
  try {
    addToLog('🔄 测试AI对话...');
    const response = await jobApi.chat({
      message: chatMessage.value,
      session_id: 'test-session'
    });
    if (response.success) {
      addToLog('✅ AI对话成功: ' + response.data.response);
    } else {
      addToLog('❌ AI对话失败: ' + response.message);
    }
  } catch (error) {
    console.error('AI对话失败:', error);
    addToLog('❌ AI对话失败: ' + (error as Error).message);
  }
};

// 初始化时检查健康状态
checkHealth();
</script>

<style scoped lang="scss">
.api-test {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.test-card {
  padding: 24px;

  .test-section {
    margin-bottom: 30px;
    padding-bottom: 20px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);

    &:last-child {
      border-bottom: none;
    }

    h3 {
      color: $text-primary;
      margin-bottom: 16px;
    }
  }

  .status-indicators {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 16px;
  }

  .status-item {
    display: flex;
    align-items: center;
    gap: 8px;
    color: $text-regular;
  }

  .status-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: $text-placeholder;

    &.active {
      background: $success-color;
      box-shadow: 0 0 8px $success-color;
    }
  }

  .input-group {
    display: flex;
    gap: 12px;
    margin-bottom: 16px;
    flex-wrap: wrap;

    :deep(.el-input) {
      max-width: 200px;
    }
  }

  .result-log {
    background: rgba(0, 0, 0, 0.2);
    border-radius: 8px;
    padding: 16px;
    max-height: 300px;
    overflow-y: auto;

    pre {
      margin: 0;
      color: $text-secondary;
      font-size: 0.9em;
      line-height: 1.4;
      white-space: pre-wrap;
      word-break: break-all;
    }
  }
}
</style>