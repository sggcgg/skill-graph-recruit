"""
职位推荐Agent
基于 LangGraph create_react_agent 实现多轮对话（兼容 LangChain 1.x）
"""
import asyncio
import logging
import yaml
from pathlib import Path
from typing import List, AsyncGenerator
import sys

# 添加项目根目录到path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from src.agent.tools import AgentTools

logger = logging.getLogger(__name__)

# 直接路径：可识别的城市名称
_CITIES = {
    '北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '南京', '西安', '重庆',
    '苏州', '天津', '合肥', '厦门', '长沙', '郑州', '宁波', '青岛', '济南', '大连',
}

SYSTEM_PROMPT = """你是「智聘助手」，专注中国 IT 就业市场的岗位推荐与职业规划助手。

# 核心决策规则（每次回复前必须先过一遍）

## 规则 A — 历史里有数据时，禁止重复检索
当用户使用以下任意追问词时：
"哪个更好"、"上面"、"前面"、"这些"、"这个"、"那个"、"哪个"、
"比较"、"对比"、"排序"、"适合我吗"、"推荐哪"、"第几个"

→ **对话历史已包含所需数据，立即分析，不得调用任何工具**
→ 违反此规则 = 额外等待 10 秒以上，用户体验极差

## 规则 B — 以下场景必须调对应工具，且仅调 1 次

### B1 — 岗位搜索/推荐（含以下词）
"帮我找"、"搜索"、"查找"、"推荐岗位"、"找职位"、"有哪些岗位"、"找一下"
- `search_jobs(query, city)` → query 填技能或岗位名；有城市时同步传 city
- `recommend_jobs(user_skills, city)` → user_skills 逗号分隔；有城市时传 city

### B2 — 技能差距分析（含以下词时必须调 analyze_skill_gap）
"技能差距"、"差距在哪"、"还差什么"、"还缺什么"、"缺哪些技能"、"帮我分析差距"、"做xxx需要什么技能"
- `analyze_skill_gap(user_skills, target_position)` → 用户未说明技能时，user_skills 传空字符串 ""，target_position 填目标岗位
- 工具会从图谱提取目标岗位高频技能并给出差距报告

### B3 — 技能图谱查询
- `query_skill_graph(skill_name)` → 查询单个技能的市场热度、薪资、关联岗位

**铁律：每轮最多调 1 次工具，调完立即回答，结果已有时绝不重调**

## 规则 C — 以下情况直接用知识回答，不调任何工具
- 闲聊、问候、感谢、表情
- 学习路径建议、学习计划制定（已有技能差距数据时可直接规划）
- 薪资行情估算（凭领域知识）
- 对已有搜索结果的分析、比较、推荐、评价

# 输出格式
- 追问 / 分析类：直接给出判断和具体建议，言简意赅，不绕弯
- 岗位列表：序号 + **加粗岗位名** + 薪资 + 地点 + 匹配技能
- 中文回复，专业简洁，避免无效废话"""

# 追问模式追加的动态提示（由 state_modifier 在检测到追问时注入）
# 参考 When2Call 2025 论文实践：显式声明"已有数据"可将不必要工具调用减少 50%+
_FOLLOWUP_ADDON = """

## ⚡ 本轮模式：对话历史分析（最高优先级覆盖）
系统已检测到本轮为追问类请求，对话历史中包含完整的岗位/数据。
本轮规则：**严禁调用任何工具**，直接基于已有数据分析并给出具体建议。"""

# 追问关键词（与 SYSTEM_PROMPT 规则 A 保持同步）
# 含这些词 + 无搜索意图 + 有 AI 历史回复 → 追问模式
_FOLLOWUP_WORDS = (
    '上面', '上边', '前面', '这些', '这个', '那些', '那个', '它们',
    '哪个', '哪些', '哪家', '比较', '对比', '更好', '更适合',
    '最好', '最适合', '第一个', '第二个', '第三个', '适合我', '推荐哪',
    '排序', '排一下', '怎么排', '第几', '哪一',
)
# 有这些词说明用户在发起新搜索，优先级高于追问词
_SEARCH_TRIGGER = ('搜索', '帮我找', '查找', '找岗位', '找职位', '搜一下', '有哪些岗位', '找一下')


class JobRecommendAgent:
    """
    职位推荐Agent（LangGraph create_react_agent，兼容 LangChain 1.x）

    功能:
    - 多轮对话（手动维护 messages 历史）
    - 自动调用工具（RAG检索、技能分析、Neo4j查询）
    - 记忆上下文
    """

    def __init__(self, config_path: str = "config.yaml", rag_service=None):
        """
        初始化Agent

        Args:
            config_path: 配置文件路径（相对于项目根目录）
            rag_service: 已有的 RAGService 实例（传入可避免重复加载 VectorDB/m3e-base）
        """
        logger.info("初始化职位推荐Agent...")

        _project_root = Path(__file__).parent.parent.parent
        config_file = _project_root / config_path
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        llm_config = config['llm']
        self._verbose = config.get('agent', {}).get('verbose', True)
        self._max_iterations = config.get('agent', {}).get('max_iterations', 3)

        # 初始化LLM
        # enable_thinking=False：关闭 Qwen3 系列的思维链(CoT)模式
        # 思维链默认开启，会让 AI 先内部"思考" 5-30 秒再回答，对话场景无必要
        self.llm = ChatOpenAI(
            base_url=llm_config['base_url'],
            api_key=llm_config['api_key'],
            model=llm_config['model'],
            temperature=llm_config.get('temperature', 0.3),
            max_tokens=llm_config.get('max_tokens', 1000),
            extra_body={"enable_thinking": False},
        )

        # 初始化工具（传入已有 rag_service 避免重复加载）
        self.agent_tools = AgentTools(rag_service=rag_service)
        self.tools = self.agent_tools.get_tools()

        # 使用 LangGraph create_react_agent（LangChain 1.x 推荐方式）
        # 创建两个 graph，兼容 LangGraph 1.0.x（state_modifier callable 签名在 1.0.x 不稳定）：
        # - graph: 通用路径（搜索/深度分析）
        # - followup_graph: 追问路径（末尾追加"禁止调工具"指令，防止重复检索）
        self.graph = create_react_agent(
            model=self.llm,
            tools=self.tools,
            prompt=SYSTEM_PROMPT,
        )
        self.followup_graph = create_react_agent(
            model=self.llm,
            tools=self.tools,
            prompt=SYSTEM_PROMPT + _FOLLOWUP_ADDON,
        )

        # 按 session_id 隔离的对话历史，避免多用户串话
        self._sessions: dict = {}

        logger.info(f"Agent初始化完成，可用工具: {len(self.tools)}")

    def close(self):
        """关闭 Agent 持有的外部连接（Neo4j 等）"""
        if self.agent_tools and self.agent_tools.neo4j_available:
            self.agent_tools.neo4j.close()

    def chat(self, user_input: str, session_id: str = "default") -> str:
        """
        对话接口（按 session_id 隔离，不同用户/会话互不干扰）

        Args:
            user_input: 用户输入
            session_id: 会话 ID，相同 ID 共享历史，不同 ID 互相隔离

        Returns:
            Agent响应
        """
        try:
            logger.info(f"[session={session_id}] 用户输入: {user_input}")

            # 获取或初始化该 session 的对话历史
            if session_id not in self._sessions:
                self._sessions[session_id] = []
            messages = self._sessions[session_id]

            # 追加用户消息
            messages.append(HumanMessage(content=user_input))

            # 限制历史长度
            MAX_HISTORY = 8
            if len(messages) > MAX_HISTORY:
                messages = messages[-MAX_HISTORY:]
                self._sessions[session_id] = messages

            # 调用 LangGraph agent（非流式接口，追问同样降低 recursion_limit）
            _fq = (
                any(w in user_input for w in _FOLLOWUP_WORDS)
                and not any(k in user_input for k in _SEARCH_TRIGGER)
                and len(messages) > 1
            )
            active = self.followup_graph if _fq else self.graph
            result = active.invoke(
                {"messages": messages},
                config={"recursion_limit": 3 if _fq else 8}
            )

            # 取最后一条 AIMessage 作为响应
            all_messages = result.get("messages", [])
            response = ""
            for msg in reversed(all_messages):
                if isinstance(msg, AIMessage):
                    response = msg.content
                    break

            if not response:
                response = "抱歉，未能生成有效回复。"

            # 用 graph 返回的完整消息列表更新该 session 历史
            self._sessions[session_id] = all_messages

            logger.info(f"[session={session_id}] Agent响应: {response[:100]}...")
            return response

        except Exception as e:
            logger.error(f"Agent处理失败: {e}")
            return f"抱歉，处理出错: {str(e)}"

    @staticmethod
    def _detect_direct_action(text: str):
        """
        检测是否为可直接执行的搜索/推荐意图，返回 (action, query, city)。
        action: None | 'search' | 'recommend'

        直接路径完全跳过 LangGraph 的两次 LLM 推断，响应速度从 5-10s 降到 <1s。
        只在意图明确时启用，复杂问题仍走 LangGraph。
        """
        stripped = text.strip()
        if len(stripped) > 80:
            return None, "", ""

        lower = stripped.lower()

        # ── 知识/建议类查询优先排除，交给 LLM 回答 ──────────────────────────────
        # 例："Python后端需要哪些技能"、"如何成为全栈工程师"、"Java薪资行情"
        knowledge_patterns = [
            '需要哪些', '需要什么', '哪些技能', '什么技能', '技能要求',
            '如何成为', '怎么成为', '如何学', '怎么学', '学习路径',
            '学习路线', '技术路线', '学什么', '需要掌握', '发展前景',
            '前景怎么', '薪资行情', '平均薪资', '平均工资', '工资水平',
            '年薪多少', '月薪多少', '大概多少', '有什么区别', '和.*的区别',
        ]
        # ── 技能差距/分析类查询排除直接路径，必须进 LangGraph 调 analyze_skill_gap ──
        # 例："我的技能差距在哪里"、"帮我分析技能差距"、"做xxx需要补充哪些技能"
        gap_analysis_patterns = [
            '技能差距', '差距在哪', '差距分析', '技能缺口', '差几个',
            '帮我分析', '分析一下', '分析我的', '我的差距', '目前的差距',
            '需要补充', '还需要学', '还差什么', '还缺什么', '还缺哪些',
        ]
        if any(w in stripped for w in knowledge_patterns):
            return None, "", ""
        if any(w in stripped for w in gap_analysis_patterns):
            return None, "", ""  # 路由到 LangGraph，由 analyze_skill_gap 工具处理

        # 搜索触发词（宽泛：以"找"开头、含"搜"等）
        search_triggers = [
            '帮我找', '帮找', '找找', '搜索', '搜一下', '查找', '查询',
            '有哪些', '有什么', '找一下', '找下',
        ]
        # "找" 单字触发：只在开头或明显是动词时（避免"找不到"等误触）
        starts_with_find = stripped.startswith('找') and len(stripped) >= 4
        # 推荐触发词（用户主动说出自己的技能）
        recommend_triggers = ['推荐', '适合我', '合适的岗位', '适合的职位']
        # 岗位相关词（判断是否为岗位搜索语境）
        job_words = [
            '职位', '岗位', '工作', '工程师', '开发', '程序员',
            '架构师', '运维', '测试', '产品经理', '数据',
            '全栈', '前端', '后端', '算法', '架构', 'devops',
        ]
        # 语义搜索信号：含这些词说明是模糊/语义查询，应走 RAG
        semantic_signals = ['类似', '相关', '提到', 'JD', 'jd', '描述', '说明', '涉及', '包含', '有关']

        has_job = any(w in stripped or w in lower for w in job_words)
        has_search = any(w in stripped for w in search_triggers) or starts_with_find
        has_recommend = any(w in stripped for w in recommend_triggers)
        has_semantic = any(w in stripped or w in lower for w in semantic_signals)

        if not has_job:
            return None, "", ""

        # 提取城市
        city = next((c for c in _CITIES if c in stripped), "")

        # 推荐意图：用户说"我会XXX"/"我懂XXX"等，或含"推荐"/"适合我"
        i_know = any(w in stripped for w in ('我会', '我懂', '我熟悉', '我学过', '我掌握'))
        if has_recommend or (i_know and (has_job or has_search)):
            return 'recommend', stripped, city

        # 搜索意图：有显式搜索词
        if has_search:
            return 'search', stripped, city

        # 语义搜索意图：含"类似/JD里/提到"等模糊描述 + 岗位词 → 走直接路径（RAG 兜底）
        # 例："找类似全栈开发的工作"、"JD 里提到微服务架构的岗位"
        if has_semantic and has_job:
            return 'search', stripped, city

        # 含职位关键词 + 城市（无其他触发词）
        if has_job and city:
            return 'search', stripped, city

        # 纯岗位词查询（5 字以上且不像闲聊/知识询问）
        # 例："全栈开发工程师"、"Python后端岗位"
        _not_search = ('怎么', '如何', '为什么', '什么是', '介绍', '解释', '区别',
                       '需要哪些', '需要什么', '哪些技能', '什么技能', '需要掌握',
                       '怎么学', '如何学', '学什么', '前景', '薪资')
        if has_job and len(stripped) >= 5 and not any(w in stripped for w in _not_search):
            return 'search', stripped, city

        return None, "", ""

    @staticmethod
    def _is_planning_query(text: str) -> bool:
        """
        判断是否为规划/建议/学习类查询，无需调用工具，直接走 LLM 流式回答。

        这类问题不需要检索岗位数据，LangGraph 反而会因为无法匹配工具而失败或超时。
        直接走 LLM 可以保证 100% 有回复，且速度更快。
        """
        # 注意：技能差距/分析类（'技能差距','差距分析','技能缺口','帮我分析','还缺什么'等）
        # 不在此列表——它们应路由到 LangGraph 由 analyze_skill_gap 工具处理。
        planning_keywords = [
            '学习计划', '学习路径', '学习路线', '提升计划', '技能提升计划',
            '如何提升', '怎么提升', '怎么学习', '如何学习', '学习建议',
            '求职建议', '职业规划', '职业发展', '成长路径', '发展方向',
            '帮我制定', '制定计划', '制定方案', '制定路线', '给我建议',
            '推荐资源', '学习资料', '学习顺序', '预计时间', '重点结合',
            '我还缺少', '我还缺',   # 来自 MatchDashboard 桥接 prompt，纯学习建议
            '简历优化', '简历分析', '简历建议', '简历改进', '优化建议',
            '面试技巧', '面试准备', '如何准备', '面试经验',
        ]
        return any(kw in text for kw in planning_keywords)

    @staticmethod
    def _is_simple_chat(text: str) -> bool:
        """
        判断是否为简单闲聊/问候，无需调用工具。
        简单问题直接走 LLM 流式，跳过 LangGraph 开销，首 token 更快。

        以下情况不走简单路径，交给 LangGraph 处理：
        1. 含技术关键词（岗位/技能/薪资等）
        2. 含追问代词（这些/他们/上面的等）——需要结合上文回答，LangGraph 更准确
        3. 含评估/比较类问题（适合/哪个更好/对比等）
        """
        text = text.strip()
        if len(text) > 40:
            return False

        # 追问上文的代词/连词 → 需要结合对话历史分析，走 LangGraph
        followup_words = [
            '这些', '这个', '那些', '那个', '它们', '他们', '上面', '前面',
            '刚才', '之前', '这份', '哪个', '哪些', '哪家', '比较', '对比',
            '更好', '更适合', '最好', '最适合', '有没有更', '还有吗',
        ]
        if any(w in text for w in followup_words):
            return False

        # 评估/分析类词 → 需要推理，走 LangGraph
        analysis_words = ['适合', '合适', '匹配', '适不适', '好不好', '怎么样', '如何', '评价']
        if any(w in text for w in analysis_words):
            return False

        # 技术关键词 → 交给 LangGraph 处理
        tech_keywords = [
            '岗位', '职位', '招聘', '工作', '技能', '薪资', '薪酬', '工资',
            '推荐', '搜索', '分析', '差距', '图谱', '学习', '路径', '转',
            'python', 'java', 'go', 'vue', 'react', 'node', 'docker',
            'k8s', 'ai', 'ml', '算法', '前端', '后端', '全栈', '运维',
        ]
        lower = text.lower()
        return not any(kw in lower for kw in tech_keywords)

    async def async_chat_stream(self, user_input: str, session_id: str = "default", mode: str = "auto") -> AsyncGenerator[str, None]:
        """
        流式对话接口 —— 通过 astream_events 逐 token 推送

        SSE 事件格式：
          event: session / data: <id>   —— 会话标识（前端 skip）
          event: tool_status / data: …  —— 思考阶段状态文字（旋转圈旁）
          data: <token>                 —— 文本 token
          data: [DONE]                  —— 流结束
          event: error / data: …        —— 错误
        """
        # ── 第一步：立即 yield 一个空注释，触发 HTTP 响应头发送 ───────────────────
        # 作用：让 FastAPI StreamingResponse 立刻发送 HTTP 响应头（session event
        # 已由 main.py 的 event_generator 发出，这里只需要让流开始即可），
        # 前端 fetch() 立刻 resolve → pushMsgBubble() → AI 气泡 + 旋转圈立刻出现。
        yield ": ping\n\n"

        try:
            logger.info(f"[stream][session={session_id}] 用户输入: {user_input}")

            if session_id not in self._sessions:
                self._sessions[session_id] = []
            messages = self._sessions[session_id]
            messages.append(HumanMessage(content=user_input))

            # 限制历史长度：最多保留最近 8 条（4 轮），防止 token 数膨胀拖慢 API
            MAX_HISTORY = 8
            if len(messages) > MAX_HISTORY:
                messages = messages[-MAX_HISTORY:]
                self._sessions[session_id] = messages

            # ── mode=llm：强制走模型，跳过所有工具 ───────────────────────────────────
            if mode == "llm":
                logger.info(f"[stream][session={session_id}] 强制模型模式")
                yield "event: source\ndata: llm\n\n"
                yield "event: tool_status\ndata: 💬 智聘助手回复中...\n\n"
                sys_msg = SystemMessage(content=SYSTEM_PROMPT)
                chat_messages = [sys_msg] + messages
                full_response = []
                async for chunk in self.llm.astream(chat_messages):
                    content = getattr(chunk, 'content', '') or ''
                    if content:
                        full_response.append(content)
                        safe = content.replace('\n', '\\n')
                        yield f"data: {safe}\n\n"
                yield "event: tool_status\ndata: \n\n"
                yield "data: [DONE]\n\n"
                messages.append(AIMessage(content="".join(full_response)))
                self._sessions[session_id] = messages
                return

            # ── 直接工具路径：意图明确的搜索/推荐，完全跳过 LangGraph 两次 LLM 推断 ──
            # 响应时间：LangGraph 5-10s → 直接路径 <2s（只有 Neo4j 查询）
            # mode=graph/rag 时强制走直接路径（跳过意图检测）
            if mode in ("graph", "rag"):
                auto_action = "search"  # 非 auto 时默认 search
                city = next((c for c in _CITIES if c in user_input), "")
                action = auto_action
            else:
                action, _, city = self._detect_direct_action(user_input)
            if action in ('search', 'recommend'):
                logger.info(f"[stream][session={session_id}] 直接工具路径: action={action}, city={city or '全国'}")
                tip = "⚡ 正在检索岗位数据库..." if action == 'search' else "🎯 正在匹配推荐岗位..."
                yield f"event: tool_status\ndata: {tip}\n\n"
                force_source = mode if mode in ("graph", "rag") else "auto"
                result_tuple = None
                try:
                    if action == 'search':
                        result_tuple = await asyncio.wait_for(
                            asyncio.to_thread(self.agent_tools.search_direct, user_input, city, force_source),
                            timeout=8.0,
                        )
                    else:
                        # skills 提取失败时改用 search_direct（不放弃直接路径）
                        skills = AgentTools._extract_skills(user_input)
                        if skills:
                            result_tuple = await asyncio.wait_for(
                                asyncio.to_thread(self.agent_tools.recommend_direct, skills, city, force_source),
                                timeout=8.0,
                            )
                        else:
                            # 没提取到技能词 → 退回 search_direct 兜底
                            result_tuple = await asyncio.wait_for(
                                asyncio.to_thread(self.agent_tools.search_direct, user_input, city, force_source),
                                timeout=8.0,
                            )
                except asyncio.TimeoutError:
                    logger.warning(f"[stream] 直接路径超时，降级到 LangGraph")
                    result_tuple = None
                except Exception as e:
                    logger.warning(f"[stream] 直接路径失败（{e}），降级到 LangGraph")
                    result_tuple = None

                if result_tuple:
                    result, source_type = result_tuple
                    logger.info(f"[stream] 直接路径返回 {len(result)} 字符，来源={source_type}")
                    # 通知前端数据来源（graph/rag）
                    yield f"event: source\ndata: {source_type}\n\n"
                    # 清除 tool_status，按段落分块推送
                    yield "event: tool_status\ndata: \n\n"
                    for para in result.split('\n\n'):
                        safe = para.replace('\n', '\\n')
                        if safe:
                            yield f"data: {safe}\\n\\n\n\n"
                    messages.append(AIMessage(content=result))
                    self._sessions[session_id] = messages
                    yield "data: [DONE]\n\n"
                    return
                # result 为空时静默降级到下面的路径

            # ── 简单闲聊快速路径：跳过 LangGraph，直接流式调 LLM ──
            if self._is_simple_chat(user_input):
                logger.info(f"[stream][session={session_id}] 简单对话快速路径")
                yield "event: source\ndata: llm\n\n"
                yield "event: tool_status\ndata: 💬 智聘助手回复中...\n\n"
                sys_msg = SystemMessage(content=SYSTEM_PROMPT)
                chat_messages = [sys_msg] + messages
                full_response = []
                async for chunk in self.llm.astream(chat_messages):
                    content = getattr(chunk, 'content', '') or ''
                    if content:
                        full_response.append(content)
                        safe = content.replace('\n', '\\n')
                        yield f"data: {safe}\n\n"
                if full_response:
                    messages.append(AIMessage(content=''.join(full_response)))
                    self._sessions[session_id] = messages
                yield "data: [DONE]\n\n"
                return

            # ── 规划/建议类快速路径：学习计划、简历建议等直接走 LLM，无需工具 ──
            # 这类问题 LangGraph 无法匹配合适的工具，常常超时或返回空，直接 LLM 更可靠
            if self._is_planning_query(user_input):
                logger.info(f"[stream][session={session_id}] 规划建议快速路径")
                yield "event: source\ndata: llm\n\n"
                yield "event: tool_status\ndata: 📝 AI 规划方案生成中...\n\n"
                sys_msg = SystemMessage(content=SYSTEM_PROMPT)
                chat_messages = [sys_msg] + messages
                full_response = []
                async for chunk in self.llm.astream(chat_messages):
                    content = getattr(chunk, 'content', '') or ''
                    if content:
                        full_response.append(content)
                        safe = content.replace('\n', '\\n')
                        yield f"data: {safe}\n\n"
                if full_response:
                    messages.append(AIMessage(content=''.join(full_response)))
                    self._sessions[session_id] = messages
                yield "data: [DONE]\n\n"
                return

            full_response = []
            tool_call_count = 0      # 累计工具调用次数
            final_answer_started = False  # 是否已进入最终回答阶段

            # 追问类问题：recursion_limit=3（最多 1 次工具调用后直接回答）
            # 普通问题：recursion_limit=8（允许多步推理）
            _is_followup_now = (
                any(w in user_input for w in _FOLLOWUP_WORDS)
                and not any(k in user_input for k in _SEARCH_TRIGGER)
                and len(messages) > 1
            )
            recursion = 3 if _is_followup_now else 8
            logger.info(f"[stream][session={session_id}] LangGraph 路径 recursion_limit={recursion} followup={_is_followup_now}")

            # LangGraph 路径：先标记为 llm，工具调用后通过 on_tool_end 更新为真实来源
            yield "event: source\ndata: llm\n\n"
            # 路径专属初始状态文字：让用户立刻知道 AI 在做什么
            if _is_followup_now:
                yield "event: tool_status\ndata: 📊 正在分析历史岗位数据...\n\n"
            else:
                yield "event: tool_status\ndata: 🧠 AI 深度分析中...\n\n"

            # 追问用 followup_graph（已内置"禁止调工具"指令），普通用 graph
            active_graph = self.followup_graph if _is_followup_now else self.graph

            async for event in active_graph.astream_events(
                {"messages": messages},
                config={"recursion_limit": recursion},
                version="v2",
            ):
                kind = event.get("event", "")

                # ── LLM 开始生成（规划 or 最终回答）：更新状态文字
                if kind == "on_chat_model_start":
                    if tool_call_count == 0:
                        # 第一次 LLM 调用：正在规划 / 准备回答
                        status = "✍️ 正在组织回答..." if _is_followup_now else "🤔 AI 正在推理..."
                    else:
                        # 工具调用结束后的 LLM 调用：正在整合结果
                        status = "✍️ 正在整合结果..."
                    yield f"event: tool_status\ndata: {status}\n\n"

                # ── 工具调用开始：推送精确的进度文字
                elif kind == "on_tool_start":
                    tool_name = event.get("name", "")
                    tool_tips = {
                        "search_jobs": "🔍 正在检索岗位数据库...",
                        "analyze_skill_gap": "📊 正在分析技能差距...",
                        "recommend_jobs": "🎯 正在匹配推荐岗位...",
                        "query_skill_graph": "🧠 正在查询技能图谱...",
                    }
                    tip = tool_tips.get(tool_name, f"⚙️ 正在处理: {tool_name}...")
                    tool_call_count += 1
                    yield f"event: tool_status\ndata: {tip}\n\n"

                # ── 工具调用结束：更新真实来源 + 切换为"整合结果"状态
                elif kind == "on_tool_end" and tool_call_count > 0:
                    # 根据调用的工具名推断数据来源
                    tool_name = event.get("name", "")
                    if tool_name in ("search_jobs", "recommend_jobs"):
                        # 图谱/RAG 工具：尝试从输出判断来源
                        tool_output = event.get("data", {}).get("output", "")
                        is_rag_output = isinstance(tool_output, str) and "图谱" not in tool_output[:20]
                        detected = "rag" if is_rag_output else "graph"
                        yield f"event: source\ndata: {detected}\n\n"
                    yield f"event: tool_status\ndata: ✍️ 正在整合结果...\n\n"

                # ── LLM token 流
                elif kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if not chunk:
                        continue
                    content = getattr(chunk, "content", None)
                    if not content:
                        continue

                    # 判断是规划 token（tool_call_chunks）还是最终回答 token
                    tool_call_chunks = getattr(chunk, "tool_call_chunks", None)
                    if tool_call_chunks:
                        # 规划阶段：LLM 在决定调用哪个工具，不推送内容
                        continue

                    # 最终回答阶段 token
                    if not final_answer_started and tool_call_count > 0:
                        # 工具调完后的第一个 token，加换行分隔
                        final_answer_started = True

                    full_response.append(content)
                    safe_token = content.replace("\n", "\\n")
                    yield f"data: {safe_token}\n\n"

            # ── LangGraph 兜底：若无文字输出，降级为直接 LLM 流式回答 ──────────────
            # 原因：LLM 规划 token 被过滤、recursion_limit 耗尽、API 超时等均可导致
            # full_response 为空，前端会显示"未能生成回复"。降级确保用户始终有回复。
            if not full_response:
                logger.warning(f"[stream][session={session_id}] LangGraph 无文字输出，降级为直接 LLM 回答")
                yield "event: tool_status\ndata: 💬 整理回复中...\n\n"
                sys_msg = SystemMessage(content=SYSTEM_PROMPT)
                async for chunk in self.llm.astream([sys_msg] + messages):
                    content = getattr(chunk, "content", "") or ""
                    if content:
                        full_response.append(content)
                        safe = content.replace("\n", "\\n")
                        yield f"data: {safe}\n\n"

            # 更新对话历史
            if full_response:
                complete_text = "".join(full_response).replace("\\n", "\n")
                messages.append(AIMessage(content=complete_text))
                self._sessions[session_id] = messages

            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"[stream] Agent流式处理失败: {e}", exc_info=True)
            err_safe = str(e).replace("\n", " ")
            # 异常降级：尝试用直接 LLM 兜底，彻底失败才返回 error 事件
            try:
                logger.info(f"[stream][session={session_id}] 异常后降级为直接 LLM 兜底")
                yield "event: tool_status\ndata: 💬 重新生成回复...\n\n"
                sys_msg = SystemMessage(content=SYSTEM_PROMPT)
                fallback_resp = []
                async for chunk in self.llm.astream([sys_msg] + messages):
                    content = getattr(chunk, "content", "") or ""
                    if content:
                        fallback_resp.append(content)
                        safe = content.replace("\n", "\\n")
                        yield f"data: {safe}\n\n"
                if fallback_resp:
                    messages.append(AIMessage(content="".join(fallback_resp)))
                    self._sessions[session_id] = messages
                    yield "data: [DONE]\n\n"
                    return
            except Exception as e2:
                logger.error(f"[stream] 兜底 LLM 也失败: {e2}")
            yield f"event: error\ndata: 抱歉，处理出错: {err_safe}\n\n"
            yield "data: [DONE]\n\n"

    def reset_memory(self, session_id: str = None):
        """
        重置对话历史

        Args:
            session_id: 指定会话 ID 则只重置该会话；为 None 则清空所有会话
        """
        if session_id is not None:
            self._sessions.pop(session_id, None)
            logger.info(f"会话 {session_id} 历史已清空")
        else:
            self._sessions.clear()
            logger.info("所有会话历史已清空")


def interactive_chat():
    """交互式对话"""
    print("="*80)
    print("职位推荐Agent - 交互式对话")
    print("="*80)
    print("\n欢迎使用智能职位推荐系统！")
    print("\n我可以帮你:")
    print("  1. 搜索相关岗位")
    print("  2. 分析技能差距")
    print("  3. 推荐合适岗位")
    print("  4. 查询技能信息")
    print("\n输入 'exit' 或 'quit' 退出")
    print("输入 'reset' 重置对话历史")
    print("\n" + "="*80 + "\n")
    
    try:
        # 初始化Agent
        agent = JobRecommendAgent()
        print("✅ Agent初始化成功！可以开始对话了。\n")
        
        # 对话循环
        while True:
            try:
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['exit', 'quit']:
                    print("\n再见！👋")
                    break
                
                if user_input.lower() == 'reset':
                    agent.reset_memory()
                    print("✅ 对话历史已重置\n")
                    continue
                
                print()  # 空行
                response = agent.chat(user_input)
                print(f"\nAgent: {response}\n")
                print("-"*80 + "\n")
                
            except KeyboardInterrupt:
                print("\n\n再见！👋")
                break
            except Exception as e:
                print(f"\n❌ 错误: {e}\n")
                continue
    
    except Exception as e:
        print(f"\n❌ Agent初始化失败: {e}")
        print("\n请检查:")
        print("  1. config.yaml中的API Key是否正确")
        print("  2. 向量数据库是否已初始化")
        print("  3. Neo4j是否正在运行")


def test_agent():
    """测试Agent功能"""
    print("="*80)
    print("测试职位推荐Agent")
    print("="*80)
    
    try:
        # 初始化Agent
        print("\n【初始化Agent】")
        agent = JobRecommendAgent()
        print("✅ 初始化成功\n")
        
        # 测试对话
        test_conversations = [
            "我会Python和Django，推荐什么岗位?",
            "我还需要学习什么技能?",
            "北京有哪些Python后端的岗位?"
        ]
        
        print("【测试对话】")
        for i, user_input in enumerate(test_conversations, 1):
            print(f"\n--- 对话 {i} ---")
            print(f"You: {user_input}")
            
            response = agent.chat(user_input)
            print(f"\nAgent: {response[:300]}...")
            
            if i < len(test_conversations):
                print("\n" + "-"*80)
        
        print("\n" + "="*80)
        print("🎉 测试完成！")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")


if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(description="职位推荐Agent")
    parser.add_argument(
        '--test',
        action='store_true',
        help='运行测试模式'
    )
    
    args = parser.parse_args()
    
    if args.test:
        test_agent()
    else:
        interactive_chat()
