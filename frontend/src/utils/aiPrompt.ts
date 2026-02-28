/**
 * AI 提示词工具模块
 *
 * 统一为所有 AI 调用注入：
 *  1. 角色设定（系统人设）
 *  2. 输出格式规范（Markdown + 字数控制）
 *  3. 领域背景（招聘平台上下文）
 *
 * 使用方式：
 *   import { buildPrompt } from '@/utils/aiPrompt';
 *   const message = buildPrompt('learning_plan', { ... });
 *   await jobApi.chat({ message, session_id: ... });
 */

// ──────────────────────────────────────────────
// 系统角色前缀（注入到每条消息最前面）
// ──────────────────────────────────────────────
const SYSTEM_ROLE = `【角色设定】你是"智聘助手"，一位专注于中国IT行业的资深职业发展顾问（10年以上经验）。你熟悉：
- 国内主流招聘市场行情（北上广深杭成都等城市薪资水位）
- 互联网/AI/大数据/云计算等技术方向的岗位要求
- 技术技能的学习难度、市场热度、职业价值评估

【回答原则】
- 直接给出可操作的具体建议，不说废话和套话
- 数字估算要合理（如学习时间、薪资区间），宁可给范围也不要瞎猜
- Markdown 格式：用 **加粗** 标注重点，用 ## 分隔章节，用 - 列出要点
- 字数适中，不冗长（每个章节不超过 4 句话）
- 最后一定要有 1 句简洁的"行动建议"作为结尾

【背景】用户正在使用一个智能招聘平台查询技能-岗位匹配情况。

---
`

// ──────────────────────────────────────────────
// Markdown 渲染（所有 AI 结果共用）
// 支持：标题、加粗、斜体、代码、引用、有序/无序列表、表格
// ──────────────────────────────────────────────
export const renderMarkdown = (text: string): string => {
  if (!text) return ''

  const lines = text.split('\n')
  const result: string[] = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i] ?? ''
    const nextLine = lines[i + 1] ?? ''

    // ── 表格（连续的 | 行，第二行为分隔符）
    if (/^\|.+\|/.test(line) && /^\|[-| :]+\|/.test(nextLine)) {
      const headerCells = line.split('|').slice(1, -1).map(c => c.trim())
      result.push('<div class="md-table-wrap"><table class="md-table"><thead><tr>')
      headerCells.forEach(c => result.push(`<th>${inlineRender(c)}</th>`))
      result.push('</tr></thead><tbody>')
      i += 2
      while (i < lines.length && /^\|.+\|/.test(lines[i] ?? '')) {
        const cells = (lines[i] ?? '').split('|').slice(1, -1).map(c => c.trim())
        result.push('<tr>')
        cells.forEach(c => result.push(`<td>${inlineRender(c)}</td>`))
        result.push('</tr>')
        i++
      }
      result.push('</tbody></table></div>')
      continue
    }

    // ── 标题
    if (/^## (.+)$/.test(line)) {
      result.push(`<h3 class="md-h3">${inlineRender(line.replace(/^## /, ''))}</h3>`)
    } else if (/^### (.+)$/.test(line)) {
      result.push(`<h4 class="md-h4">${inlineRender(line.replace(/^### /, ''))}</h4>`)
    } else if (/^#### (.+)$/.test(line)) {
      result.push(`<h5 class="md-h5">${inlineRender(line.replace(/^#### /, ''))}</h5>`)

    // ── 有序列表
    } else if (/^(\d+)\. (.+)$/.test(line)) {
      const m = line.match(/^(\d+)\. (.+)$/)
      if (m) {
        result.push(`<li class="md-li-ol"><span class="md-ol-num">${m[1]}</span><span>${inlineRender(m[2] ?? '')}</span></li>`)
      }

    // ── 无序列表
    } else if (/^[-•*] (.+)$/.test(line)) {
      result.push(`<li class="md-li-ul">${inlineRender(line.replace(/^[-•*] /, ''))}</li>`)

    // ── 引用
    } else if (/^> (.+)$/.test(line)) {
      result.push(`<blockquote class="md-quote">${inlineRender(line.replace(/^> /, ''))}</blockquote>`)

    // ── 分割线
    } else if (/^---+$/.test(line.trim())) {
      result.push('<hr class="md-hr" />')

    // ── 空行
    } else if (line.trim() === '') {
      result.push('<div class="md-spacer"></div>')

    // ── 普通段落
    } else {
      result.push(`<p class="md-p">${inlineRender(line)}</p>`)
    }

    i++
  }

  return result.join('')
}

// 行内元素渲染（加粗、斜体、代码）
const inlineRender = (text: string): string => {
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code class="md-code">$1</code>')
}

// ──────────────────────────────────────────────
// 各场景 Prompt 构建器
// ──────────────────────────────────────────────

/** 学习路径规划 */
export const buildLearningPlanPrompt = (params: {
  targetPosition: string
  matchRate: number
  matchedSkills: string[]
  missingSkills: string[]
}) => {
  const { targetPosition, matchRate, matchedSkills, missingSkills } = params
  const matched = matchedSkills.slice(0, 12).join('、') || '暂无'
  const missing = missingSkills.slice(0, 12).join('、') || '暂无'

  return SYSTEM_ROLE + `## 任务：为用户制定学习路径规划

**目标岗位：** ${targetPosition}
**当前技能匹配率：** ${matchRate}%
**已掌握技能：** ${matched}
**需要补足技能：** ${missing}

请输出以下结构（严格按此格式）：

## 🎯 现状评估
（1-2句评估当前匹配率意味着什么）

## 📋 学习优先级
（按"先学什么 → 再学什么"列出，每项格式：- **技能名** · 预计X周 · 原因一句话）

## ⏱️ 整体时间规划
（给出从当前状态到基本胜任该岗位需要多久，分 乐观/正常/保守 三档）

## 🔥 行动第一步
（今天就可以开始的最具体的一个行动）`
}

/** 匹配报告 AI 解读 */
export const buildInterpretationPrompt = (params: {
  targetPosition: string
  matchRate: number
  matchedSkills: string[]
  missingSkills: string[]
}) => {
  const { targetPosition, matchRate, matchedSkills, missingSkills } = params
  const matched = matchedSkills.slice(0, 8).join('、') || '暂无'
  const missing = missingSkills.slice(0, 8).join('、') || '暂无'

  return SYSTEM_ROLE + `## 任务：解读技能匹配报告并给出提升建议

**目标岗位：** ${targetPosition}
**匹配率：** ${matchRate}%
**已具备：** ${matched}
**缺失：** ${missing}

请输出以下结构：

## 📊 竞争力评估
（这个匹配率在该岗位市场中处于什么水平？高于/低于平均竞争者？）

## 🔑 最关键的缺口
（列出 2-3 个最影响竞争力的缺失技能，说明为什么这些最重要）

## ✅ 你的核心优势
（已有技能中哪些是该岗位的加分项？）

## 📅 3个月提升计划
（具体、可执行的短期计划，不要泛泛而谈）

## 💡 一句话建议
（直接告诉用户：现在适不适合投这类岗位）`
}

/** 岗位 AI 点评 */
export const buildJobReviewPrompt = (params: {
  jobTitle: string
  company: string
  city: string
  salaryRange: string
  experience: string
  education: string
  jobSkills: string[]
  jobDocument: string
  userSkills: string[]
}) => {
  const { jobTitle, company, city, salaryRange, experience, education, jobSkills, jobDocument, userSkills } = params
  const jSkills = jobSkills.slice(0, 10).join('、') || '未知'
  const uSkills = userSkills.length ? userSkills.join('、') : '（用户未设置技能，请提示用户在个人中心添加技能以获得更准确的分析）'
  const doc = jobDocument.slice(0, 300)

  return SYSTEM_ROLE + `## 任务：快速点评某岗位是否适合该用户

**岗位：** ${jobTitle} @ ${company}（${city}）
**薪资：** ${salaryRange} | **经验：** ${experience} | **学历：** ${education}
**岗位技能要求：** ${jSkills}
**JD摘要：** ${doc}

**用户当前技能：** ${uSkills}

请用以下格式输出（总字数控制在150字以内，简洁有力）：

**适合度：** 💚高 / 💛中等 / 🔴低（选一个，后面一句理由）

**你的优势：** （1-2个已有的匹配点）

**关键缺口：** （最重要的1-2个不足）

**建议：** （"立即投递" / "补足X技能后再投" / "暂不建议"，一句话说明）`
}

/** 技能节点 AI 介绍 */
export const buildSkillIntroPrompt = (params: {
  skillName: string
  category: string
  jobCount?: number
  avgSalary?: number
  relatedSkills: string[]
}) => {
  const { skillName, category, jobCount, avgSalary, relatedSkills } = params
  const related = relatedSkills.slice(0, 6).join('、') || '暂无数据'
  const marketData = jobCount
    ? `图谱数据：${jobCount} 个相关岗位，平均薪资 ${avgSalary}K`
    : '（无图谱数据）'

  return SYSTEM_ROLE + `## 任务：介绍技术技能"${skillName}"

**技能分类：** ${category}
**市场数据：** ${marketData}
**关联技能（来自知识图谱）：** ${related}

请按以下结构输出：

## 💡 是什么
（2句话：核心定义 + 主要用途场景）

## 📈 市场价值
（结合图谱数据评估：市场热度、典型薪资区间、适合什么阶段的人学）

## 🛣️ 学习路径
（从零到能用：大概需要多久？推荐的学习顺序是什么？）

## 🔗 最佳技能搭配
（与上面关联技能中，哪2-3个搭配起来最有竞争力？为什么？）`
}

/** 用户技能档案诊断 */
export const buildDiagnosisPrompt = (params: {
  skills: Array<{ name: string; level: number }>
  expectCities?: string[]
  expectSalary?: number
}) => {
  const { skills, expectCities, expectSalary } = params
  const skillList = skills
    .map(s => `${s.name}（${['入门', '基础', '熟练', '精通', '专家'][s.level - 1] || '未知'}）`)
    .join('、')
  const cityInfo = expectCities?.length ? `期望城市：${expectCities.join('、')}` : ''
  const salaryInfo = expectSalary ? `期望薪资：${expectSalary}K` : ''

  return SYSTEM_ROLE + `## 任务：全面诊断用户的技能档案

**技能清单：** ${skillList || '未设置'}
${cityInfo}
${salaryInfo}

请按以下结构输出专业诊断报告：

## 🔍 技能组合诊断
（这些技能是否构成完整技术栈？优势点和薄弱点各是什么？）

## 🏆 市场竞争力
（在当前招聘市场，这套技能组合能达到什么竞争水平？）

## 🎯 最佳岗位方向
（列出 2-3 个最匹配的具体岗位，说明为什么合适）

## ⚠️ 关键短板
（最需要补充的 1-2 项技能，以及补足后能带来的薪资/竞争力提升）

## 📅 6个月行动计划
（分月份给出优先级最高的学习任务，要具体可执行）`
}
