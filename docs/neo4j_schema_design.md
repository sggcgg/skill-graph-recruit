# Neo4j 技能图谱 Schema 设计（优化版）

## 📋 设计目标
1. 满足毕业设计"技能图谱"核心要求
2. 支持复杂的图查询和推荐算法
3. 可扩展性强，便于后续增强
4. 适合写入简历，展示技术深度

## 🎯 节点类型设计

### 1. Skill（技能节点）- 核心节点
**用途**：技能知识本体的核心载体

**属性设计**：
```cypher
(skill:Skill {
    skill_id: String,           // 唯一ID，如 "skill_001"
    name: String,               // 技能标准名称，如 "Python"
    category: String,           // 一级分类，如 "编程语言"
    sub_category: String,       // 二级分类，如 "后端语言"（可选）
    level: String,              // 级别: 核心/常用/进阶/专业/基础
    hot_score: Integer,         // 市场热度 0-100
    aliases: List<String>,      // 别名列表，用于匹配
    description: String,        // 技能描述
    demand_count: Integer,      // 需求该技能的岗位数
    avg_salary_min: Float,      // 涉及该技能的平均最低薪资
    avg_salary_max: Float,      // 涉及该技能的平均最高薪资
    created_at: DateTime,       // 创建时间
    updated_at: DateTime        // 更新时间
})
```

**索引**：
- 主键索引：`skill_id`
- 唯一索引：`name`
- 全文索引：`name`, `aliases`（用于模糊搜索）

---

### 2. Job（职位节点）
**用途**：招聘岗位信息

**属性设计**：
```cypher
(job:Job {
    job_id: String,             // 唯一ID
    title: String,              // 职位名称
    city: String,               // 城市
    district: String,           // 区县
    business_district: String,  // 商圈
    salary_min: Integer,        // 最低薪资（K）
    salary_max: Integer,        // 最高薪资（K）
    salary_text: String,        // 薪资文本
    experience: String,         // 经验要求
    education: String,          // 学历要求
    publish_date: Date,         // 发布日期
    source: String,             // 数据来源
    welfare: List<String>,      // 福利标签
    jd_text: String,            // 职位描述全文（用于NLP）
    skill_count: Integer,       // 要求技能数量
    created_at: DateTime
})
```

**索引**：
- 主键索引：`job_id`
- 复合索引：`(city, salary_min, education)` - 用于筛选查询

---

### 3. Company（公司节点）
**用途**：公司信息及招聘偏好分析

**属性设计**：
```cypher
(company:Company {
    company_id: String,         // 唯一ID
    name: String,               // 公司名称（标准化后）
    industry: String,           // 行业
    size: String,               // 规模
    stage: String,              // 融资阶段
    city: String,               // 所在城市
    job_count: Integer,         // 发布岗位数
    avg_salary_min: Float,      // 平均薪资
    avg_salary_max: Float,
    top_skills: List<String>,   // 最常要求的技能TOP10
    created_at: DateTime
})
```

**索引**：
- 主键索引：`company_id`
- 唯一索引：`name`

---

### 4. SkillCategory（技能分类节点）
**用途**：技能分类体系，便于层级查询

**属性设计**：
```cypher
(category:SkillCategory {
    category_id: String,        // 分类ID
    name: String,               // 分类名称，如 "编程语言"
    level: Integer,             // 层级：1-一级分类，2-二级分类
    skill_count: Integer,       // 该分类下技能数量
    description: String
})
```

---

### 5. SkillCluster（技能簇节点）【高级特性】
**用途**：通过图算法（如Louvain社区发现）自动发现的技能组合

**属性设计**：
```cypher
(cluster:SkillCluster {
    cluster_id: String,         // 簇ID
    name: String,               // 簇名称，如 "Python全栈开发"
    core_skills: List<String>,  // 核心技能
    cluster_score: Float,       // 聚合度分数
    scenario: String,           // 应用场景
    job_count: Integer          // 相关岗位数
})
```

---

## 🔗 关系类型设计

### 1. REQUIRES（岗位要求技能）
**连接**：`(Job)-[:REQUIRES]->(Skill)`

**属性**：
```cypher
{
    importance: String,         // 重要程度: "must"|"prefer"|"optional"
    source: String,             // 来源: "explicit"（明确标注）| "extracted"（从JD提取）
    confidence: Float,          // 置信度 0-1（NLP提取的技能需要）
    extracted_at: DateTime
}
```

**场景**：
- 查询某岗位需要哪些技能
- 统计某技能被多少岗位需要
- 技能市场需求分析

---

### 2. RELATED_TO（技能关联）
**连接**：`(Skill)-[:RELATED_TO]->(Skill)`

**属性**：
```cypher
{
    co_occurrence: Integer,     // 共现次数
    correlation: Float,         // 相关性分数（基于共现频率计算）
    relation_type: String,      // 关系类型: "prerequisite"(前置)|"alternative"(替代)|"complementary"(互补)
    strength: Float,            // 关系强度 0-1
    created_at: DateTime
}
```

**计算方法**：
```python
correlation = co_occurrence / sqrt(count_A * count_B)  # Jaccard或PMI
```

**场景**：
- 技能推荐："掌握Python的人还应该学习..."
- 学习路径生成
- 技能差距分析

---

### 3. BELONGS_TO（技能属于分类）
**连接**：`(Skill)-[:BELONGS_TO]->(SkillCategory)`

**属性**：
```cypher
{
    assigned_at: DateTime
}
```

---

### 4. POSTED_BY（岗位发布于公司）
**连接**：`(Job)-[:POSTED_BY]->(Company)`

**属性**：
```cypher
{
    post_date: Date
}
```

---

### 5. LOCATED_IN（位于城市）
**连接**：`(Job)-[:LOCATED_IN]->(City)`

**属性**：
```cypher
{
    district: String,
    business_district: String
}
```

（可选，如果需要城市节点的话）

---

### 6. IN_CLUSTER（技能属于技能簇）【高级】
**连接**：`(Skill)-[:IN_CLUSTER]->(SkillCluster)`

**属性**：
```cypher
{
    membership_score: Float     // 隶属度分数
}
```

---

### 7. PREQUISITE_OF（技能前置关系）【高级】
**连接**：`(Skill)-[:PREREQUISITE_OF]->(Skill)`

**属性**：
```cypher
{
    strength: Float,            // 前置必要性 0-1
    learning_order: Integer     // 学习顺序
}
```

**场景**：学习路径规划

---

## 📐 图谱Schema可视化

```
┌─────────────────────────────────────────────────────────────┐
│                      技能知识图谱                             │
└─────────────────────────────────────────────────────────────┘
                          │
           ┌──────────────┼──────────────┐
           │              │              │
    ┌──────▼─────┐ ┌──────▼─────┐ ┌─────▼──────┐
    │   Skill    │ │    Job     │ │  Company   │
    │  (核心节点) │ │  (岗位节点) │ │  (公司节点) │
    └──────┬─────┘ └──────┬─────┘ └─────┬──────┘
           │              │              │
           │         REQUIRES        POSTED_BY
           │              │              │
           │              ▼              │
           │    ┌─────────────────┐     │
           │    │   Skill_A       │◄────┘
           │    │   Skill_B       │
           │    │   Skill_C       │
           │    └─────────────────┘
           │
      RELATED_TO (相互关联)
           │
           ▼
    ┌─────────────┐
    │ SkillCluster│
    │  (技能簇)    │
    └─────────────┘
```

---

## 🚀 Cypher创建语句

```cypher
// 1. 创建约束和索引
CREATE CONSTRAINT skill_id IF NOT EXISTS FOR (s:Skill) REQUIRE s.skill_id IS UNIQUE;
CREATE CONSTRAINT skill_name IF NOT EXISTS FOR (s:Skill) REQUIRE s.name IS UNIQUE;
CREATE CONSTRAINT job_id IF NOT EXISTS FOR (j:Job) REQUIRE j.job_id IS UNIQUE;
CREATE CONSTRAINT company_id IF NOT EXISTS FOR (c:Company) REQUIRE c.company_id IS UNIQUE;

CREATE INDEX skill_name_idx IF NOT EXISTS FOR (s:Skill) ON (s.name);
CREATE INDEX skill_category_idx IF NOT EXISTS FOR (s:Skill) ON (s.category);
CREATE INDEX job_city_idx IF NOT EXISTS FOR (j:Job) ON (j.city);
CREATE INDEX job_salary_idx IF NOT EXISTS FOR (j:Job) ON (j.salary_min, j.salary_max);

// 2. 创建全文索引（用于技能名称和别名的模糊搜索）
CREATE FULLTEXT INDEX skill_fulltext IF NOT EXISTS 
FOR (s:Skill) ON EACH [s.name, s.aliases];

// 3. 示例：创建技能节点
CREATE (s:Skill {
    skill_id: 'skill_python',
    name: 'Python',
    category: '编程语言',
    level: '核心',
    hot_score: 95,
    aliases: ['python', 'py', 'Python3'],
    description: '通用编程语言，数据科学首选',
    demand_count: 0,
    avg_salary_min: 0.0,
    avg_salary_max: 0.0,
    created_at: datetime(),
    updated_at: datetime()
});

// 4. 创建关系
MATCH (j:Job {job_id: 'xxx'}), (s:Skill {name: 'Python'})
CREATE (j)-[:REQUIRES {
    importance: 'must',
    source: 'explicit',
    confidence: 1.0,
    extracted_at: datetime()
}]->(s);

// 5. 计算技能共现关系
MATCH (s1:Skill)<-[:REQUIRES]-(j:Job)-[:REQUIRES]->(s2:Skill)
WHERE s1.skill_id < s2.skill_id  // 避免重复
WITH s1, s2, COUNT(j) as co_occurrence
WHERE co_occurrence >= 10  // 至少共现10次
MERGE (s1)-[r:RELATED_TO]-(s2)
SET r.co_occurrence = co_occurrence,
    r.correlation = co_occurrence * 1.0 / sqrt(s1.demand_count * s2.demand_count),
    r.strength = co_occurrence * 1.0 / 1000.0;  // 归一化
```

---

## 📊 与任务书要求的对应

| 任务书要求 | Schema设计 | 实现方式 |
|-----------|-----------|---------|
| 技能实体识别 | Skill节点 | 基于skill_taxonomy.json + NLP提取 |
| 技能关系抽取 | RELATED_TO关系 | 基于共现频率计算 |
| 岗位-技能关联 | REQUIRES关系 | 明确标注 + JD文本提取 |
| 图谱查询 | Cypher查询 | 支持路径查询、聚合查询 |
| 智能推荐 | 关系强度 + 图算法 | 协同过滤、图嵌入 |

---

## 🎯 简历亮点体现

1. **多层次节点设计**：不仅有Skill和Job，还有SkillCluster（技能簇）、SkillCategory（层级分类）
2. **丰富的关系类型**：REQUIRES、RELATED_TO、PREREQUISITE_OF，支持复杂查询
3. **属性工程**：hot_score、correlation、confidence等量化字段，体现工程思维
4. **图算法应用**：可以基于此Schema实现PageRank、社区发现、路径查找等算法
5. **可扩展性**：预留了SkillCluster、PREREQUISITE_OF等高级特性

---

## 🔧 后续优化方向

1. **引入User节点**：支持个性化推荐
2. **时间维度**：分析技能热度趋势（时序图）
3. **图嵌入**：使用Node2Vec生成技能向量，支持语义搜索
4. **知识融合**：整合外部知识源（如技术栈官网、学习平台）
