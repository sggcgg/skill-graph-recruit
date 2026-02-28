# 智能招聘系统 - 前端使用指南

## 快速开始

### 1. 启动后端服务

确保后端服务正在运行：

```bash
cd d:\PycharmProjects\skill-graph-recruit
# 启动后端服务
```

### 2. 启动前端服务

在另一个终端中启动前端：

```bash
cd d:\vscode_project\智能招聘_前端\frontend
npm run dev
```

前端服务将在 http://localhost:5173 启动

### 3. 访问系统

打开浏览器访问：http://localhost:5173

## 功能使用说明

### 1. 岗位搜索

- 访问 `/search` 页面
- 在搜索框中输入关键词（如：Python、Java等）
- 可以选择城市进行筛选
- 支持图谱增强搜索和RAG语义搜索

### 2. 技能图谱

- 访问 `/graph` 页面
- 查看技能之间的关系网络
- 支持节点拖拽、缩放、点击查看详情
- 展示热门技能和技能组合

### 3. AI助手

- 访问 `/chat` 页面
- 输入关于岗位、技能、职业发展等问题
- AI助手会提供智能回答
- 支持RAG搜索作为备选方案

### 4. 技能-岗位匹配看板

- 访问 `/match` 页面
- 输入你的技能（用逗号分隔）
- 输入目标岗位
- 系统会生成匹配度雷达图
- 显示技能差距和学习路径

### 5. 数据可视化报表

- 访问 `/analytics` 页面
- 查看技能热度趋势
- 查看技能分类分布
- 查看高薪技能排行榜
- 查看热门城市岗位分布
- 查看技能词云

### 6. 技能本体管理

- 访问 `/skill-management` 页面
- 查看所有技能列表
- 添加新技能
- 编辑现有技能
- 删除技能
- 管理技能同义词

### 7. 数据监控看板

- 访问 `/monitoring` 页面
- 查看服务状态（RAG、Agent、图谱服务等）
- 查看图谱规模（节点数、关系数）
- 查看API健康状况
- 查看系统日志

### 8. 用户中心

- 访问 `/user-center` 页面
- 管理个人资料
- 编辑简历
- 管理技能档案
- 查看收藏的岗位

## API接口说明

### 系统统计

```bash
GET /api/stats
```

返回：
- 岗位总数
- 技能总数
- 图谱节点数
- 图谱关系数

### 岗位搜索

```bash
POST /api/search
Content-Type: application/json

{
  "query": "Python开发工程师",
  "top_k": 50,
  "city": "北京"
}
```

### 技能差距分析

```bash
POST /api/gap-analysis
Content-Type: application/json

{
  "user_skills": ["Python", "Django", "MySQL"],
  "target_position": "全栈开发工程师"
}
```

### 市场趋势

```bash
GET /api/trend
```

返回：
- 热门技能列表
- 技能分类分布
- 技能组合
- 高薪技能

### AI对话

```bash
POST /api/agent/chat
Content-Type: application/json

{
  "message": "Python开发工程师需要什么技能？",
  "session_id": "session-123"
}
```

## 浏览器支持

推荐使用以下浏览器：

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## 常见问题

### 1. 页面无法加载

- 检查后端服务是否正常运行
- 检查浏览器控制台是否有错误
- 刷新页面尝试

### 2. 数据不显示

- 检查后端API是否返回数据
- 检查网络请求是否成功
- 查看浏览器控制台的网络请求

### 3. 图表不渲染

- 确保ECharts库已正确安装
- 检查图表容器是否有正确的尺寸
- 查看浏览器控制台是否有错误

## 开发指南

### 添加新页面

1. 在 `src/views/` 目录下创建新页面组件
2. 在 `src/router/index.ts` 中添加路由
3. 在 `src/components/Navbar.vue` 中添加导航链接

### 添加新API

1. 在 `src/api/` 目录下添加API接口定义
2. 在 `src/api/jobApi.ts` 或 `src/api/userApi.ts` 中添加API方法
3. 在后端实现对应的API端点

### 修改样式

1. 全局样式在 `src/styles/variables.scss` 中定义
2. 组件样式在组件的 `<style>` 标签中定义
3. 使用SCSS变量和Mixin来保持一致性

## 技术支持

如有问题，请查看：

- Vue 3文档：https://vuejs.org/
- Element Plus文档：https://element-plus.org/
- ECharts文档：https://echarts.apache.org/
- Vite文档：https://vitejs.dev/
