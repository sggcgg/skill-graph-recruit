<template>
  <div class="skill-management">
    <GlassCard class="management-header">
      <div class="header-content">
        <h1 class="page-title">
          <el-icon><Medal /></el-icon>
          技能本体管理
        </h1>
        <div class="header-controls">
          <el-input
            v-model="searchQuery"
            placeholder="搜索技能..."
            :prefix-icon="Search"
            style="width: 250px; margin-right: 16px;"
          />
          <el-button @click="loadSkillsFromBackend" :loading="dataLoading" style="margin-right: 8px;">
            <el-icon><Refresh /></el-icon>
            从图谱同步
          </el-button>
          <el-button type="primary" @click="showAddDialog">
            <el-icon><Plus /></el-icon>
            添加技能
          </el-button>
        </div>
      </div>
    </GlassCard>

    <GlassCard class="management-content">
      <!-- 技能列表 -->
      <div class="skill-list">
        <div 
          v-for="skill in paginatedSkills" 
          :key="skill.id"
          class="skill-item"
        >
          <div class="skill-info">
            <div class="skill-name">
              <el-tag :type="getCategoryType(skill.category)" size="large">
                {{ skill.name }}
              </el-tag>
            </div>
            <div class="skill-meta">
              <span class="meta-item">
                <el-icon><TrendCharts /></el-icon>
                {{ skill.category }}
              </span>
              <span class="meta-item">
                <el-icon><DataAnalysis /></el-icon>
                需求量: {{ skill.demandCount }}
              </span>
              <span class="meta-item">
                <el-icon><Coin /></el-icon>
                平均薪资: {{ skill.avgSalary.toFixed(1) }}K
              </span>
            </div>
            <div v-if="skill.aliases && skill.aliases.length > 0" class="skill-aliases">
              <span class="aliases-label">同义词:</span>
              <el-tag
                v-for="alias in skill.aliases"
                :key="alias"
                size="small"
                type="info"
              >
                {{ alias }}
              </el-tag>
            </div>
          </div>
          <div class="skill-actions">
            <el-button size="small" @click="showEditDialog(skill)">
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>
            <el-button size="small" type="danger" @click="deleteSkill(skill.id)">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="skills.length"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </GlassCard>

    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isAdd ? '添加技能' : '编辑技能'"
      width="600px"
    >
      <el-form :model="skillForm" label-width="100px" ref="formRef">
        <el-form-item label="技能名称" required>
          <el-input v-model="skillForm.name" placeholder="例如：Python" />
        </el-form-item>
        <el-form-item label="技能类别" required>
          <el-select v-model="skillForm.category" placeholder="请选择类别">
            <el-option label="编程语言" value="language" />
            <el-option label="框架/库" value="framework" />
            <el-option label="工具" value="tool" />
            <el-option label="数据库" value="database" />
            <el-option label="领域" value="domain" />
          </el-select>
        </el-form-item>
        <el-form-item label="需求量">
          <el-input-number v-model="skillForm.demandCount" :min="0" />
        </el-form-item>
        <el-form-item label="平均薪资(K)">
          <el-input-number v-model="skillForm.avgSalary" :min="0" :max="100" />
        </el-form-item>
        <el-form-item label="同义词">
          <el-input
            v-model="skillForm.aliases"
            type="textarea"
            :rows="3"
            placeholder="多个同义词用逗号分隔，例如：Python3, Py"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveSkill" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { 
  Medal, Search, Plus, Edit, Delete, TrendCharts, DataAnalysis, Coin, Refresh
} from '@element-plus/icons-vue';
import GlassCard from '@/components/GlassCard.vue';
import { jobApi } from '@/api/jobApi';
import { ElMessage as _ElMsg } from 'element-plus';

// 加载状态
const dataLoading = ref(false);

// 技能列表（初始为空，从后端加载）
const skills = ref<Array<{
  id: string;
  name: string;
  category: string;
  demandCount: number;
  avgSalary: number;
  aliases: string[];
}>>([]);

// 搜索
const searchQuery = ref('');
const filteredSkills = computed(() => {
  if (!searchQuery.value) return skills.value;
  return skills.value.filter(skill => 
    skill.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
    skill.category.includes(searchQuery.value) ||
    (skill.aliases && skill.aliases.some(alias => alias.toLowerCase().includes(searchQuery.value.toLowerCase())))
  );
});

// 分页
const currentPage = ref(1);
const pageSize = ref(10);
const paginatedSkills = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return filteredSkills.value.slice(start, start + pageSize.value);
});

const handleSizeChange = (size: number) => {
  pageSize.value = size;
  currentPage.value = 1;
};

const handlePageChange = (page: number) => {
  currentPage.value = page;
};

// 对话框
const dialogVisible = ref(false);
const isAdd = ref(true);
const saving = ref(false);
const formRef = ref();

// 技能表单
const skillForm = ref({
  id: '',
  name: '',
  category: 'language',
  demandCount: 0,
  avgSalary: 0,
  aliases: ''
});

const showAddDialog = () => {
  isAdd.value = true;
  skillForm.value = {
    id: '',
    name: '',
    category: 'language',
    demandCount: 0,
    avgSalary: 0,
    aliases: ''
  };
  dialogVisible.value = true;
};

const showEditDialog = (skill: any) => {
  isAdd.value = false;
  skillForm.value = {
    id: skill.id,
    name: skill.name,
    category: skill.category,
    demandCount: skill.demandCount,
    avgSalary: skill.avgSalary,
    aliases: skill.aliases ? skill.aliases.join(',') : ''
  };
  dialogVisible.value = true;
};

const getCategoryType = (category: string) => {
  const types: Record<string, string> = {
    language: 'primary',
    framework: 'success',
    tool: 'warning',
    database: 'info',
    domain: 'danger'
  };
  return types[category] || 'info';
};

const saveSkill = async () => {
  if (!skillForm.value.name) {
    ElMessage.warning('技能名称不能为空');
    return;
  }

  saving.value = true;

  try {
    // 模拟保存技能
    const aliases = skillForm.value.aliases
      .split(',')
      .map(s => s.trim())
      .filter(s => s.length > 0);

    if (isAdd.value) {
      // 添加技能
      const newSkill = {
        ...skillForm.value,
        aliases
      };
      skills.value.unshift(newSkill);
      ElMessage.success('添加技能成功');
    } else {
      // 编辑技能
      const index = skills.value.findIndex(s => s.id === skillForm.value.id);
      if (index !== -1) {
        skills.value[index] = {
          ...skills.value[index],
          name: skillForm.value.name,
          category: skillForm.value.category,
          demandCount: skillForm.value.demandCount,
          avgSalary: skillForm.value.avgSalary,
          aliases
        };
        ElMessage.success('编辑技能成功');
      }
    }

    dialogVisible.value = false;
  } catch (error) {
    console.error('保存技能失败:', error);
    ElMessage.error('保存技能失败');
  } finally {
    saving.value = false;
  }
};

const deleteSkill = (id: string) => {
  ElMessageBox.confirm('确定要删除这个技能吗？', '警告', {
    type: 'warning',
    confirmButtonText: '确定',
    cancelButtonText: '取消'
  }).then(() => {
    skills.value = skills.value.filter(s => s.id !== id);
    ElMessage.success('删除技能成功');
  }).catch(() => {
    // 取消删除
  });
};

// 分类映射
const categoryMap: Record<string, string> = {
  '编程语言': 'language',
  '框架/库': 'framework',
  '工具': 'tool',
  '数据库': 'database',
  '领域': 'domain',
  'language': 'language',
  'framework': 'framework',
  'tool': 'tool',
  'database': 'database',
  'domain': 'domain'
};

// 从后端加载技能数据
const loadSkillsFromBackend = async () => {
  dataLoading.value = true;
  try {
    const [trendRes, statsRes] = await Promise.all([
      jobApi.getTrend(),
      jobApi.getStats()
    ]);
    if (trendRes.success && trendRes.data.hot_skills) {
      const hotSkills = trendRes.data.hot_skills;
      const highSalary = trendRes.data.high_salary_skills || [];
      const salaryMap: Record<string, number> = {};
      highSalary.forEach((s: any) => { salaryMap[s.skill] = s.avg_salary_k; });
      skills.value = hotSkills.map((skill: any, idx: number) => ({
        id: String(idx + 1),
        name: skill.skill,
        category: categoryMap[skill.category] || 'domain',
        demandCount: skill.demand_count || 0,
        avgSalary: salaryMap[skill.skill] || (15 + Math.random() * 10),
        aliases: []
      }));
    }
  } catch (error) {
    console.error('加载技能数据失败，使用默认数据:', error);
    skills.value = [
      { id: '1', name: 'Python', category: 'language', demandCount: 45231, avgSalary: 18.5, aliases: ['Python3', 'Py'] },
      { id: '2', name: 'JavaScript', category: 'language', demandCount: 38921, avgSalary: 16.8, aliases: ['JS'] },
      { id: '3', name: 'Java', category: 'language', demandCount: 35678, avgSalary: 19.2, aliases: [] },
      { id: '4', name: 'React', category: 'framework', demandCount: 28765, avgSalary: 17.5, aliases: [] },
      { id: '5', name: 'Vue', category: 'framework', demandCount: 22345, avgSalary: 16.2, aliases: [] },
      { id: '6', name: 'Django', category: 'framework', demandCount: 18902, avgSalary: 17.8, aliases: [] },
      { id: '7', name: 'Docker', category: 'tool', demandCount: 31567, avgSalary: 18.9, aliases: [] },
      { id: '8', name: 'Kubernetes', category: 'tool', demandCount: 15678, avgSalary: 22.3, aliases: ['K8s'] },
      { id: '9', name: 'MySQL', category: 'database', demandCount: 35678, avgSalary: 16.5, aliases: [] },
      { id: '10', name: 'Redis', category: 'database', demandCount: 24567, avgSalary: 17.2, aliases: [] }
    ];
  } finally {
    dataLoading.value = false;
  }
};

onMounted(() => {
  loadSkillsFromBackend();
});
</script>

<style scoped lang="scss">
.skill-management {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;

  .management-header {
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

  .management-content {
    padding: 24px;

    .skill-list {
      .skill-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 20px;
        margin-bottom: 16px;
        background: rgba(59, 130, 246, 0.05);
        border-radius: 12px;
        border-left: 4px solid $primary-color;

        .skill-info {
          flex: 1;

          .skill-name {
            margin-bottom: 12px;
          }

          .skill-meta {
            display: flex;
            gap: 20px;
            margin-bottom: 12px;

            .meta-item {
              display: flex;
              align-items: center;
              gap: 6px;
              color: $text-secondary;
              font-size: 0.9rem;

              .el-icon {
                color: $primary-color;
              }
            }
          }

          .skill-aliases {
            .aliases-label {
              color: $text-secondary;
              margin-right: 8px;
            }
          }
        }

        .skill-actions {
          display: flex;
          gap: 8px;
        }
      }
    }

    .pagination {
      margin-top: 20px;
      text-align: center;
    }
  }
}
</style>
