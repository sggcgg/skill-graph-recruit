<template>
  <div class="test-api-page">
    <GlassCard class="test-container">
      <h2>API 测试页面</h2>
      
      <div class="test-section">
        <h3>健康检查</h3>
        <el-button @click="testHealth">测试健康检查</el-button>
        <div v-if="healthResult" class="result">
          <pre>{{ JSON.stringify(healthResult, null, 2) }}</pre>
        </div>
      </div>
      
      <div class="test-section">
        <h3>系统统计</h3>
        <el-button @click="testStats">获取系统统计</el-button>
        <div v-if="statsResult" class="result">
          <pre>{{ JSON.stringify(statsResult, null, 2) }}</pre>
        </div>
      </div>
      
      <div class="test-section">
        <h3>RAG 搜索测试</h3>
        <el-input v-model="searchQuery" placeholder="输入搜索内容" />
        <el-button @click="testRagSearch" style="margin-top: 10px;">执行搜索</el-button>
        <div v-if="searchResult" class="result">
          <pre>{{ JSON.stringify(searchResult, null, 2) }}</pre>
        </div>
      </div>
    </GlassCard>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import GlassCard from '@/components/GlassCard.vue';
import { jobApi } from '@/api/jobApi';

const healthResult = ref<any>(null);
const statsResult = ref<any>(null);
const searchResult = ref<any>(null);
const searchQuery = ref('Python后端开发');

const testHealth = async () => {
  try {
    const result = await jobApi.healthCheck();
    healthResult.value = result;
  } catch (error) {
    console.error('健康检查失败:', error);
    healthResult.value = { error: '请求失败', details: error };
  }
};

const testStats = async () => {
  try {
    const result = await jobApi.getStats();
    statsResult.value = result;
  } catch (error) {
    console.error('获取统计失败:', error);
    statsResult.value = { error: '请求失败', details: error };
  }
};

const testRagSearch = async () => {
  try {
    const result = await jobApi.searchJobs({
      query: searchQuery.value,
      top_k: 5
    });
    searchResult.value = result;
  } catch (error) {
    console.error('搜索失败:', error);
    searchResult.value = { error: '请求失败', details: error };
  }
};
</script>

<style scoped lang="scss">
.test-api-page {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;

  .test-container {
    padding: 30px;

    .test-section {
      margin-bottom: 30px;
      padding-bottom: 20px;
      border-bottom: 1px solid $border-color;

      &:last-child {
        border-bottom: none;
        margin-bottom: 0;
        padding-bottom: 0;
      }

      h3 {
        margin-bottom: 15px;
        color: $text-primary;
      }

      .result {
        margin-top: 15px;
        padding: 15px;
        background: $bg-secondary;
        border-radius: 8px;
        max-height: 300px;
        overflow: auto;

        pre {
          margin: 0;
          color: $text-regular;
          font-size: 0.9rem;
          line-height: 1.5;
        }
      }
    }
  }
}
</style>