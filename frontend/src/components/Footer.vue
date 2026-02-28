<template>
  <footer class="footer">
    <div class="footer-container">
      <div class="footer-stats">
        <h3>系统统计</h3>
        <div class="stats-grid">
          <div class="stat-item">
            <div class="stat-number">20万+</div>
            <div class="stat-label">岗位数</div>
          </div>
          <div class="stat-item">
            <div class="stat-number">352</div>
            <div class="stat-label">技能数</div>
          </div>
          <div class="stat-item">
            <div class="stat-number">&lt;200ms</div>
            <div class="stat-label">响应时间</div>
          </div>
        </div>
      </div>
      
      <div class="footer-tech-stack">
        <h3>技术栈</h3>
        <div class="tech-grid">
          <div class="tech-item">
            <strong>Agent:</strong> Qwen3.5-Plus API · LangGraph ReAct
          </div>
          <div class="tech-item">
            <strong>RAG:</strong> ChromaDB向量库 · m3e-base语义嵌入
          </div>
          <div class="tech-item">
            <strong>技能抽取:</strong> 本地Qwen2.5-1.5B · vLLM加速
          </div>
          <div class="tech-item">
            <strong>知识图谱:</strong> Neo4j · Vue3前端
          </div>
        </div>
      </div>
      
      <div class="footer-links">
        <div class="copyright">© 2026 智能招聘系统</div>
        <div class="github-link">
          <el-link href="https://github.com/your-repo" target="_blank" type="primary">
            GitHub 仓库
          </el-link>
        </div>
      </div>
    </div>
  </footer>
</template>

<script setup lang="ts">
// Footer 组件逻辑
</script>

<style scoped lang="scss">
.footer {
  background: $bg-secondary;
  border-top: 1px solid $border-color;
  padding: 40px 20px 20px;
  margin-top: 60px;

  .footer-container {
    max-width: 1400px;
    margin: 0 auto;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 40px;

    .footer-stats {
      h3 {
        margin-bottom: 20px;
        color: $text-primary;
        font-size: 18px;
      }

      .stats-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 20px;

        .stat-item {
          text-align: center;

          .stat-number {
            font-size: 24px;
            font-weight: bold;
            color: $primary-color;
            margin-bottom: 4px;
          }

          .stat-label {
            font-size: 14px;
            color: $text-regular;
          }
        }
      }
    }

    .footer-tech-stack {
      h3 {
        margin-bottom: 20px;
        color: $text-primary;
        font-size: 18px;
      }

      .tech-grid {
        display: flex;
        flex-direction: column;
        gap: 10px;

        .tech-item {
          padding: 10px;
          background: rgba(255, 255, 255, 0.05);
          border-radius: 6px;
          font-size: 14px;
          color: $text-regular;

          strong {
            color: $text-primary;
          }
        }
      }
    }

    .footer-links {
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      gap: 15px;

      .copyright {
        color: $text-regular;
        font-size: 14px;
      }

      .github-link {
        :deep(.el-link) {
          font-size: 16px;
        }
      }
    }
  }
}
</style>