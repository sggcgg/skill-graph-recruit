"""
FastAPI主应用
提供智能招聘分析的REST API服务
"""
import asyncio
import logging
import uuid
import time
import yaml
from fastapi import FastAPI, HTTPException, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import sys

# ===== 简易 TTL 内存缓存 =====
_api_cache: Dict[str, Tuple[Any, float]] = {}

def cache_get(key: str) -> Optional[Any]:
    """从缓存读取，过期返回 None"""
    if key in _api_cache:
        value, expire_at = _api_cache[key]
        if time.time() < expire_at:
            return value
        del _api_cache[key]
    return None

def cache_set(key: str, value: Any, ttl: int = 300) -> None:
    """写入缓存，ttl 单位秒"""
    _api_cache[key] = (value, time.time() + ttl)

# 添加项目根目录到path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.rag.rag_service import RAGService
from src.agent.job_agent import JobRecommendAgent
from src.nlp.hybrid_skill_extractor import HybridSkillExtractor
from src.auth.routes import include_auth_routes
from src.database.database import init_db

logger = logging.getLogger(__name__)

# 获取项目根目录并加载配置
project_root_for_config = Path(__file__).parent.parent.parent
config_path_abs = project_root_for_config / 'config.yaml'

with open(config_path_abs, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

api_config = config.get('api', {})

# 创建FastAPI应用
app = FastAPI(
    title=api_config.get('title', '智能招聘分析API'),
    description=api_config.get('description', '基于LLM+RAG的智能招聘信息聚合分析系统'),
    version=api_config.get('version', '2.0.0'),
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局服务实例（启动时初始化）
rag_service = None
agent = None
skill_extractor = None
neo4j_manager = None


# ===== 数据模型 =====

class SkillExtractRequest(BaseModel):
    """技能抽取请求"""
    title: str = Field(..., description="岗位标题")
    jd_text: Optional[str] = Field(None, description="职位描述文本")
    explicit_skills: List[str] = Field(default=[], description="显式标注的技能")
    use_llm: bool = Field(default=True, description="是否使用LLM增强")


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., description="查询文本")
    top_k: Optional[int] = Field(default=None, ge=1, description="返回数量，None=不限")
    city: Optional[str] = Field(None, description="城市过滤")


class SkillGapRequest(BaseModel):
    """技能差距分析请求"""
    user_skills: List[str] = Field(..., description="用户当前技能")
    target_position: str = Field(..., description="目标岗位")
    city: Optional[str] = Field(None, description="城市")


class RecommendRequest(BaseModel):
    """岗位推荐请求"""
    user_skills: List[str] = Field(..., description="用户技能")
    top_k: Optional[int] = Field(default=100, ge=1, le=500, description="推荐数量，最多500")
    city: Optional[str] = Field(None, description="城市过滤")


class AgentChatRequest(BaseModel):
    """Agent对话请求"""
    message: str = Field(..., description="用户消息")
    session_id: Optional[str] = Field(None, description="会话ID")
    mode: str = Field("auto", description="检索模式：auto/graph/rag/llm")


class GraphSearchRequest(BaseModel):
    """图谱语义搜索请求"""
    query: str = Field(..., description="查询词（支持自然语言）")
    top_k: Optional[int] = Field(default=None, ge=1, description="返回结果数量，None=全量返回")
    city: Optional[str] = Field(None, description="城市过滤")
    include_vector: bool = Field(default=False, description="是否追加向量语义补充（较慢）")


class GraphRecommendRequest(BaseModel):
    """图谱岗位推荐请求"""
    user_skills: List[str] = Field(..., description="用户技能列表")
    top_k: Optional[int] = Field(default=100, ge=1, le=500, description="推荐数量，最多500")
    city: Optional[str] = Field(None, description="城市过滤")


class GraphGapAnalysisRequest(BaseModel):
    """图谱技能差距分析请求"""
    user_skills: List[str] = Field(..., description="用户当前技能")
    target_position: str = Field(..., description="目标岗位名称")
    city: Optional[str] = Field(None, description="城市过滤")


# ===== 事件处理 =====

@app.on_event("startup")
async def startup_event():
    """启动时初始化服务"""
    global rag_service, agent, skill_extractor, neo4j_manager
    
    logger.info("="*80)
    logger.info("🚀 启动API服务...")
    logger.info("="*80)
    
    try:
        # 初始化数据库
        logger.info("初始化数据库...")
        init_db()
        logger.info("✅ 数据库初始化完成")
        
        # 初始化RAG服务
        logger.info("初始化RAG服务...")
        rag_service = RAGService()
        logger.info("✅ RAG服务初始化完成")
        
        # 初始化Agent（传入已有 rag_service，避免重复加载 VectorDB 和 m3e-base）
        try:
            logger.info("初始化Agent...")
            agent = JobRecommendAgent(rag_service=rag_service)
            logger.info("✅ Agent初始化完成")
        except Exception as e:
            logger.warning(f"Agent初始化失败: {e}")
            logger.warning("Agent功能将不可用")
            agent = None
        
        # 初始化技能抽取器
        logger.info("初始化技能抽取器...")
        skill_extractor = HybridSkillExtractor()
        logger.info("✅ 技能抽取器初始化完成")

        # 初始化Neo4j（用于图谱接口）
        try:
            logger.info("初始化Neo4j连接...")
            from src.graph_builder.neo4j_manager import Neo4jManager
            neo4j_cfg = config.get('neo4j', {})
            neo4j_manager = Neo4jManager(
                uri=neo4j_cfg['uri'],
                user=neo4j_cfg['user'],
                password=neo4j_cfg['password']
            )
            logger.info("✅ Neo4j连接初始化完成")
        except Exception as e:
            logger.warning(f"Neo4j初始化失败: {e}，图谱接口将降级为向量搜索")
            neo4j_manager = None
        
        logger.info("="*80)
        logger.info("✅ API服务启动成功！")
        logger.info(f"📖 API文档: http://localhost:{api_config.get('port', 8000)}/docs")
        logger.info("="*80)

        # 后台：确保 Neo4j 索引存在 + 预热缓存 + 启动定时刷新（均不阻塞启动）
        asyncio.create_task(_ensure_neo4j_indexes())
        asyncio.create_task(_warmup_cache())
        asyncio.create_task(_cache_refresh_loop())

    except Exception as e:
        logger.error(f"❌ 服务初始化失败: {e}")
        raise


async def _neo4j_query(cypher: str, params: dict = None):
    """把同步 Neo4j 查询放到线程池执行，避免阻塞 asyncio 事件循环"""
    if neo4j_manager is None:
        raise RuntimeError("Neo4j 服务不可用")
    return await asyncio.to_thread(neo4j_manager.execute_query, cypher, params or {})


async def _ensure_neo4j_indexes():
    """启动时异步确保关键 Neo4j 索引存在，让搜索查询能走索引而非全表扫描"""
    if not neo4j_manager:
        return
    await asyncio.sleep(5)  # 等初始化稳定
    indexes = [
        # Skill.name 点查/IN 查询索引（技能搜索核心路径）
        ("CREATE INDEX skill_name_idx IF NOT EXISTS FOR (s:Skill) ON (s.name)", "Skill.name"),
        # Skill.demand_count 范围查询索引（trend/graph 过滤）
        ("CREATE INDEX skill_demand_idx IF NOT EXISTS FOR (s:Skill) ON (s.demand_count)", "Skill.demand_count"),
        # Job.city 城市筛选索引
        ("CREATE INDEX job_city_idx IF NOT EXISTS FOR (j:Job) ON (j.city)", "Job.city"),
        # Job 全文索引：让 j.title CONTAINS 'xxx' 走全文搜索，而非全表扫描
        # 注意：全文索引语法在 Neo4j 4.x / 5.x 不同，用 try-except 兼容
    ]
    for cypher, label in indexes:
        try:
            await asyncio.to_thread(neo4j_manager.execute_query, cypher, {})
            logger.info(f"  ✅ Neo4j 索引确认: {label}")
        except Exception as e:
            logger.debug(f"  索引 {label} 跳过（可能已存在或不支持）: {e}")

    # 全文索引（Job.title），语法兼容 Neo4j 4.x 和 5.x
    fulltext_cyphs = [
        # Neo4j 5.x 语法
        "CREATE FULLTEXT INDEX job_title_fts IF NOT EXISTS FOR (j:Job) ON EACH [j.title]",
        # Neo4j 4.x 语法（无 IF NOT EXISTS）
        "CALL db.index.fulltext.createNodeIndex('job_title_fts', ['Job'], ['title'])",
    ]
    for fc in fulltext_cyphs:
        try:
            await asyncio.to_thread(neo4j_manager.execute_query, fc, {})
            logger.info("  ✅ Neo4j 全文索引 job_title_fts 确认")
            break
        except Exception:
            pass  # 忽略，换下一种语法

    logger.info("✅ Neo4j 索引检查完毕")


async def _warmup_cache():
    """
    两阶段预热：
    - 快阶（~2s）：只跑轻量查询，确保 stats/trend/graph 的核心数据在服务启动后秒级可用
    - 慢阶（后台）：co-occurrence（技能组合）等重型查询异步补全，不阻塞快阶
    """
    await asyncio.sleep(2)  # 等待服务完全就绪
    logger.info("🔥 [快阶] 开始核心缓存预热...")

    # ── stats（快，<500ms）──────────────────────────────
    try:
        if rag_service or neo4j_manager:
            stats: dict = {}
            if rag_service:
                stats['rag'] = await asyncio.to_thread(rag_service.vector_db.get_stats)
            if neo4j_manager:
                try:
                    stats['neo4j'] = await asyncio.to_thread(neo4j_manager.get_database_stats)
                except Exception:
                    stats['neo4j'] = None
            cache_set("stats", {"success": True, "data": stats}, ttl=300)
            logger.info("  ✅ /api/stats 预热完成")
    except Exception as e:
        logger.warning(f"  ⚠️ stats 预热失败: {e}")

    if not neo4j_manager:
        logger.info("🔥 Neo4j 不可用，跳过图谱预热")
        return

    # ── trend 快阶：hot_skills + category + city_distribution（均为轻量查询）──
    try:
        hot_rows, cat_rows, city_rows_fast = await asyncio.gather(
            _neo4j_query("""
                MATCH (s:Skill) WHERE s.demand_count > 0
                RETURN s.name AS skill, s.category AS category,
                       s.demand_count AS demand_count, s.hot_score AS hot_score
                ORDER BY s.demand_count DESC LIMIT 100
            """),
            _neo4j_query("""
                MATCH (s:Skill) WHERE s.demand_count > 0 AND s.category IS NOT NULL
                RETURN s.category AS category, count(s) AS skill_count,
                       sum(s.demand_count) AS total_demand
                ORDER BY total_demand DESC
            """),
            _neo4j_query("""
                MATCH (j:Job)
                WHERE j.city IS NOT NULL AND j.city <> ''
                WITH j.city AS city, count(j) AS job_count
                ORDER BY job_count DESC LIMIT 15
                RETURN city, job_count
            """),
            return_exceptions=True
        )
        # 先用空列表占位 combo/salary，慢阶完成后会覆盖
        cache_set("trend", {
            "success": True,
            "data": {
                "hot_skills":            [dict(r) for r in (hot_rows if isinstance(hot_rows, list) else [])],
                "category_distribution": [dict(r) for r in (cat_rows if isinstance(cat_rows, list) else [])],
                "skill_combos":          [],
                "high_salary_skills":    [],
                "city_distribution":     [{"city": r["city"], "job_count": r["job_count"]} for r in (city_rows_fast if isinstance(city_rows_fast, list) else [])],
            }
        }, ttl=600)
        logger.info("  ✅ /api/trend 快阶预热完成（hot_skills + category + city_distribution）")
    except Exception as e:
        logger.warning(f"  ⚠️ trend 快阶预热失败: {e}")

    # ── graph（默认参数：100节点 200边）──────────────────
    try:
        # graph 快阶：只预热节点（轻量），不跑 co-occurrence 边查询
        node_rows = await _neo4j_query("""
            MATCH (s:Skill) WHERE coalesce(s.demand_count,0) >= 5
            RETURN s.name AS skill, s.category AS category,
                   coalesce(s.demand_count,0) AS demand_count,
                   coalesce(s.hot_score,0)    AS hot_score,
                   coalesce(s.avg_salary,0)   AS avg_salary
            ORDER BY demand_count DESC LIMIT 100
        """)
        node_list = [dict(r) for r in node_rows]
        # 先用空边列表占位，慢阶完成后覆盖
        cache_set("graph:100:5:200", {
            "success": True,
            "data": {"nodes": node_list, "edges": [], "node_count": len(node_list), "edge_count": 0}
        }, ttl=600)
        logger.info("  ✅ /api/graph 快阶预热完成（节点已缓存，边将在慢阶补全）")
    except Exception as e:
        logger.warning(f"  ⚠️ graph 快阶预热失败: {e}")

    # ── graph/categories（轻量，走 category 属性）──────
    try:
        cat_rows = await _neo4j_query(
            "MATCH (s:Skill) WHERE s.category IS NOT NULL "
            "RETURN DISTINCT s.category AS category, count(s) AS cnt ORDER BY cnt DESC"
        )
        cache_set("graph_categories", {"success": True, "data": [dict(r) for r in cat_rows]}, ttl=3600)
        logger.info("  ✅ /api/graph/categories 预热完成")
    except Exception as e:
        logger.warning(f"  ⚠️ graph/categories 预热失败: {e}")

    logger.info("🔥 [快阶] 核心缓存预热完毕！启动慢阶后台补全...")
    # 慢阶：co-occurrence 等重型查询交给后台，不阻塞服务启动
    asyncio.create_task(_warmup_slow_phase())


async def _warmup_slow_phase():
    """慢阶预热：co-occurrence / 高薪技能 / 城市分布等重型查询，在快阶完成后异步补全缓存"""
    logger.info("🐢 [慢阶] 开始补全重型缓存（co-occurrence / 高薪技能 / 城市分布）...")
    if not neo4j_manager:
        return
    try:
        combo_rows, salary_rows, city_rows = await asyncio.gather(
            _neo4j_query("""
                MATCH (j:Job)-[:REQUIRES]->(s1:Skill),(j)-[:REQUIRES]->(s2:Skill)
                WHERE s1.name < s2.name AND s1.demand_count > 100 AND s2.demand_count > 100
                WITH s1.name AS skill1, s2.name AS skill2, count(j) AS co_count
                ORDER BY co_count DESC LIMIT 10
                RETURN skill1, skill2, co_count
            """),
            _neo4j_query("""
                MATCH (j:Job)-[:REQUIRES]->(s:Skill)
                WHERE j.salary_min > 0 AND j.salary_min < 200
                WITH s.name AS skill, avg(j.salary_min) AS avg_sal, count(j) AS job_count
                WHERE job_count >= 3
                RETURN skill, avg_sal, job_count ORDER BY avg_sal DESC LIMIT 100
            """),
            _neo4j_query("""
                MATCH (j:Job)
                WHERE j.city IS NOT NULL AND j.city <> ''
                WITH j.city AS city, count(j) AS job_count
                ORDER BY job_count DESC LIMIT 15
                RETURN city, job_count
            """),
            return_exceptions=True
        )
        # 读取快阶已有的 trend 缓存，补充 combo / salary / city
        existing = cache_get("trend") or {"success": True, "data": {}}
        existing["data"]["skill_combos"] = [dict(r) for r in (combo_rows if isinstance(combo_rows, list) else [])]
        existing["data"]["high_salary_skills"] = [
            {"skill": r["skill"], "avg_salary_k": round(r["avg_sal"] or 0, 1), "job_count": r["job_count"]}
            for r in (salary_rows if isinstance(salary_rows, list) else [])
        ]
        # 城市数据在快阶已写入，慢阶用新查询结果覆盖（数据相同，保持新鲜度）
        existing["data"]["city_distribution"] = [
            {"city": r["city"], "job_count": r["job_count"]}
            for r in (city_rows if isinstance(city_rows, list) else [])
        ] or existing["data"].get("city_distribution", [])
        cache_set("trend", existing, ttl=600)
        logger.info("  ✅ /api/trend 慢阶补全完成（skill_combos + high_salary_skills + city_distribution）")
    except Exception as e:
        logger.warning(f"  ⚠️ trend 慢阶补全失败: {e}")

    try:
        # graph 边查询（co-occurrence，最重的查询）
        existing_graph = cache_get("graph:100:5:200") or {"success": True, "data": {"nodes": [], "edges": []}}
        skill_names = [n["skill"] for n in existing_graph["data"].get("nodes", [])]
        if skill_names:
            edge_rows = await _neo4j_query("""
                MATCH (j:Job)-[:REQUIRES]->(s1:Skill),(j)-[:REQUIRES]->(s2:Skill)
                WHERE s1.name < s2.name AND s1.name IN $names AND s2.name IN $names
                WITH s1.name AS skill1, s2.name AS skill2, count(j) AS co_count
                WHERE co_count >= 1
                RETURN skill1, skill2, co_count ORDER BY co_count DESC LIMIT 200
            """, {"names": skill_names})
            existing_graph["data"]["edges"] = [dict(r) for r in edge_rows]
            existing_graph["data"]["edge_count"] = len(edge_rows)
            cache_set("graph:100:5:200", existing_graph, ttl=600)
            logger.info(f"  ✅ /api/graph 慢阶补全完成（{len(edge_rows)} 条边）")
    except Exception as e:
        logger.warning(f"  ⚠️ graph 慢阶补全失败: {e}")

    logger.info("🐢 [慢阶] 重型缓存补全完毕")


async def _cache_refresh_loop():
    """后台定时刷新任务：每 4.5 分钟刷新一次，让缓存始终热着（stats TTL=5min，trend/graph TTL=10min）"""
    await asyncio.sleep(270)  # 首次刷新等 4.5 min（预热已完成）
    while True:
        logger.info("♻️  后台缓存刷新开始...")
        try:
            # ── stats ──────────────────────────────────────────
            if rag_service or neo4j_manager:
                s: dict = {}
                if rag_service:
                    s['rag'] = await asyncio.to_thread(rag_service.vector_db.get_stats)
                if neo4j_manager:
                    try:
                        s['neo4j'] = await asyncio.to_thread(neo4j_manager.get_database_stats)
                    except Exception:
                        s['neo4j'] = None
                cache_set("stats", {"success": True, "data": s}, ttl=300)
        except Exception as e:
            logger.warning(f"  ⚠️ stats 刷新失败: {e}")

        if neo4j_manager:
            # ── trend（并发 4 子查询）──────────────────────────
            try:
                hot_r, cat_r, combo_r, sal_r = await asyncio.gather(
                    _neo4j_query("MATCH (s:Skill) WHERE s.demand_count > 0 RETURN s.name AS skill, s.category AS category, s.demand_count AS demand_count, s.hot_score AS hot_score ORDER BY s.demand_count DESC LIMIT 100"),
                    _neo4j_query("MATCH (s:Skill) WHERE s.demand_count > 0 AND s.category IS NOT NULL RETURN s.category AS category, count(s) AS skill_count, sum(s.demand_count) AS total_demand ORDER BY total_demand DESC"),
                    _neo4j_query("MATCH (j:Job)-[:REQUIRES]->(s1:Skill),(j)-[:REQUIRES]->(s2:Skill) WHERE s1.name < s2.name AND s1.demand_count > 100 AND s2.demand_count > 100 WITH s1.name AS skill1, s2.name AS skill2, count(j) AS co_count ORDER BY co_count DESC LIMIT 10 RETURN skill1, skill2, co_count"),
                    _neo4j_query("MATCH (j:Job)-[:REQUIRES]->(s:Skill) WHERE j.salary_min > 0 AND j.salary_min < 200 WITH s.name AS skill, avg(j.salary_min) AS avg_sal, count(j) AS job_count WHERE job_count >= 3 RETURN skill, avg_sal, job_count ORDER BY avg_sal DESC LIMIT 100"),
                    return_exceptions=True
                )
                cache_set("trend", {"success": True, "data": {
                    "hot_skills":            [dict(r) for r in (hot_r   if isinstance(hot_r,   list) else [])],
                    "category_distribution": [dict(r) for r in (cat_r   if isinstance(cat_r,   list) else [])],
                    "skill_combos":          [dict(r) for r in (combo_r if isinstance(combo_r, list) else [])],
                    "high_salary_skills":    [{"skill": r["skill"], "avg_salary_k": round(r["avg_sal"] or 0, 1), "job_count": r["job_count"]} for r in (sal_r if isinstance(sal_r, list) else [])],
                }}, ttl=600)
            except Exception as e:
                logger.warning(f"  ⚠️ trend 刷新失败: {e}")

            # ── graph（默认参数并发）──────────────────────────
            try:
                n_rows, e_rows = await asyncio.gather(
                    _neo4j_query("MATCH (s:Skill) WHERE coalesce(s.demand_count,0) >= 5 RETURN s.name AS skill, s.category AS category, coalesce(s.demand_count,0) AS demand_count, coalesce(s.hot_score,0) AS hot_score, coalesce(s.avg_salary,0) AS avg_salary ORDER BY demand_count DESC LIMIT 100"),
                    _neo4j_query("MATCH (j:Job)-[:REQUIRES]->(s1:Skill),(j)-[:REQUIRES]->(s2:Skill) WHERE s1.name < s2.name AND coalesce(s1.demand_count,0) >= 5 AND coalesce(s2.demand_count,0) >= 5 WITH s1.name AS skill1, s2.name AS skill2, count(j) AS co_count WHERE co_count >= 1 RETURN skill1, skill2, co_count ORDER BY co_count DESC LIMIT 200"),
                    return_exceptions=True
                )
                nl = [dict(r) for r in (n_rows if isinstance(n_rows, list) else [])]
                el = [dict(r) for r in (e_rows if isinstance(e_rows, list) else [])]
                cache_set("graph:100:5:200", {"success": True, "data": {"nodes": nl, "edges": el, "node_count": len(nl), "edge_count": len(el)}}, ttl=600)
            except Exception as e:
                logger.warning(f"  ⚠️ graph 刷新失败: {e}")

        logger.info("♻️  缓存刷新完成")
        await asyncio.sleep(270)  # 每 4.5 分钟刷新一次


# ===== 路由注册 =====

# 注册认证相关路由
include_auth_routes(app)


@app.on_event("shutdown")
async def shutdown_event():
    """关闭时清理资源"""
    logger.info("关闭API服务...")
    if agent is not None:
        agent.close()
    if neo4j_manager is not None:
        neo4j_manager.close()


# ===== API端点 =====

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "智能招聘分析API v2.0",
        "status": "running",
        "features": [
            "RAG语义搜索",
            "技能差距分析",
            "岗位推荐",
            "Agent对话",
            "混合技能抽取"
        ],
        "docs": "/docs"
    }


@app.get("/api/health/quick")
async def health_quick():
    """轻量健康检查 —— 仅返回服务初始化状态，<10ms，供监控看板使用"""
    return {
        "status": "ok",
        "ts": time.time(),
        "services": {
            "rag":    rag_service is not None,
            "agent":  agent is not None,
            "neo4j":  neo4j_manager is not None,
            "search": skill_extractor is not None,
        },
        "cache_size": len(_api_cache),
    }


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "services": {
            "rag": rag_service is not None,
            "agent": agent is not None,
            "skill_extractor": skill_extractor is not None,
            "neo4j": neo4j_manager is not None,
        }
    }


@app.post("/api/skill/extract")
async def extract_skills(request: SkillExtractRequest):
    """
    技能抽取（混合方法）
    
    使用规则+LLM混合方法从岗位信息中抽取技能
    """
    if not skill_extractor:
        raise HTTPException(status_code=503, detail="技能抽取服务不可用")
    
    try:
        # 构建岗位数据
        job_data = {
            'title': request.title,
            'skills': request.explicit_skills,
            'jd_text': request.jd_text
        }
        
        # 抽取技能
        result = skill_extractor.extract(job_data, use_llm=request.use_llm)
        
        # 简化返回结果
        return {
            "success": True,
            "data": {
                "skills": [s['name'] for s in result['merged_skills']],
                "detailed": result['merged_skills'],
                "stats": result['stats'],
                "method": result['method']
            }
        }
    except Exception as e:
        logger.error(f"技能抽取失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rag/search")
async def rag_search(request: SearchRequest):
    """
    RAG语义搜索

    使用向量检索+LLM总结的方式搜索相关岗位。
    若 Neo4j 可用，自动回填各岗位的完整技能列表（无需重建向量库）。
    结果缓存 2 分钟，同一关键词的重复请求（包括健康检查）直接命中缓存。
    """
    if not rag_service:
        raise HTTPException(status_code=503, detail="RAG服务不可用")

    # 缓存：同一 (query, city, top_k) 组合 2 分钟内不重复跑向量推断
    rag_cache_key = f"rag:{request.query}:{request.city}:{request.top_k}"
    cached = cache_get(rag_cache_key)
    if cached:
        return cached

    try:
        filters = {"city": request.city} if request.city else None

        # search_and_summarize 是同步阻塞（ChromaDB + 可能调 LLM），放入线程池
        result = await asyncio.to_thread(
            rag_service.search_and_summarize,
            request.query,
            request.top_k,
            filters,
        )

        # 用 Neo4j 批量回填技能（向量库元数据不一定有 skills 字段，Neo4j 是权威来源）
        jobs = result.get("retrieved_jobs", [])
        if jobs and neo4j_manager:
            try:
                job_ids = [j["job_id"] for j in jobs if j.get("job_id")]
                if job_ids:
                    cypher = """
                    MATCH (j:Job)-[:REQUIRES]->(s:Skill)
                    WHERE j.job_id IN $job_ids
                    RETURN j.job_id AS job_id, collect(s.name) AS skills
                    """
                    rows = await _neo4j_query(cypher, {"job_ids": job_ids})
                    skills_map = {r["job_id"]: r["skills"] for r in rows}
                    for job in jobs:
                        neo4j_skills = skills_map.get(job["job_id"])
                        if neo4j_skills:
                            job["skills"] = neo4j_skills
            except Exception as e:
                logger.warning(f"Neo4j 技能回填失败（不影响搜索结果）: {e}")

        final = {"success": True, "data": result}
        cache_set(rag_cache_key, final, ttl=120)  # 缓存 2 分钟
        return final
    except Exception as e:
        logger.error(f"RAG搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/skill/gap-analysis")
async def skill_gap_analysis(request: SkillGapRequest):
    """
    技能差距分析
    
    分析用户技能与目标岗位的差距，提供学习建议
    """
    if not rag_service:
        raise HTTPException(status_code=503, detail="RAG服务不可用")
    
    try:
        result = rag_service.skill_gap_analysis(
            user_skills=request.user_skills,
            target_position=request.target_position,
            city=request.city
        )
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"技能差距分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/job/recommend")
async def recommend_jobs(request: RecommendRequest):
    """
    岗位推荐
    
    基于用户技能推荐合适的岗位
    """
    if not rag_service:
        raise HTTPException(status_code=503, detail="RAG服务不可用")
    
    try:
        # 构建过滤条件
        filters = {"city": request.city} if request.city else None
        
        result = rag_service.recommend_jobs(
            user_skills=request.user_skills,
            top_k=request.top_k,
            filters=filters
        )
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"岗位推荐失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agent/chat")
async def agent_chat(request: AgentChatRequest):
    """
    Agent对话（非流式，兼容旧客户端）

    与智能Agent进行多轮对话，返回完整响应。
    注意：使用 run_in_executor 避免同步调用阻塞 asyncio 事件循环。
    """
    # 健康检查专用 ping 快速路径，<5ms 返回，不消耗 LLM 调用
    if request.message.strip().lower() in ("ping", "__ping__", "health"):
        return {
            "success": True,
            "data": {
                "response": "pong",
                "session_id": request.session_id or "ping",
                "agent_ready": agent is not None,
            },
        }

    if not agent:
        raise HTTPException(status_code=503, detail="Agent服务不可用")

    try:
        session_id = request.session_id or str(uuid.uuid4())
        # agent.chat() 是同步阻塞调用，必须放入线程池，否则会卡住整个事件循环
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, agent.chat, request.message, session_id
        )
        return {
            "success": True,
            "data": {
                "response": response,
                "session_id": session_id
            }
        }
    except Exception as e:
        logger.error(f"Agent对话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agent/chat/stream")
async def agent_chat_stream(request: AgentChatRequest):
    """
    Agent流式对话（SSE，推荐使用）

    通过 Server-Sent Events 逐 token 推送响应，用户可立即看到内容生成过程。

    事件格式：
    - data: <token>      —— 普通文本 token
    - event: status      —— 工具调用状态提示（如"正在检索岗位..."）
    - data: [DONE]       —— 流结束标志
    - event: error       —— 出错时的错误信息
    """
    if not agent:
        raise HTTPException(status_code=503, detail="Agent服务不可用")

    session_id = request.session_id or str(uuid.uuid4())

    async def event_generator():
        # 先推送 session_id，供前端记录
        yield f"event: session\ndata: {session_id}\n\n"
        async for chunk in agent.async_chat_stream(request.message, session_id, mode=request.mode):
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # 禁止 Nginx 缓冲，确保实时推送
        },
    )


@app.get("/api/stats")
async def get_stats():
    """获取系统统计信息"""
    cached = cache_get("stats")
    if cached:
        return cached
    try:
        stats = {}
        if rag_service:
            stats['rag'] = await asyncio.to_thread(rag_service.vector_db.get_stats)
        try:
            stats['neo4j'] = await asyncio.to_thread(neo4j_manager.get_database_stats) if neo4j_manager else None
        except Exception:
            stats['neo4j'] = None
        result = {"success": True, "data": stats}
        cache_set("stats", result, ttl=300)
        return result
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== 图谱增强接口 =====

@app.post("/api/search")
async def graph_search(request: GraphSearchRequest):
    """
    语义化搜索（图谱增强版）

    流程：
    1. 用技能词典将查询词映射到标准技能名
    2. 通过 Neo4j 图遍历找到需要这些技能的岗位
    3. 若 Neo4j 不可用则自动降级为向量检索
    """
    if not skill_extractor and not rag_service:
        raise HTTPException(status_code=503, detail="搜索服务不可用")

    # 统一用实际生效的 limit 值作为 cache key，避免 top_k=None 和 top_k=500 命中不同缓存
    _effective_limit = min(request.top_k, 500) if request.top_k else 500
    cache_key = f"search:{request.query}:{request.city}:{_effective_limit}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    try:
        matched_skills = []

        # Step 1：技能词典映射（CPU 密集型字典扫描，放入线程池避免阻塞事件循环）
        if skill_extractor:
            def _extract():
                job_data = {'title': request.query, 'jd_text': request.query, 'skills': []}
                return skill_extractor.extract(job_data, use_llm=False)
            extract_result = await asyncio.to_thread(_extract)
            matched_skills = [s['name'] for s in extract_result.get('merged_skills', [])]

        # Step 2：Neo4j 图谱查询
        graph_jobs = []
        search_type = "skill"   # "skill" | "title"
        if neo4j_manager:
            # 结果上限：外部明确指定时遵从，否则默认 500（全库检索后取前 500 条）
            # 监控健康检查传 top_k=1，不受影响；前端不传 top_k 则取 500 条
            limit_val = min(request.top_k, 500) if request.top_k else 500

            if matched_skills:
                # 2a：技能搜索 —— 从 Skill 节点（已建索引）出发遍历 Job，效率最高
                # 第一步：利用 Skill.name 索引快速定位所有匹配岗位，按命中技能数排序
                # 第二步：仅对 top-500 结果再查一次 all_skills，避免对全库做二次扫描
                search_type = "skill"
                cypher = f"""
                MATCH (j:Job)-[:REQUIRES]->(s:Skill)
                WHERE s.name IN $skill_names
                  AND ($city IS NULL OR j.city = $city)
                WITH j,
                     collect(DISTINCT s.name) AS matched_skills,
                     count(DISTINCT s)        AS match_count
                ORDER BY match_count DESC, j.salary_max DESC
                LIMIT {limit_val}
                MATCH (j)-[:REQUIRES]->(all_s:Skill)
                WITH j, matched_skills, match_count,
                     count(DISTINCT all_s) AS total_skills
                OPTIONAL MATCH (j)-[:POSTED_BY]->(c:Company)
                RETURN j.job_id          AS job_id,
                       j.title           AS title,
                       j.city            AS city,
                       coalesce(c.name, '') AS company,
                       coalesce(j.salary_min, 0) AS salary_min,
                       coalesce(j.salary_max, 0) AS salary_max,
                       coalesce(j.experience,    '') AS experience,
                       coalesce(j.education,     '') AS education,
                       coalesce(j.jd_text,       '') AS jd_text,
                       coalesce(j.publish_date,  '') AS publish_date,
                       matched_skills,
                       match_count,
                       total_skills
                """
                rows = await _neo4j_query(cypher, {
                    "skill_names": matched_skills,
                    "city": request.city,
                })
            else:
                # 2b：职位名称关键词搜索（无技能词时）
                # 若 Neo4j 已建全文索引 job_title_fts，此查询可在毫秒级完成
                search_type = "title"
                raw_keywords = [w for w in request.query.replace('，', ' ').replace(',', ' ').split() if len(w) >= 2]
                if not raw_keywords:
                    raw_keywords = [request.query]
                # 去掉单引号防止 Cypher 注入；限制最多 5 个关键词
                keywords = [kw.replace("'", "") for kw in raw_keywords[:5]]
                # 参数化写法：$kw0, $kw1... 替代字符串拼接，彻底消除注入风险
                kw_params = {f"kw{i}": kw for i, kw in enumerate(keywords)}
                where_parts = " OR ".join([f"j.title CONTAINS $kw{i}" for i in range(len(keywords))])
                score_parts = " + ".join([f"(CASE WHEN j.title CONTAINS $kw{i} THEN 1 ELSE 0 END)" for i in range(len(keywords))])
                cypher = f"""
                MATCH (j:Job)
                WHERE ({where_parts})
                  AND ($city IS NULL OR j.city = $city)
                WITH j, ({score_parts}) AS kw_score
                ORDER BY kw_score DESC, j.salary_max DESC
                LIMIT $limit_val
                OPTIONAL MATCH (j)-[:REQUIRES]->(s:Skill)
                WITH j, kw_score, collect(DISTINCT s.name) AS all_skills
                OPTIONAL MATCH (j)-[:POSTED_BY]->(c:Company)
                RETURN j.job_id          AS job_id,
                       j.title           AS title,
                       j.city            AS city,
                       coalesce(c.name, '') AS company,
                       coalesce(j.salary_min, 0) AS salary_min,
                       coalesce(j.salary_max, 0) AS salary_max,
                       coalesce(j.experience,    '') AS experience,
                       coalesce(j.education,     '') AS education,
                       coalesce(j.jd_text,       '') AS jd_text,
                       coalesce(j.publish_date,  '') AS publish_date,
                       all_skills        AS matched_skills,
                       kw_score          AS match_count,
                       size(all_skills)  AS total_skills
                """
                rows = await _neo4j_query(cypher, {"city": request.city, "limit_val": limit_val, **kw_params})

            for r in rows:
                graph_jobs.append({
                    "job_id":        r["job_id"],
                    "title":         r["title"],
                    "city":          r["city"],
                    "company":       r["company"],
                    "salary_range":  f"{r['salary_min'] or 0}-{r['salary_max'] or 0}K",
                    "experience":    r.get("experience", ""),
                    "education":     r.get("education", ""),
                    "jd_text":        r.get("jd_text", ""),
                    "publish_date":   r.get("publish_date", ""),
                    "matched_skills": r["matched_skills"],
                    "match_count":   r["match_count"],
                    "total_skills":  r["total_skills"],
                    "search_type":   search_type,
                    "source":        "graph",
                })

        # Step 3：向量语义补充（可选，默认关闭以加速响应）
        vector_jobs = []
        need_vector = request.include_vector or (not graph_jobs and rag_service)
        if need_vector and rag_service:
            filters = {"city": request.city} if request.city else None
            v_result = rag_service.search_and_summarize(
                query=request.query, top_k=request.top_k, filters=filters
            )
            for j in v_result.get("retrieved_jobs", []):
                j["source"] = "vector"
                vector_jobs.append(j)

        # 合并去重：图谱结果优先，向量结果补足
        seen_ids = {j["job_id"] for j in graph_jobs}
        merged = graph_jobs[:]
        for j in vector_jobs:
            if j["job_id"] not in seen_ids:
                merged.append(j)
                seen_ids.add(j["job_id"])

        # 最终截断：外部明确传了 top_k 则遵从，否则统一上限 500
        final_limit = min(request.top_k, 500) if request.top_k else 500
        merged = merged[:final_limit]

        result = {
            "success": True,
            "data": {
                "jobs": merged,
                "count": len(merged),
                "query": request.query,
                "matched_skills": matched_skills,
                "graph_hits": len(graph_jobs),
                "vector_hits": len(vector_jobs),
            },
        }
        cache_set(cache_key, result, ttl=180)   # 搜索结果缓存 3 分钟
        return result
    except Exception as e:
        logger.error(f"图谱搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/recommend")
async def graph_recommend(request: GraphRecommendRequest):
    """
    智能岗位推荐（Cypher 精准匹配 + 语义扩展）

    流程：
    1. Cypher 精准匹配：查找需要用户技能最多的岗位
    2. 图谱扩展：通过 RELATED_TO 关系找关联技能，扩大推荐范围
    3. 降级：Neo4j 不可用时退回向量推荐
    """
    if not rag_service and not neo4j_manager:
        raise HTTPException(status_code=503, detail="推荐服务不可用")

    skills_key = ",".join(sorted(request.user_skills or []))
    cache_key = f"recommend:{skills_key}:{request.city}:{request.top_k}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    try:
        precise_jobs = []
        expanded_jobs = []
        related_skills: List[str] = []

        if neo4j_manager and request.user_skills:
            rec_limit = min(request.top_k, 500) if request.top_k else 500

            # Step 1 & 2：精准匹配 + 关联技能扩展 并发执行
            precise_cypher = """
            MATCH (j:Job)-[:REQUIRES]->(s:Skill)
            WHERE s.name IN $user_skills
              AND ($city IS NULL OR j.city = $city)
            WITH j,
                 collect(DISTINCT s.name) AS matched_skills,
                 count(DISTINCT s)        AS match_count
            ORDER BY match_count DESC
            LIMIT $top_k
            MATCH (j)-[:REQUIRES]->(all_s:Skill)
            WITH j, matched_skills, match_count,
                 count(DISTINCT all_s) AS total_skills
            OPTIONAL MATCH (j)-[:POSTED_BY]->(c:Company)
            RETURN j.job_id     AS job_id,
                   j.title      AS title,
                   j.city       AS city,
                   coalesce(c.name, '') AS company,
                   j.salary_min AS salary_min,
                   j.salary_max AS salary_max,
                   matched_skills,
                   match_count,
                   total_skills
            """
            expand_cypher = """
            MATCH (us:Skill)-[:RELATED_TO]-(rs:Skill)
            WHERE us.name IN $user_skills
              AND NOT rs.name IN $user_skills
            RETURN DISTINCT rs.name AS related_skill
            LIMIT 10
            """
            precise_rows, rel_rows = await asyncio.gather(
                _neo4j_query(precise_cypher, {
                    "user_skills": request.user_skills,
                    "city": request.city,
                    "top_k": rec_limit,
                }),
                _neo4j_query(expand_cypher, {"user_skills": request.user_skills}),
                return_exceptions=True,
            )
            if isinstance(precise_rows, Exception):
                logger.warning(f"精准推荐查询失败: {precise_rows}")
                precise_rows = []
            if isinstance(rel_rows, Exception):
                logger.warning(f"关联技能查询失败: {rel_rows}")
                rel_rows = []

            for r in precise_rows:
                precise_jobs.append({
                    "job_id": r["job_id"],
                    "title": r["title"],
                    "city": r["city"],
                    "company": r["company"],
                    "salary_range": f"{r['salary_min'] or 0}-{r['salary_max'] or 0}K",
                    "matched_skills": r["matched_skills"],
                    "match_count": r["match_count"],
                    "total_skills": r["total_skills"],
                    "match_type": "precise",
                })

            related_skills = [r["related_skill"] for r in rel_rows]

            if related_skills:
                cypher_expanded = """
                MATCH (j:Job)-[:REQUIRES]->(s:Skill)
                WHERE s.name IN $related_skills
                  AND ($city IS NULL OR j.city = $city)
                WITH j,
                     collect(DISTINCT s.name) AS expansion_skills,
                     count(DISTINCT s)        AS exp_count
                ORDER BY exp_count DESC
                LIMIT $top_k
                OPTIONAL MATCH (j)-[:POSTED_BY]->(c:Company)
                RETURN j.job_id     AS job_id,
                       j.title      AS title,
                       j.city       AS city,
                       coalesce(c.name, '') AS company,
                       j.salary_min AS salary_min,
                       j.salary_max AS salary_max,
                       expansion_skills,
                       exp_count
                """
                exp_rows = await _neo4j_query(cypher_expanded, {
                    "related_skills": related_skills,
                    "city": request.city,
                    "top_k": rec_limit,
                })
                for r in exp_rows:
                    expanded_jobs.append({
                        "job_id": r["job_id"],
                        "title": r["title"],
                        "city": r["city"],
                        "company": r["company"],
                        "salary_range": f"{r['salary_min'] or 0}-{r['salary_max'] or 0}K",
                        "matched_skills": r["expansion_skills"],
                        "match_count": r["exp_count"],
                        "match_type": "expanded",
                    })

        # 向量兜底
        vector_jobs = []
        if rag_service and not precise_jobs:
            filters = {"city": request.city} if request.city else None
            v_result = rag_service.recommend_jobs(
                user_skills=request.user_skills,
                top_k=request.top_k,
                filters=filters,
            )
            for j in v_result.get("retrieved_jobs", []):
                j["match_type"] = "vector"
                vector_jobs.append(j)

        # 合并：精准 > 扩展 > 向量
        seen_ids: set = set()
        merged: List[Dict] = []
        for j in precise_jobs + expanded_jobs + vector_jobs:
            if j["job_id"] not in seen_ids:
                merged.append(j)
                seen_ids.add(j["job_id"])

        # top_k 为 None 时 list[:None] 等于 list[:]（全量），不会截断
        merge_limit = min(request.top_k, 500) if request.top_k else 500
        merged = merged[:merge_limit]

        result = {
            "success": True,
            "data": {
                "jobs": merged,
                "count": len(merged),
                "precise_count": len(precise_jobs),
                "expanded_count": len(expanded_jobs),
                "related_skills": related_skills,
            },
        }
        cache_set(cache_key, result, ttl=180)   # 推荐结果缓存 3 分钟
        return result
    except Exception as e:
        logger.error(f"图谱推荐失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/gap-analysis")
async def graph_gap_analysis(request: GraphGapAnalysisRequest):
    """
    技能差距分析（图谱版）

    流程：
    1. 从 Neo4j 中查找目标岗位所需的高频技能
    2. 与用户技能对比，计算匹配率和缺失技能
    3. 通过图谱查询缺失技能的前置/关联技能，生成学习路径
    """
    if not neo4j_manager and not rag_service:
        raise HTTPException(status_code=503, detail="分析服务不可用")

    user_key = ",".join(sorted(request.user_skills or []))
    cache_key = f"gap:{request.target_position}:{user_key}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    try:
        required_skills: List[str] = []
        sample_jobs: List[Dict] = []

        if neo4j_manager:
            # Step 1 & 2：高频技能 + 样本岗位 并发查询（独立查询，无依赖关系）
            req_params = {"position": request.target_position, "city": request.city}
            skill_rows, job_rows = await asyncio.gather(
                _neo4j_query("""
                    MATCH (j:Job)-[:REQUIRES]->(s:Skill)
                    WHERE j.title CONTAINS $position
                      AND ($city IS NULL OR j.city = $city)
                    WITH s.name AS skill_name, count(j) AS freq
                    ORDER BY freq DESC LIMIT 20
                    RETURN skill_name, freq
                """, req_params),
                _neo4j_query("""
                    MATCH (j:Job)
                    WHERE j.title CONTAINS $position
                      AND ($city IS NULL OR j.city = $city)
                    OPTIONAL MATCH (j)-[:POSTED_BY]->(c:Company)
                    RETURN j.job_id AS job_id, j.title AS title, j.city AS city,
                           coalesce(c.name, '') AS company,
                           j.salary_min AS salary_min, j.salary_max AS salary_max
                    LIMIT 5
                """, req_params),
                return_exceptions=True,
            )
            if isinstance(skill_rows, Exception):
                logger.warning(f"gap-analysis 技能查询失败: {skill_rows}")
                skill_rows = []
            if isinstance(job_rows, Exception):
                logger.warning(f"gap-analysis 样本岗位查询失败: {job_rows}")
                job_rows = []
            required_skills = [r["skill_name"] for r in skill_rows]
            sample_jobs = [{
                "title": r["title"],
                "city": r["city"],
                "company": r["company"],
                "salary_range": f"{r['salary_min'] or 0}-{r['salary_max'] or 0}K",
            } for r in job_rows]

        # 若图谱无数据，用向量搜索兜底
        if not required_skills:
            if rag_service:
                v_result = rag_service.skill_gap_analysis(
                    user_skills=request.user_skills,
                    target_position=request.target_position,
                    city=request.city,
                )
                return {"success": True, "data": v_result}
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"图谱中未找到与「{request.target_position}」相关的岗位，请尝试更通用的岗位名称",
                )

        # Step 2：计算匹配 / 缺失技能
        user_set = set(request.user_skills)
        required_set = set(required_skills)
        matched_skills = sorted(user_set & required_set)
        missing_skills = sorted(required_set - user_set)
        match_rate = round(len(matched_skills) / len(required_set), 3) if required_set else 0.0

        # Step 3：为缺失技能查找学习路径（前置 / 关联技能）
        learning_path: List[Dict] = []
        if neo4j_manager and missing_skills:
            top_missing = missing_skills[:10]
            # OPTIONAL MATCH 确保没有 RELATED_TO 的技能也会出现在结果中
            cypher_path = """
            UNWIND $missing AS miss_name
            MATCH (ms:Skill {name: miss_name})
            OPTIONAL MATCH (ms)-[:RELATED_TO]-(pre:Skill)
            RETURN miss_name,
                   collect(DISTINCT pre.name) AS prerequisites
            """
            path_rows = await _neo4j_query(cypher_path, {"missing": top_missing})
            covered = set()
            for r in path_rows:
                prereqs = [p for p in r.get("prerequisites", []) if p]
                owned = [p for p in prereqs if p in user_set]
                needed = [p for p in prereqs if p not in user_set]
                learning_path.append({
                    "skill": r["miss_name"],
                    "owned_prerequisites": owned,
                    "needed_prerequisites": needed,
                    "ready_to_learn": len(needed) == 0,
                })
                covered.add(r["miss_name"])
            # 补充在图谱中找不到节点的技能（直接可学习）
            for skill in top_missing:
                if skill not in covered:
                    learning_path.append({
                        "skill": skill,
                        "owned_prerequisites": [],
                        "needed_prerequisites": [],
                        "ready_to_learn": True,
                    })
            # 优先展示"可直接学习"的技能
            learning_path.sort(key=lambda x: (not x["ready_to_learn"]))

        result = {
            "success": True,
            "data": {
                "target_position": request.target_position,
                "user_skills": request.user_skills,
                "required_skills": required_skills,
                "matched_skills": matched_skills,
                "missing_skills": missing_skills,
                "match_rate": match_rate,
                "learning_path": learning_path,
                "sample_jobs": sample_jobs,
            },
        }
        cache_set(cache_key, result, ttl=300)   # 差距分析缓存 5 分钟
        return result
    except Exception as e:
        logger.error(f"图谱差距分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trend")
async def market_trend():
    """
    市场趋势分析

    返回：
    - 热门技能 TOP 20（按需求量排序）
    - 技能分类分布（编程语言 / 框架 / 工具等）
    - 技能组合强度 TOP 10（经常同时出现的技能对）
    - 高薪技能 TOP 10
    """
    if not neo4j_manager:
        raise HTTPException(status_code=503, detail="Neo4j服务不可用，趋势分析需要图谱数据")

    cached = cache_get("trend")
    if cached:
        return cached

    try:
        # 5 个子查询并发执行，时间取决于最慢的那个而非 5 个之和
        hot_rows, cat_rows, combo_rows, salary_rows, city_rows = await asyncio.gather(
            _neo4j_query("""
                MATCH (s:Skill) WHERE s.demand_count > 0
                RETURN s.name AS skill, s.category AS category,
                       s.demand_count AS demand_count, s.hot_score AS hot_score
                ORDER BY s.demand_count DESC LIMIT 100
            """),
            _neo4j_query("""
                MATCH (s:Skill) WHERE s.demand_count > 0 AND s.category IS NOT NULL
                RETURN s.category AS category, count(s) AS skill_count,
                       sum(s.demand_count) AS total_demand
                ORDER BY total_demand DESC
            """),
            _neo4j_query("""
                MATCH (j:Job)-[:REQUIRES]->(s1:Skill),(j)-[:REQUIRES]->(s2:Skill)
                WHERE s1.name < s2.name AND s1.demand_count > 100 AND s2.demand_count > 100
                WITH s1.name AS skill1, s2.name AS skill2, count(j) AS co_count
                ORDER BY co_count DESC LIMIT 10
                RETURN skill1, skill2, co_count
            """),
            _neo4j_query("""
                MATCH (j:Job)-[:REQUIRES]->(s:Skill)
                WHERE j.salary_min > 0 AND j.salary_min < 200
                WITH s.name AS skill, avg(j.salary_min) AS avg_sal, count(j) AS job_count
                WHERE job_count >= 3
                RETURN skill, avg_sal, job_count ORDER BY avg_sal DESC LIMIT 100
            """),
            _neo4j_query("""
                MATCH (j:Job)
                WHERE j.city IS NOT NULL AND j.city <> ''
                WITH j.city AS city, count(j) AS job_count
                ORDER BY job_count DESC LIMIT 15
                RETURN city, job_count
            """),
        )
        result = {
            "success": True,
            "data": {
                "hot_skills":            [dict(r) for r in hot_rows],
                "category_distribution": [dict(r) for r in cat_rows],
                "skill_combos":          [dict(r) for r in combo_rows],
                "high_salary_skills": [
                    {"skill": r["skill"], "avg_salary_k": round(r["avg_sal"] or 0, 1), "job_count": r["job_count"]}
                    for r in salary_rows
                ],
                "city_distribution": [
                    {"city": r["city"], "job_count": r["job_count"]}
                    for r in city_rows
                ],
            },
        }
        cache_set("trend", result, ttl=600)
        return result
    except Exception as e:
        logger.error(f"趋势分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/graph/categories")
async def get_skill_categories():
    """查询 Neo4j 中所有 Skill 节点实际存在的 category 值"""
    if not neo4j_manager:
        raise HTTPException(status_code=503, detail="Neo4j服务不可用")
    cached = cache_get("graph_categories")
    if cached:
        return cached
    rows = await _neo4j_query(
        "MATCH (s:Skill) WHERE s.category IS NOT NULL "
        "RETURN DISTINCT s.category AS category, count(s) AS cnt "
        "ORDER BY cnt DESC"
    )
    result = {"success": True, "data": [dict(r) for r in rows]}
    cache_set("graph_categories", result, ttl=3600)  # 分类几乎不变，缓存 1 小时
    return result


@app.get("/api/graph")
async def get_skill_graph(
    limit: int = Query(default=100, ge=1, le=500, description="返回技能节点数量上限"),
    min_demand: int = Query(default=5, ge=0, description="最低岗位需求数过滤"),
    edge_limit: int = Query(default=200, ge=0, le=5000, description="返回关系边数量上限，0表示不返回边"),
):
    """
    技能知识图谱可视化专用接口

    返回：
    - 技能节点列表（按需求量排序，可通过 limit 控制数量）
    - 技能共现关系边列表（两个技能同时出现在一个岗位中）
    """
    if not neo4j_manager:
        raise HTTPException(status_code=503, detail="Neo4j服务不可用")

    cache_key = f"graph:{limit}:{min_demand}:{edge_limit}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    try:
        # 节点与边查询并发：边查询直接用 demand_count 过滤，无需先等节点结果
        node_rows, edge_rows = await asyncio.gather(
            _neo4j_query("""
                MATCH (s:Skill)
                WHERE coalesce(s.demand_count, 0) >= $min_demand
                RETURN s.name AS skill, s.category AS category,
                       coalesce(s.demand_count, 0) AS demand_count,
                       coalesce(s.hot_score, 0)    AS hot_score,
                       coalesce(s.avg_salary, 0)   AS avg_salary
                ORDER BY demand_count DESC LIMIT $limit
            """, {"min_demand": min_demand, "limit": limit}),
            _neo4j_query("""
                MATCH (j:Job)-[:REQUIRES]->(s1:Skill),(j)-[:REQUIRES]->(s2:Skill)
                WHERE s1.name < s2.name
                  AND coalesce(s1.demand_count, 0) >= $min_demand
                  AND coalesce(s2.demand_count, 0) >= $min_demand
                WITH s1.name AS skill1, s2.name AS skill2, count(j) AS co_count
                WHERE co_count >= 1
                RETURN skill1, skill2, co_count
                ORDER BY co_count DESC LIMIT $edge_limit
            """, {"min_demand": min_demand, "edge_limit": edge_limit}),
            return_exceptions=True,
        )
        if isinstance(node_rows, Exception):
            raise node_rows  # 节点查询失败直接上报
        if isinstance(edge_rows, Exception):
            logger.warning(f"图谱边查询失败（节点仍返回）: {edge_rows}")
            edge_rows = []
        node_list = [dict(r) for r in node_rows]
        edge_list = [dict(r) for r in edge_rows]

        result = {
            "success": True,
            "data": {
                "nodes": node_list,
                "edges": edge_list,
                "node_count": len(node_list),
                "edge_count": len(edge_list),
            },
        }
        cache_set(cache_key, result, ttl=600)
        return result
    except Exception as e:
        logger.error(f"技能图谱查询失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== 启动脚本 =====

if __name__ == "__main__":
    import uvicorn
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 启动服务
    uvicorn.run(
        "main:app",
        host=api_config.get('host', '0.0.0.0'),
        port=api_config.get('port', 8000),
        reload=api_config.get('debug', True),
        log_level="info"
    )
