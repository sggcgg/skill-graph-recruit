"""
RAG服务
结合向量检索和LLM，提供智能问答和分析
"""
import logging
from typing import List, Dict, Optional
from pathlib import Path
import sys

# 添加项目根目录到path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.rag.vector_db import VectorDB

logger = logging.getLogger(__name__)


class RAGService:
    """
    RAG检索增强生成服务
    
    功能:
    1. 语义搜索 + LLM总结
    2. 技能差距分析
    3. 岗位推荐
    4. 学习路径规划
    """
    
    def __init__(self):
        """初始化RAG服务"""
        logger.info("初始化RAG服务...")

        # 初始化向量数据库
        self.vector_db = VectorDB()

        # 延迟导入，避免与 agent 模块的循环依赖
        from src.agent.qwen_api_client import QwenAPIClient

        # LLM 统一使用 Qwen API（无需本地模型）
        self.qwen_api = QwenAPIClient()
        if self.qwen_api.api_key:
            logger.info("✅ Qwen API 初始化成功，RAG 摘要已就绪")
        else:
            logger.warning("⚠️  未配置 DASHSCOPE_API_KEY，RAG 摘要不可用")

        logger.info("RAG服务初始化完成")
    
    def search_and_summarize(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict] = None
    ) -> Dict:
        """
        检索 + LLM总结
        
        Args:
            query: 用户查询
            top_k: 检索TOP K个结果
            filters: 过滤条件
            
        Returns:
            {
                'retrieved_jobs': [...],  # 检索到的岗位
                'summary': '...',         # LLM总结（如果可用）
                'query': '...'            # 原始查询
            }
        """
        logger.info(f"搜索查询: {query}")
        
        # 1. 向量检索
        results = self.vector_db.search(query, top_k=top_k, filters=filters)
        
        # 提取岗位信息
        retrieved_jobs = []
        if results['metadatas'] and results['metadatas'][0]:
            for i, meta in enumerate(results['metadatas'][0]):
                distance = results['distances'][0][i]
                # 1/(1+d) 将任意非负距离映射到(0,1]，兼容L2和cosine两种度量
                similarity = round(1 / (1 + max(0, distance)), 3)
                
                # 解析技能列表（逗号分隔字符串 → list）
                skills_raw = meta.get('skills', '')
                skills = [s.strip() for s in skills_raw.split(',') if s.strip()] if skills_raw else []

                job_info = {
                    'job_id': meta['job_id'],
                    'title': meta['title'],
                    'city': meta['city'],
                    'company': meta['company'],
                    'salary_range': f"{meta['salary_min']}-{meta['salary_max']}K",
                    'experience': meta.get('experience', ''),
                    'education': meta.get('education', ''),
                    'skills': skills,
                    'similarity': round(similarity, 3),
                    'document': results['documents'][0][i][:800]  # 文档片段
                }
                retrieved_jobs.append(job_info)
        
        # 2. Qwen API 生成摘要
        summary = None
        if retrieved_jobs and self.qwen_api and self.qwen_api.api_key:
            try:
                summary = self._summarize_jobs(query, retrieved_jobs)
            except Exception as e:
                logger.warning(f"摘要生成失败: {e}")
                summary = None
        
        return {
            'retrieved_jobs': retrieved_jobs,
            'summary': summary,
            'query': query,
            'count': len(retrieved_jobs)
        }
    
    def _summarize_jobs(self, query: str, jobs: List[Dict]) -> str:
        """
        LLM 总结检索结果（本地模型优先，不可用自动切换 Qwen API）

        Args:
            query: 用户查询
            jobs:  检索到的岗位列表

        Returns:
            总结文本
        """
        # 构建上下文（最多取前5个岗位）
        context_jobs = []
        for i, job in enumerate(jobs[:5]):
            skills_str = '、'.join(job.get('skills', [])[:6]) or '未知'
            context_jobs.append(
                f"{i+1}. {job['title']} — {job.get('company', '企业')}\n"
                f"   城市：{job.get('city', '未知')}  薪资：{job.get('salary_range', '面议')}"
                f"  经验：{job.get('experience', '不限')}\n"
                f"   技能要求：{skills_str}"
            )
        context = "\n\n".join(context_jobs)

        prompt = f"""用户查询：{query}

相关岗位（共 {len(jobs)} 个，展示前5个）：
{context}

请用3-4句话简洁总结：
1. 该类岗位的核心技能要求
2. 薪资行情和竞争程度
3. 给求职者的一句建议

直接输出总结内容，不要序号和标题。"""

        messages = [{"role": "user", "content": prompt}]
        return self.qwen_api.chat(messages, temperature=0.3, max_tokens=300)
    
    def skill_gap_analysis(
        self,
        user_skills: List[str],
        target_position: str,
        city: Optional[str] = None
    ) -> Dict:
        """
        技能差距分析
        
        Args:
            user_skills: 用户当前技能
            target_position: 目标岗位
            city: 城市（可选）
            
        Returns:
            {
                'analysis': '...',        # 差距分析
                'target_jobs': [...],     # 目标岗位样本
                'required_skills': [...], # 推荐学习的技能
            }
        """
        logger.info(f"技能差距分析: {user_skills} -> {target_position}")
        
        # 1. 检索目标岗位
        query = f"{target_position} 岗位需要的技能"
        filters = {"city": city} if city else None
        
        results = self.vector_db.search(query, top_k=20, filters=filters)
        
        # 提取岗位信息
        target_jobs = []
        if results['metadatas'] and results['metadatas'][0]:
            for meta in results['metadatas'][0][:5]:
                target_jobs.append({
                    'title': meta['title'],
                    'city': meta['city'],
                    'company': meta['company'],
                    'salary_range': f"{meta['salary_min']}-{meta['salary_max']}K"
                })
        
        # 2. Qwen API 分析差距
        analysis = None
        if self.qwen_api and self.qwen_api.api_key:
            try:
                user_skills_str = '、'.join(user_skills) if user_skills else '（未提供）'
                prompt = f"""请分析以下技能差距情况：

用户当前技能：{user_skills_str}
目标岗位：{target_position}

请提供：
1. 用户已具备的相关技能
2. 目标岗位通常要求但用户尚缺的技能
3. 建议的学习优先级（高/中/低）
4. 简要的学习路径建议

请用简洁、结构化的方式回答。"""
                messages = [{"role": "user", "content": prompt}]
                analysis = self.qwen_api.chat(messages, temperature=0.3, max_tokens=600)
            except Exception as e:
                logger.warning(f"技能差距分析失败: {e}")
                analysis = None
        
        return {
            'analysis': analysis,
            'target_jobs': target_jobs,
            'user_skills': user_skills,
            'target_position': target_position
        }
    
    def recommend_jobs(
        self,
        user_skills: List[str],
        top_k: int = 10,
        filters: Optional[Dict] = None
    ) -> Dict:
        """
        基于用户技能推荐岗位
        
        Args:
            user_skills: 用户技能列表
            top_k: 推荐TOP K个岗位
            filters: 过滤条件
            
        Returns:
            推荐结果
        """
        logger.info(f"岗位推荐: {user_skills}")
        
        # 构建查询
        query = f"需要以下技能的岗位: {', '.join(user_skills)}"
        
        # 检索
        return self.search_and_summarize(query, top_k=top_k, filters=filters)
    
    def find_similar_jobs(
        self,
        job_id: str,
        top_k: int = 5
    ) -> List[Dict]:
        """
        查找相似岗位
        
        Args:
            job_id: 岗位ID
            top_k: 返回TOP K个相似岗位
            
        Returns:
            相似岗位列表
        """
        # 获取原岗位信息
        try:
            original_job = self.vector_db.collection.get(ids=[job_id])
            if not original_job['documents']:
                return []
            
            # 使用原岗位的文档作为查询
            query_doc = original_job['documents'][0]
            
            # 检索
            results = self.vector_db.search(query_doc, top_k=top_k+1)
            
            # 过滤掉原岗位本身
            similar_jobs = []
            for i, meta in enumerate(results['metadatas'][0]):
                if meta['job_id'] != job_id:
                    similar_jobs.append({
                        'job_id': meta['job_id'],
                        'title': meta['title'],
                        'city': meta['city'],
                        'similarity': round(1 / (1 + max(0, results['distances'][0][i])), 3)
                    })
            
            return similar_jobs[:top_k]
            
        except Exception as e:
            logger.error(f"查找相似岗位失败: {e}")
            return []


# 测试代码
def test_rag_service():
    """测试RAG服务"""
    print("="*80)
    print("测试RAG服务")
    print("="*80)
    
    # 初始化
    print("\n【初始化RAG服务】")
    rag = RAGService()
    print("✅ 初始化成功")
    
    # 测试1: 语义搜索+总结
    print("\n【测试1: 语义搜索+总结】")
    query = "Python后端开发，熟悉Django和MySQL"
    result = rag.search_and_summarize(query, top_k=5)
    
    print(f"查询: {query}")
    print(f"找到 {result['count']} 个相关岗位:")
    for job in result['retrieved_jobs'][:3]:
        print(f"  - {job['title']} | {job['city']} | {job['salary_range']} (相似度: {job['similarity']})")
    
    if result['summary']:
        print(f"\nLLM总结:")
        print(result['summary'][:200] + "...")
    
    # 测试2: 技能差距分析
    print("\n【测试2: 技能差距分析】")
    gap_result = rag.skill_gap_analysis(
        user_skills=["Python", "Django", "MySQL"],
        target_position="高级Python后端工程师"
    )
    
    print(f"用户技能: {gap_result['user_skills']}")
    print(f"目标岗位: {gap_result['target_position']}")
    print(f"找到 {len(gap_result['target_jobs'])} 个目标岗位样本")
    
    if gap_result['analysis']:
        print(f"\n差距分析:")
        print(gap_result['analysis'][:200] + "...")
    
    # 测试3: 岗位推荐
    print("\n【测试3: 岗位推荐】")
    recommend_result = rag.recommend_jobs(
        user_skills=["Java", "Spring Boot", "MySQL"],
        top_k=5
    )
    
    print(f"推荐 {recommend_result['count']} 个岗位:")
    for job in recommend_result['retrieved_jobs'][:3]:
        print(f"  - {job['title']} | {job['city']}")
    
    print("\n" + "="*80)
    print("🎉 测试完成！")
    print("="*80)


if __name__ == "__main__":
    import logging
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    test_rag_service()
