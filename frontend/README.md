# 智能招聘系统 - 前端

## 项目简介

这是一个基于Vue3 + TypeScript + Element Plus构建的智能招聘系统前端应用，集成了RAG搜索、Neo4j知识图谱、Agent对话等多种AI技术。

## 功能模块

### 1. 主交互平台
- **首页** - 系统概览和统计数据展示
- **岗位搜索** - 支持图谱增强搜索和RAG语义搜索
- **技能图谱** - 基于Neo4j的技能关系可视化
- **AI助手** - 基于Agent的智能对话系统

### 2. 技能管理
- **技能-岗位匹配看板** - 雷达图展示技能匹配度
- **技能本体管理** - 技能词典的增删改查操作
- **数据可视化报表** - 折线图、饼图、词云等数据可视化

### 3. 用户系统
- **用户中心** - 个人资料、简历管理、技能档案
- **收藏岗位** - 用户收藏的岗位列表
- **技能跟踪** - 个人技能学习进度

### 4. 系统监控
- **数据监控看板** - 图谱规模、API健康状况监控
- **系统日志** - 系统运行日志查看

## 技术栈

### 前端框架
- Vue 3 + TypeScript
- Element Plus UI组件库
- Vue Router路由管理
- Pinia状态管理
- ECharts数据可视化
- D3.js图谱可视化

### 后端集成
- RAG搜索 - ChromaDB向量库
- Agent对话 - Qwen3.5-Plus API
- 知识图谱 - Neo4j
- 向量嵌入 - m3e-base模型

## 项目结构

```
frontend/
├── src/
│   ├── api/              # API接口定义
│   │   ├── jobApi.ts     # 岗位相关API
│   │   └── userApi.ts    # 用户相关API
│   ├── components/       # 公共组件
│   │   ├── AIButton.vue  # AI风格按钮
│   │   ├── GlassCard.vue # 玻璃拟态卡片
│   │   ├── Navbar.vue    # 导航栏
│   │   ├── SkillTag.vue  # 技能标签
│   │   └── ...
│   ├── router/           # 路由配置
│   │   └── index.ts
│   ├── store/            # Pinia状态管理
│   ├── styles/           # 样式文件
│   │   ├── global.scss
│   │   └── variables.scss
│   ├── views/            # 页面组件
│   │   ├── Home.vue
│   │   ├── JobSearch.vue
│   │   ├── SkillGraph.vue
│   │   ├── Chat.vue
│   │   ├── MatchDashboard.vue
│   │   ├── Analytics.vue
│   │   ├── SkillManagement.vue
│   │   ├── Monitoring.vue
│   │   └── UserCenter.vue
│   ├── App.vue
│   └── main.ts
├── public/
└── package.json
```

## 启动项目

### 前置要求
- Node.js >= 18.0.0
- npm >= 9.0.0

### 安装依赖
```bash
npm install
```

### 启动开发服务器
```bash
npm run dev
```

### 构建生产版本
```bash
npm run build
```

## API接口

### 岗位相关API
- `POST /api/search` - 图谱增强搜索
- `POST /api/recommend` - 图谱增强推荐
- `POST /api/gap-analysis` - 技能差距分析
- `GET /api/trend` - 市场趋势数据

### RAG搜索API
- `POST /api/rag/search` - 语义搜索

### Agent API
- `POST /api/agent/chat` - AI对话

### 用户API
- `POST /api/user/login` - 登录
- `POST /api/user/register` - 注册
- `GET /api/user/profile` - 获取用户信息
- `PUT /api/user/profile` - 更新用户信息

### 系统API
- `GET /api/stats` - 系统统计
- `GET /api/health` - 健康检查

## 路由配置

| 路由 | 页面 | 描述 |
|------|------|------|
| `/` | Home | 首页 |
| `/search` | JobSearch | 岗位搜索 |
| `/graph` | SkillGraph | 技能图谱 |
| `/chat` | Chat | AI助手 |
| `/match` | MatchDashboard | 匹配看板 |
| `/analytics` | Analytics | 数据报表 |
| `/skill-management` | SkillManagement | 技能管理 |
| `/monitoring` | Monitoring | 监控看板 |
| `/user-center` | UserCenter | 用户中心 |

## 开发规范

### 代码风格
- 使用TypeScript进行类型检查
- 遵循Vue 3 Composition API规范
- 使用ESLint和Prettier进行代码格式化

### 组件命名
- 使用PascalCase命名组件
- 文件名使用PascalCase或kebab-case

### 样式规范
- 使用SCSS进行样式编写
- 使用CSS变量进行主题管理
- 遵循BEM命名规范

## 浏览器支持

- Chrome (最新版本)
- Firefox (最新版本)
- Safari (最新版本)
- Edge (最新版本)

## 许可证

MIT License
