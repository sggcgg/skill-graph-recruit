"""
Agent工具定义
定义Agent可以调用的工具集（使用 @tool 装饰器，兼容 LangGraph astream_events）
"""
import logging
from typing import List
from pathlib import Path
import sys

# 添加项目根目录到path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from langchain_core.tools import tool, BaseTool
from src.rag.rag_service import RAGService

logger = logging.getLogger(__name__)


class AgentTools:
    """Agent可用的工具集"""

    def __init__(self, rag_service: RAGService = None):
        """
        初始化工具

        Args:
            rag_service: 已有的 RAGService 实例（复用，避免重复加载 VectorDB 和 LLM）。
                         为 None 时自动创建（独立使用场景）。
        """
        logger.info("初始化Agent工具...")

        # 复用已有 RAGService，避免重复加载 m3e-base embedding 模型
        if rag_service is not None:
            self.rag = rag_service
            logger.info("复用已有 RAGService 实例")
        else:
            self.rag = RAGService()
            logger.info("新建 RAGService 实例")

        # 初始化Neo4j管理器（可选）
        try:
            from src.graph_builder.neo4j_manager import Neo4jManager
            import yaml

            project_root_local = Path(__file__).parent.parent.parent
            config_path = project_root_local / 'config.yaml'

            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            neo4j_config = config['neo4j']
            self.neo4j = Neo4jManager(
                uri=neo4j_config['uri'],
                user=neo4j_config['user'],
                password=neo4j_config['password']
            )
            self.neo4j_available = True
            logger.info("Neo4j连接成功")
        except Exception as e:
            logger.warning(f"Neo4j连接失败: {e}")
            self.neo4j = None
            self.neo4j_available = False

        logger.info("Agent工具初始化完成")

    # 常用技能词典（用于从用户输入中快速提取技能名称）
    _SKILLS_DICT = {
        'python': 'Python', 'java': 'Java', 'go': 'Go', 'golang': 'Go',
        'c++': 'C++', 'c#': 'C#', 'rust': 'Rust', 'kotlin': 'Kotlin', 'swift': 'Swift',
        'vue': 'Vue', 'vue.js': 'Vue', 'react': 'React', 'angular': 'Angular',
        'node': 'Node.js', 'node.js': 'Node.js', 'nodejs': 'Node.js',
        'typescript': 'TypeScript', 'ts': 'TypeScript',
        'javascript': 'JavaScript', 'js': 'JavaScript',
        'html': 'HTML', 'css': 'CSS', 'sass': 'Sass',
        'spring': 'Spring', 'spring boot': 'Spring Boot', 'springboot': 'Spring Boot',
        'django': 'Django', 'flask': 'Flask', 'fastapi': 'FastAPI',
        'docker': 'Docker', 'k8s': 'Kubernetes', 'kubernetes': 'Kubernetes',
        'mysql': 'MySQL', 'redis': 'Redis', 'mongodb': 'MongoDB',
        'postgresql': 'PostgreSQL', 'postgres': 'PostgreSQL',
        'elasticsearch': 'Elasticsearch', 'kafka': 'Kafka', 'rabbitmq': 'RabbitMQ',
        'nginx': 'Nginx', 'linux': 'Linux', 'git': 'Git',
        'aws': 'AWS', 'azure': 'Azure', 'gcp': 'GCP',
        'tensorflow': 'TensorFlow', 'pytorch': 'PyTorch',
        '前端': '前端开发', '后端': '后端开发', '全栈': '全栈开发',
        '运维': '运维', '算法': '算法', 'devops': 'DevOps',
    }

    @staticmethod
    def _extract_skills(text: str) -> List[str]:
        """从文本中提取技能名称（字典匹配，无 LLM 开销）"""
        text_lower = text.lower()
        found = []
        # 优先匹配多字技能（避免 "node.js" 被 "node" 先命中）
        for kw in sorted(AgentTools._SKILLS_DICT, key=len, reverse=True):
            if kw in text_lower and AgentTools._SKILLS_DICT[kw] not in found:
                found.append(AgentTools._SKILLS_DICT[kw])
        return found

    def search_direct(self, query: str, city: str = "", force_source: str = "auto") -> tuple:
        """核心搜索逻辑（供 @tool 包装和快速路径直接调用共用）
        返回 (text, source_type)，source_type 为 'graph' 或 'rag'
        """
        city_val = city.strip() if city and city.strip() else None
        logger.info(f"[搜索] query={query}, city={city_val or '全国'}")

        rows = []
        if force_source != "rag" and self.neo4j_available and self.neo4j:
            try:
                matched_skills = AgentTools._extract_skills(query)
                if matched_skills:
                    rows = self.neo4j.execute_query("""
                        MATCH (j:Job)-[:REQUIRES]->(s:Skill)
                        WHERE s.name IN $skills AND ($city IS NULL OR j.city = $city)
                        WITH j, collect(DISTINCT s.name) AS ms, count(DISTINCT s) AS cnt
                        ORDER BY cnt DESC LIMIT 8
                        OPTIONAL MATCH (j)-[:POSTED_BY]->(c:Company)
                        RETURN j.title AS title, coalesce(c.name,'') AS company,
                               j.city AS city,
                               coalesce(j.salary_min,0) AS smin,
                               coalesce(j.salary_max,0) AS smax,
                               coalesce(j.experience,'') AS exp,
                               ms AS matched_skills, cnt
                    """, {"skills": matched_skills, "city": city_val})
                else:
                    keywords = [w for w in query.replace('，', ' ').replace(',', ' ').split()
                                if len(w) >= 2][:3] or [query[:15]]
                    kw_params = {f"kw{i}": kw.replace("'", "") for i, kw in enumerate(keywords)}
                    where = " OR ".join([f"j.title CONTAINS $kw{i}" for i in range(len(keywords))])
                    rows = self.neo4j.execute_query(f"""
                        MATCH (j:Job) WHERE ({where})
                          AND ($city IS NULL OR j.city = $city)
                        WITH j LIMIT 8
                        OPTIONAL MATCH (j)-[:POSTED_BY]->(c:Company)
                        OPTIONAL MATCH (j)-[:REQUIRES]->(s:Skill)
                        RETURN j.title AS title, coalesce(c.name,'') AS company,
                               j.city AS city,
                               coalesce(j.salary_min,0) AS smin,
                               coalesce(j.salary_max,0) AS smax,
                               coalesce(j.experience,'') AS exp,
                               collect(DISTINCT s.name) AS matched_skills, 1 AS cnt
                    """, {"city": city_val, **kw_params})
            except Exception as e:
                logger.warning(f"[搜索] Neo4j 查询失败，降级到 RAG: {e}")
                rows = []

        # Neo4j 有结果 → 直接返回图谱结果
        if rows:
            city_desc = f"（{city_val}）" if city_val else "（全国）"
            lines = [f"找到 **{len(rows)}** 个相关岗位 {city_desc}:\n"]
            for i, r in enumerate(rows, 1):
                sal = f"{r['smin']}-{r['smax']}K" if r.get('smax') else "面议"
                exp = f" | 经验：{r['exp']}" if r.get('exp') else ""
                skills_str = "、".join((r.get('matched_skills') or [])[:5])
                lines.append(
                    f"{i}. **{r['title']}**\n"
                    f"   🏢 {r['company'] or '未知公司'} | 📍 {r['city']} | 💰 {sal}{exp}\n"
                    f"   匹配技能：{skills_str or '—'}"
                )
            return "\n".join(lines), "graph"   # ← Neo4j 图谱命中

        # Neo4j 无结果或不可用 → RAG 语义检索兜底（对模糊/语义查询效果更好）
        if force_source == "graph":
            return "图谱中未找到匹配岗位，可尝试切换到 RAG 语义检索模式。", "graph"

        logger.info(f"[搜索] Neo4j 无结果，切换到 RAG 语义检索: query={query}")
        filters = {"city": city_val} if city_val else None
        result = self.rag.search_and_summarize(query, top_k=8, filters=filters)
        jobs = result.get('retrieved_jobs', [])
        if not jobs:
            return f"未找到与「{query}」相关的岗位，请尝试换个关键词。", "rag"
        city_desc = f"（{city_val}）" if city_val else ""
        lines = [f"找到 **{len(jobs)}** 个相关岗位{city_desc}:\n"]
        for i, job in enumerate(jobs[:8], 1):
            # RAG 结果补充技能信息
            skills_str = "、".join(job.get('skills', [])[:5])
            sim = job.get('similarity', 0)
            lines.append(
                f"{i}. **{job['title']}**\n"
                f"   🏢 {job['company']} | 📍 {job['city']} | 💰 {job['salary_range']}\n"
                f"   {'匹配技能：' + skills_str if skills_str else f'语义相似度：{sim:.0%}'}"
            )
        return "\n".join(lines), "rag"   # ← RAG 向量库命中

    def recommend_direct(self, user_skills: List[str], city: str = "", force_source: str = "auto") -> tuple:
        """核心推荐逻辑（供 @tool 包装和快速路径直接调用共用）
        返回 (text, source_type)，source_type 为 'graph' 或 'rag'
        """
        city_val = city.strip() if city and city.strip() else None
        logger.info(f"[推荐] skills={user_skills}, city={city_val or '全国'}")

        rows = []
        if force_source != "rag" and self.neo4j_available and self.neo4j and user_skills:
            try:
                rows = self.neo4j.execute_query("""
                    MATCH (j:Job)-[:REQUIRES]->(s:Skill)
                    WHERE s.name IN $skills AND ($city IS NULL OR j.city = $city)
                    WITH j, collect(DISTINCT s.name) AS matched, count(DISTINCT s) AS cnt
                    ORDER BY cnt DESC LIMIT 8
                    OPTIONAL MATCH (j)-[:POSTED_BY]->(c:Company)
                    RETURN j.title AS title, coalesce(c.name,'') AS company,
                           j.city AS city,
                           coalesce(j.salary_min,0) AS smin,
                           coalesce(j.salary_max,0) AS smax,
                           matched, cnt
                """, {"skills": user_skills, "city": city_val})
            except Exception as e:
                logger.warning(f"[推荐] Neo4j 查询失败，降级到 RAG: {e}")
                rows = []

        # Neo4j 有结果 → 直接返回图谱推荐
        if rows:
            city_desc = f"（{city_val}）" if city_val else ""
            lines = [f"基于您的技能（{', '.join(user_skills)}），推荐以下岗位{city_desc}:\n"]
            for i, r in enumerate(rows, 1):
                sal = f"{r['smin']}-{r['smax']}K" if r.get('smax') else "面议"
                matched_str = "、".join(r['matched'][:5])
                lines.append(
                    f"{i}. **{r['title']}**\n"
                    f"   🏢 {r['company'] or '未知公司'} | 📍 {r['city']} | 💰 {sal}\n"
                    f"   命中技能（{r['cnt']} 个）：{matched_str}"
                )
            return "\n".join(lines), "graph"   # ← Neo4j 图谱命中

        # Neo4j 无结果 → RAG 兜底
        if force_source == "graph":
            return "图谱中未找到匹配岗位，可尝试切换到 RAG 语义检索模式。", "graph"

        logger.info(f"[推荐] Neo4j 无结果，切换到 RAG: skills={user_skills}")
        filters = {"city": city_val} if city_val else None
        result = self.rag.recommend_jobs(user_skills, top_k=8, filters=filters)
        jobs = result.get('retrieved_jobs', [])
        if not jobs:
            return "未找到匹配的岗位推荐。", "rag"
        lines = ["基于您的技能，推荐以下岗位:\n"]
        for i, job in enumerate(jobs[:8], 1):
            # 补充匹配技能信息
            skills_str = "、".join(job.get('skills', [])[:5])
            sim = job.get('similarity', 0)
            lines.append(
                f"{i}. **{job['title']}** | 📍 {job['city']} | 💰 {job['salary_range']}\n"
                f"   {'匹配技能：' + skills_str if skills_str else f'语义相似度：{sim:.0%}'}"
            )
        return "\n".join(lines), "rag"   # ← RAG 向量库命中

    def get_tools(self) -> List[BaseTool]:
        """
        返回工具列表（使用 @tool 装饰器的 StructuredTool，兼容 LangGraph astream_events）

        Returns:
            LangChain BaseTool 列表
        """
        # @tool 包装只负责参数描述，核心逻辑在上面的方法里，避免代码重复
        search_direct = self.search_direct
        recommend_direct = self.recommend_direct
        rag = self.rag
        _neo4j = self.neo4j if self.neo4j_available else None

        @tool
        def search_jobs(query: str, city: str = "") -> str:
            """搜索相关岗位。优先使用图谱数据库（快速、精准），支持按城市筛选。
            Args:
                query: 技能或岗位关键词，例如 "Vue Node.js"、"Python后端工程师"、"Java开发"
                city: 城市筛选（可选），例如 "北京"、"上海"、"深圳"。不填则搜索全国
            Returns:
                匹配的岗位列表（含职位名称、公司、城市、薪资、所需技能）
            """
            text, _ = search_direct(query, city)   # LangGraph 只需要文本
            return text

        @tool
        def recommend_jobs(user_skills: str, city: str = "") -> str:
            """基于用户已有技能推荐最匹配的岗位（按技能命中数排序）。
            Args:
                user_skills: 用户技能，多个技能用英文逗号分隔，例如 "Vue,Node.js,MySQL"
                city: 城市（可选），例如 "北京"、"上海"。不填则搜索全国
            Returns:
                推荐岗位列表（按技能匹配度降序）
            """
            skills_list = [s.strip() for s in user_skills.replace('，', ',').split(',') if s.strip()]
            text, _ = recommend_direct(skills_list, city)   # LangGraph 只需要文本
            return text

        @tool
        def analyze_skill_gap(user_skills: str, target_position: str) -> str:
            """分析用户技能与目标岗位的差距，给出需要补充的技能和学习建议。
            Args:
                user_skills: 用户当前掌握的技能，多个技能用英文逗号分隔，例如 "Python,Django,MySQL"
                target_position: 目标岗位名称，例如 "高级Python后端工程师"
            Returns:
                差距分析和学习建议
            """
            try:
                logger.info(f"[工具调用] 技能差距分析: {user_skills} -> {target_position}")
                skills_list = [s.strip() for s in user_skills.replace('，', ',').split(',') if s.strip()]

                if _neo4j:
                    # 从图谱获取目标岗位高频技能
                    kw = target_position.replace("'", "")[:30]
                    skill_rows = _neo4j.execute_query("""
                        MATCH (j:Job)-[:REQUIRES]->(s:Skill)
                        WHERE j.title CONTAINS $kw
                        WITH s.name AS skill, count(j) AS freq ORDER BY freq DESC LIMIT 15
                        RETURN skill, freq
                    """, {"kw": kw})

                    if skill_rows:
                        required = [r['skill'] for r in skill_rows]
                        user_set = set(skills_list)
                        matched = sorted(set(required) & user_set)
                        missing = sorted(set(required) - user_set)
                        rate = len(matched) / len(required) if required else 0
                        lines = [
                            f"**目标岗位**：{target_position}",
                            f"**匹配率**：{rate:.0%}（已掌握 {len(matched)}/{len(required)} 个核心技能）\n",
                            f"✅ **已掌握**：{', '.join(matched) or '（无）'}",
                            f"📌 **待补充**：{', '.join(missing[:10]) or '（无）'}",
                        ]
                        if missing:
                            lines.append(f"\n💡 **建议优先学习**：{', '.join(missing[:5])}")
                        return "\n".join(lines)

                # RAG 兜底
                result = rag.skill_gap_analysis(user_skills=skills_list, target_position=target_position.strip())
                output = [
                    f"用户技能: {', '.join(result['user_skills'])}",
                    f"目标岗位: {result['target_position']}\n",
                ]
                for i, job in enumerate(result.get('target_jobs', [])[:3], 1):
                    output.append(f"{i}. {job['title']} - {job['city']} (薪资: {job['salary_range']})")
                if result.get('analysis'):
                    output.append(f"\n差距分析:\n{result['analysis']}")
                return "\n".join(output)

            except Exception as e:
                logger.error(f"技能差距分析失败: {e}")
                return f"分析出错，请稍后重试。"

        tools: List[BaseTool] = [search_jobs, recommend_jobs, analyze_skill_gap]

        # Neo4j 图谱详情查询工具
        if self.neo4j_available:
            neo4j = self.neo4j

            @tool
            def query_skill_graph(skill_name: str) -> str:
                """查询单个技能的图谱信息：热度、需求量、平均薪资、相关技能。
                Args:
                    skill_name: 技能名称，例如 "Python"、"Vue"、"Docker"
                Returns:
                    技能详细统计信息
                """
                try:
                    logger.info(f"[工具调用] 技能图谱查询: {skill_name}")
                    result = neo4j.execute_query("""
                        MATCH (s:Skill {name: $skill_name})
                        OPTIONAL MATCH (s)-[r:RELATED_TO]-(related:Skill)
                        OPTIONAL MATCH (j:Job)-[:REQUIRES]->(s)
                        WITH s,
                             collect(DISTINCT {name: related.name, correlation: r.correlation})[0..5] AS related_skills,
                             count(DISTINCT j) AS job_count
                        RETURN s.name AS skill_name, s.hot_score AS hot_score,
                               s.category AS category, s.demand_count AS demand_count,
                               s.avg_salary_min AS avg_salary_min,
                               s.avg_salary_max AS avg_salary_max,
                               related_skills, job_count
                    """, {"skill_name": skill_name})

                    if not result:
                        return f"未找到技能「{skill_name}」，请确认名称（区分大小写）。"
                    data = result[0]
                    avg_min = data.get('avg_salary_min') or 0
                    avg_max = data.get('avg_salary_max') or 0
                    output = [
                        f"**{data['skill_name']}** （{data.get('category') or '未知分类'}）",
                        f"热度：{data.get('hot_score') or 0}/100 | 需求量：{data.get('demand_count') or 0} 个岗位",
                        f"平均薪资：{avg_min:.0f}–{avg_max:.0f}K",
                    ]
                    if data.get('related_skills'):
                        rel = [r['name'] for r in data['related_skills'] if r and r.get('name')]
                        if rel:
                            output.append(f"相关技能：{', '.join(rel)}")
                    return "\n".join(output)
                except Exception as e:
                    logger.error(f"技能图谱查询失败: {e}")
                    return f"查询失败：{str(e)}"

            tools.append(query_skill_graph)

        return tools


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 80)
    print("测试Agent工具")
    print("=" * 80)

    tools_manager = AgentTools()
    tools = tools_manager.get_tools()

    print(f"\n可用工具数: {len(tools)}")
    for t in tools:
        print(f"\n工具: {t.name}")
        print(f"描述: {t.description.strip()[:100]}...")

    print("\n" + "=" * 80)
    print("✅ 工具初始化成功！")
    print("=" * 80)
