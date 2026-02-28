# 智能招聘分析系统 API 使用文档

**Base URL**: `http://localhost:8000`  
**在线文档（可直接测试）**: `http://localhost:8000/docs`

---

## 目录

1. [快速开始](#快速开始)
2. [接口总览](#接口总览)
3. [认证系统](#认证系统)
4. [图谱增强核心接口（新）](#图谱增强核心接口新)
5. [RAG向量搜索接口（原有）](#rag向量搜索接口原有)
6. [用户管理接口](#用户管理接口)
7. [完整使用流程](#完整使用流程)
8. [请求示例汇总](#请求示例汇总)

---

## 快速开始

### 启动服务

```bash
source ~/.venv-skill-graph/bin/activate
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### 验证服务正常

```bash
curl http://localhost:8000/api/health
```

返回：
```json
{
  "status": "healthy",
  "services": { "rag": true, "agent": true, "skill_extractor": true }
}
```

---

## 接口总览

### 图谱增强接口（新增，基于 Neo4j）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/search` | 语义搜索（技能词典映射 + 图遍历） |
| POST | `/api/recommend` | 智能推荐（Cypher 精准匹配 + 语义扩展） |
| POST | `/api/gap-analysis` | 技能差距分析（图谱前置技能路径） |
| GET  | `/api/trend` | 市场趋势（热门技能、高薪技能、技能组合） |

### RAG 向量接口（原有，基于 ChromaDB）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/rag/search` | 向量语义搜索 + LLM 总结 |
| POST | `/api/skill/gap-analysis` | 技能差距分析（向量版） |
| POST | `/api/job/recommend` | 岗位推荐（向量版） |
| POST | `/api/skill/extract` | 技能抽取（规则 + LLM） |
| POST | `/api/agent/chat` | AI Agent 对话 |
| GET  | `/api/stats` | 系统数据统计 |

### 认证与用户接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 注册 |
| POST | `/api/auth/login` | 登录（获取 Token） |
| GET/PUT | `/api/user/profile` | 个人资料 |
| GET/PUT | `/api/user/resume` | 简历管理 |
| GET/POST/PUT/DELETE | `/api/user/skills` | 技能档案 |
| GET/POST/DELETE | `/api/user/favorites` | 收藏职位 |
| GET/POST/PUT | `/api/user/reports` | 匹配报告 |
| GET/PUT | `/api/user/settings` | 用户设置 |

---

## 认证系统

### 注册

**POST** `/api/auth/register`

```json
{
  "username": "张三",
  "email": "zhangsan@example.com",
  "password": "mypassword123"
}
```

### 登录

**POST** `/api/auth/login`

```json
{
  "username": "张三",
  "password": "mypassword123"
}
```

返回 `access_token`，后续需要登录的接口在请求头中携带：

```
Authorization: Bearer <access_token>
```

---

## 图谱增强核心接口（新）

这些接口直接查询 Neo4j 图数据库（18 万岗位、352 个技能节点、技能关系网络），具备更精准的结构化匹配能力。当 Neo4j 不可用时会自动降级为向量搜索。

---

### POST /api/search — 语义化搜索

**功能**：接收自然语言查询，自动提取其中的技能关键词，通过图谱遍历找到匹配岗位，同时辅以向量搜索补充结果。

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | string | ✅ | 查询词（自然语言） |
| top_k | integer | ❌ | 返回数量，默认 10，最大 50 |
| city | string | ❌ | 城市过滤，如 "北京" |

**请求示例**：
```json
{
  "query": "Python 后端开发，熟悉 Django 和 Redis",
  "top_k": 10,
  "city": "上海"
}
```

**返回示例**：
```json
{
  "success": true,
  "data": {
    "jobs": [
      {
        "job_id": "xxx",
        "title": "Python后端工程师",
        "city": "上海",
        "company": "某公司",
        "salary_range": "15-25K",
        "matched_skills": ["Python", "Django", "Redis"],
        "match_count": 3,
        "source": "graph"
      }
    ],
    "count": 10,
    "query": "Python 后端开发，熟悉 Django 和 Redis",
    "matched_skills": ["Python", "Django", "Redis"],
    "graph_hits": 8,
    "vector_hits": 5
  }
}
```

**与 `/api/rag/search` 的区别**：

| | `/api/search`（新） | `/api/rag/search`（原有） |
|---|---|---|
| 搜索引擎 | Neo4j 图谱 + 向量双路 | ChromaDB 向量 |
| 技能匹配 | 精确映射到标准技能名 | 语义相似度 |
| 结果字段 | 包含 `matched_skills`、`match_count` | 包含 `similarity` 分数 |
| LLM 总结 | 无 | 有（如 LLM 可用） |

---

### POST /api/recommend — 智能岗位推荐

**功能**：基于用户技能列表，通过 Cypher 查询找到技能匹配度最高的岗位（精准匹配），再利用 `RELATED_TO` 图关系扩展相似技能，推荐更多可能感兴趣的岗位（语义扩展）。

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_skills | array | ✅ | 你掌握的技能列表 |
| top_k | integer | ❌ | 推荐数量，默认 10 |
| city | string | ❌ | 城市过滤 |

**请求示例**：
```json
{
  "user_skills": ["Python", "Django", "MySQL", "Redis", "Docker"],
  "top_k": 10,
  "city": "深圳"
}
```

**返回示例**：
```json
{
  "success": true,
  "data": {
    "jobs": [
      {
        "job_id": "xxx",
        "title": "高级后端开发工程师",
        "salary_range": "20-35K",
        "matched_skills": ["Python", "Django", "MySQL"],
        "match_count": 3,
        "match_type": "precise"
      },
      {
        "job_id": "yyy",
        "title": "DevOps工程师",
        "salary_range": "18-28K",
        "matched_skills": ["Kubernetes", "Helm"],
        "match_count": 2,
        "match_type": "expanded"
      }
    ],
    "count": 10,
    "precise_count": 7,
    "expanded_count": 3,
    "related_skills": ["Kubernetes", "FastAPI", "PostgreSQL", "Helm"]
  }
}
```

**字段说明**：
- `match_type: "precise"` — 直接匹配用户技能的岗位
- `match_type: "expanded"` — 通过关联技能图谱扩展匹配的岗位
- `related_skills` — 与用户技能关联的扩展技能列表

---

### POST /api/gap-analysis — 技能差距分析

**功能**：输入用户现有技能和目标岗位，通过图谱查询该岗位高频所需技能，计算缺失技能，并利用 `RELATED_TO` 关系为每个缺失技能生成学习路径。

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_skills | array | ✅ | 你目前掌握的技能 |
| target_position | string | ✅ | 目标岗位名称 |
| city | string | ❌ | 目标城市 |

**请求示例**：
```json
{
  "user_skills": ["Python", "MySQL", "HTML", "CSS"],
  "target_position": "全栈开发工程师",
  "city": "北京"
}
```

**返回示例**：
```json
{
  "success": true,
  "data": {
    "target_position": "全栈开发工程师",
    "user_skills": ["Python", "MySQL", "HTML", "CSS"],
    "required_skills": ["Python", "React", "Node.js", "MySQL", "Redis", "Docker"],
    "matched_skills": ["Python", "MySQL"],
    "missing_skills": ["React", "Node.js", "Redis", "Docker"],
    "match_rate": 0.333,
    "learning_path": [
      {
        "skill": "Node.js",
        "owned_prerequisites": ["Python"],
        "needed_prerequisites": [],
        "ready_to_learn": true
      },
      {
        "skill": "React",
        "owned_prerequisites": ["HTML", "CSS"],
        "needed_prerequisites": ["JavaScript"],
        "ready_to_learn": false
      }
    ],
    "sample_jobs": [
      {"title": "全栈开发工程师", "city": "北京", "salary_range": "18-30K"}
    ]
  }
}
```

**字段说明**：
- `match_rate` — 技能匹配率（0~1）
- `learning_path` — 每个缺失技能的学习建议
  - `ready_to_learn: true` — 你已有前置技能，可以直接开始学
  - `ready_to_learn: false` — 还需先学 `needed_prerequisites` 中的技能

---

### GET /api/trend — 市场趋势分析

**功能**：从 Neo4j 图谱查询职位市场趋势数据，包含热门技能排行、技能分类分布、高频技能组合（共现对）、高薪技能榜。

**无需请求体**，直接 GET 请求即可。

**返回示例**：
```json
{
  "success": true,
  "data": {
    "hot_skills": [
      {"skill": "Java", "category": "编程语言", "demand_count": 45230, "hot_score": 97},
      {"skill": "Python", "category": "编程语言", "demand_count": 38920, "hot_score": 95}
    ],
    "category_distribution": [
      {"category": "编程语言", "skill_count": 15, "total_demand": 180000},
      {"category": "框架/库", "skill_count": 48, "total_demand": 130000}
    ],
    "skill_combos": [
      {"skill1": "Java", "skill2": "Spring Boot", "co_count": 28000},
      {"skill1": "Python", "skill2": "MySQL", "co_count": 22000}
    ],
    "high_salary_skills": [
      {"skill": "Kubernetes", "avg_salary_k": 28.5, "job_count": 3200},
      {"skill": "Golang", "avg_salary_k": 26.8, "job_count": 8900}
    ]
  }
}
```

**字段说明**：
- `hot_skills` — 岗位需求量最高的技能 TOP 20
- `category_distribution` — 各技能大类的总需求量分布
- `skill_combos` — 最常同时出现在同一岗位中的技能对（组合强度）
- `high_salary_skills` — 关联岗位平均薪资最高的技能 TOP 10

---

## RAG 向量搜索接口（原有）

这些接口基于 ChromaDB 向量数据库（18 万条岗位向量），适合语义模糊搜索和 LLM 增强分析。

### POST /api/rag/search — 向量语义搜索

**请求示例**：
```json
{
  "query": "机器学习工程师，熟悉深度学习框架",
  "top_k": 5,
  "city": "北京"
}
```

### POST /api/skill/gap-analysis — 技能差距（向量版）

```json
{
  "user_skills": ["Python", "TensorFlow"],
  "target_position": "算法工程师",
  "city": "上海"
}
```

### POST /api/job/recommend — 岗位推荐（向量版）

```json
{
  "user_skills": ["Java", "Spring Boot", "MySQL"],
  "top_k": 10
}
```

### POST /api/skill/extract — 技能抽取

从职位标题和 JD 文本中自动提取技能标签：

```json
{
  "title": "高级 Python 后端工程师",
  "jd_text": "熟悉 Django、MySQL、Redis，了解 Docker 和 Kubernetes",
  "use_llm": true
}
```

### POST /api/agent/chat — AI Agent 对话

直接与 AI 对话，Agent 会自动调用搜索、图谱工具：

```json
{
  "message": "我会 Python 和机器学习，北京有什么适合我的工作，薪资大概多少？",
  "session_id": "user_001"
}
```

### GET /api/stats — 系统统计

查看向量库和图谱的数据量统计，无需参数。

---

## 用户管理接口

以下接口需要在请求头中携带 Token（登录后获得）：

```
Authorization: Bearer <access_token>
```

在 `/docs` 页面点击右上角 **Authorize** 按钮粘贴 Token，即可直接测试。

### 个人资料

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/user/profile` | 查看个人资料 |
| PUT | `/api/user/profile` | 更新资料 |

**字段说明**（`UserProfile` 实际字段）：

| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | 姓名 |
| phone | string | 手机号 |
| city | string | 所在城市 |
| position | string | 期望岗位 |
| avatar_url | string | 头像 URL |
| bio | string | 个人简介 |

**更新示例**：
```json
{
  "name": "张三",
  "city": "北京",
  "position": "Python后端工程师",
  "bio": "3年后端开发经验"
}
```

### 简历管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/user/resume` | 查看简历 |
| PUT | `/api/user/resume` | 更新简历 |

**字段说明**（`UserResume` 实际字段）：

| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | 姓名 |
| school | string | 学校 |
| major | string | 专业 |
| degree | string | 学历（本科/硕士等） |
| skills | array | 技能列表 `["Python","MySQL"]` |
| expect_cities | array | 期望城市 `["北京","上海"]` |
| expect_salary_min | int | 期望薪资最低（K） |
| expect_salary_max | int | 期望薪资最高（K） |
| work_experience | string | 工作经历（文本） |
| projects | string | 项目经历（文本） |

**更新示例**：
```json
{
  "name": "张三",
  "degree": "本科",
  "skills": ["Python", "Django", "MySQL"],
  "expect_cities": ["北京", "上海"],
  "expect_salary_min": 15,
  "expect_salary_max": 25,
  "work_experience": "3年Python后端开发，负责..."
}
```

### 技能档案

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/user/skills` | 查看我的技能列表 |
| POST | `/api/user/skills` | 添加技能 |
| PUT | `/api/user/skills/{skill_name}` | 更新熟练度 |
| DELETE | `/api/user/skills/{skill_name}` | 删除技能 |

**添加技能示例**（`proficiency_level` 为 1-5 整数，不是字符串）：
```json
{
  "user_id": 1,
  "skill_name": "Python",
  "proficiency_level": 5,
  "years_of_experience": 3.0
}
```

熟练度等级参考：`1=了解  2=入门  3=熟悉  4=熟练  5=精通`

### 收藏职位

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/user/favorites` | 查看收藏的职位 |
| POST | `/api/user/favorites` | 收藏职位 |
| DELETE | `/api/user/favorites/{job_id}` | 取消收藏 |

**收藏示例**（必须提供 `title` 和 `company`）：
```json
{
  "user_id": 1,
  "job_id": "6f1fd88250c3f1a403Ny09",
  "title": "Python后端工程师",
  "company": "某科技公司",
  "salary_range": "20-35K",
  "city": "北京",
  "skills": ["Python", "Django", "MySQL"]
}
```

### 匹配报告 & 设置

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST/PUT | `/api/user/reports` | 查看/生成/更新求职分析报告 |
| GET/PUT | `/api/user/settings` | 查看/更新用户偏好设置 |

---

## 完整使用流程

### 场景一：完整求职流程（注册用户）

```
1. 注册账号          POST /api/auth/register
         ↓
2. 登录获取 Token    POST /api/auth/login
         ↓
3. 上传简历文本      PUT  /api/user/resume
         ↓
4. 提取简历技能      POST /api/skill/extract
         ↓
5. 保存到个人档案    POST /api/user/skills
         ↓
6. 分析与目标岗位的差距  POST /api/gap-analysis  （图谱版，含学习路径）
         ↓
7. 根据技能推荐岗位   POST /api/recommend        （图谱版，精准+扩展）
         ↓
8. 收藏感兴趣的职位   POST /api/user/favorites
         ↓
9. 深入了解市场行情   GET  /api/trend
```

---

### 场景二：快速搜索（无需注册）

```
1. 语义搜索职位      POST /api/search
   "会 Java，想找上海的后端岗位"
         ↓
2. 查看市场趋势      GET  /api/trend
   了解 Java 岗位常见的技能组合和薪资水平
         ↓
3. 技能差距分析      POST /api/gap-analysis
   对比自己和目标岗位的差距
```

---

### 场景三：探索市场行情（无需注册）

```
1. 市场趋势总览      GET  /api/trend
   查看热门技能 TOP 20、高薪技能、技能组合
         ↓
2. AI Agent 深入提问  POST /api/agent/chat
   "Kubernetes 岗位一般还需要哪些配套技能？"
         ↓
3. 图谱搜索验证      POST /api/search
   搜索具体的岗位样本
```

---

## 请求示例汇总

```bash
# 健康检查
curl http://localhost:8000/api/health

# ======= 图谱增强接口 =======

# 语义搜索
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query":"Python后端，熟悉Django和Redis","top_k":5,"city":"北京"}'

# 智能推荐
curl -X POST http://localhost:8000/api/recommend \
  -H "Content-Type: application/json" \
  -d '{"user_skills":["Python","Django","MySQL","Redis"],"top_k":10,"city":"上海"}'

# 技能差距分析
curl -X POST http://localhost:8000/api/gap-analysis \
  -H "Content-Type: application/json" \
  -d '{"user_skills":["Python","MySQL"],"target_position":"全栈开发工程师","city":"北京"}'

# 市场趋势
curl http://localhost:8000/api/trend

# ======= 认证接口 =======

# 注册
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"123456"}'

# 登录（复制返回的 access_token）
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"123456"}'

# ======= 用户接口（替换 <token>）=======

# 查看个人资料
curl http://localhost:8000/api/user/profile \
  -H "Authorization: Bearer <token>"

# 上传简历
curl -X PUT http://localhost:8000/api/user/resume \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"degree":"本科","skills":["Python","Django"],"expect_salary_min":15,"expect_salary_max":25}'

# 添加技能（proficiency_level 为 1-5 整数）
curl -X POST http://localhost:8000/api/user/skills \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"user_id":1,"skill_name":"Python","proficiency_level":5,"years_of_experience":3.0}'
```

---

## 注意事项

| 事项 | 说明 |
|------|------|
| `/api/trend` 依赖 Neo4j | 需要 Neo4j 服务正常运行，否则返回 503 |
| 图谱接口自动降级 | `/api/search`、`/api/recommend` 在 Neo4j 不可用时自动改用向量搜索 |
| `/api/gap-analysis` 精度 | 图谱版依赖 Neo4j 中的岗位技能关系；若无匹配岗位则降级为向量版 |
| Token 有效期 | 7 天，过期需重新登录 |
| 首次启动慢 | vLLM 加载约 1～2 分钟，等 `Application startup complete` 再访问 |
| top_k 上限 | 搜索/推荐接口最大返回 50 条 |
| 城市参数 | 填中文城市名，如 `"北京"`、`"上海"`、`"深圳"` |
