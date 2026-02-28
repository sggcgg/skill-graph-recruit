"""
向量数据库管理
基于ChromaDB实现岗位JD的向量化存储和检索
"""
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
import yaml
import logging
from pathlib import Path
from tqdm import tqdm

logger = logging.getLogger(__name__)


class VectorDB:
    """ChromaDB向量数据库封装"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        初始化向量数据库
        
        Args:
            config_path: 配置文件路径（相对于项目根目录）
        """
        # 获取项目根目录
        project_root = Path(__file__).parent.parent.parent
        
        # 加载配置（使用绝对路径）
        config_file = project_root / config_path
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        self.vector_config = config['vector_db']
        self.embedding_config = config['embedding']
        
        # 初始化ChromaDB（使用绝对路径）
        persist_dir = self.vector_config['persist_directory']
        persist_dir_abs = project_root / persist_dir
        persist_dir_abs.mkdir(parents=True, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=str(persist_dir_abs))
        
        # 加载Embedding模型
        logger.info(f"加载Embedding模型: {self.embedding_config['model_name']}")
        
        # 优先使用本地模型（使用绝对路径）
        model_path = self.embedding_config.get('model_path')
        if model_path:
            model_path_abs = project_root / model_path
            if model_path_abs.exists():
                logger.info(f"从本地加载模型: {model_path_abs}")
                self.model = SentenceTransformer(str(model_path_abs))
            else:
                logger.warning(f"本地模型不存在: {model_path_abs}")
                logger.info(f"从HuggingFace下载模型: {self.embedding_config['model_name']}")
                self.model = SentenceTransformer(self.embedding_config['model_name'])
        else:
            logger.info(f"从HuggingFace下载模型: {self.embedding_config['model_name']}")
            self.model = SentenceTransformer(self.embedding_config['model_name'])
        
        # 创建或获取collection（使用cosine距离，相似度范围0~1，更直观）
        collection_name = self.vector_config['collection_name']
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={
                "description": "招聘岗位JD向量",
                "hnsw:space": "cosine"   # cosine距离：1-similarity，值域[0,2]，对应similarity[-1,1]
            }
        )
        
        logger.info(f"向量数据库初始化完成")
        logger.info(f"  Collection: {collection_name}")
        logger.info(f"  存储路径: {persist_dir}")
        logger.info(f"  当前文档数: {self.collection.count()}")
    
    def encode(self, texts: List[str], batch_size: Optional[int] = None) -> List[List[float]]:
        """
        文本向量化
        
        Args:
            texts: 文本列表
            batch_size: 批处理大小（可选）
            
        Returns:
            向量列表
        """
        if batch_size is None:
            batch_size = self.embedding_config.get('batch_size', 32)
        
        # 使用模型的encode方法，自动批处理
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_tensor=False
        )
        
        return embeddings.tolist()
    
    def add_jobs(self, jobs: List[Dict], batch_size: int = 50, show_progress: bool = True):
        """
        批量添加岗位
        
        Args:
            jobs: 岗位列表
            batch_size: 批处理大小
            show_progress: 是否显示进度条
        """
        logger.info(f"开始添加岗位到向量数据库，共 {len(jobs)} 条")
        
        # 使用tqdm显示进度
        iterator = tqdm(range(0, len(jobs), batch_size), desc="向量化") if show_progress else range(0, len(jobs), batch_size)
        
        for i in iterator:
            batch = jobs[i:i+batch_size]
            
            # 构建文档（用于向量化的文本）
            documents = []
            metadatas = []
            ids = []
            
            # 批次内按 job_id 去重，避免 ChromaDB upsert 报重复 ID 错误
            seen_ids = set()
            deduped_batch = []
            for job in batch:
                jid = job.get('job_id', '')
                if jid and jid not in seen_ids:
                    seen_ids.add(jid)
                    deduped_batch.append(job)
            batch = deduped_batch

            for job in batch:
                # 合并多个字段作为检索文本
                doc = self._build_document(job)
                documents.append(doc)
                
                # 元数据（用于过滤和返回）
                skills_list = job.get('skills', [])
                metadatas.append({
                    'job_id': job['job_id'],
                    'title': job['title'],
                    'city': job.get('city', ''),
                    'company': job.get('company', ''),
                    'salary_min': str(job.get('salary_min', 0)),
                    'salary_max': str(job.get('salary_max', 0)),
                    'experience': job.get('experience', ''),
                    'education': job.get('education', ''),
                    'industry': job.get('company_industry', ''),
                    'company_size': job.get('company_size', ''),
                    'skills_count': str(len(skills_list)),
                    # 存储技能列表（逗号分隔，最多15个），供搜索结果直接返回
                    'skills': ','.join(skills_list[:15]) if skills_list else '',
                })
                
                ids.append(job['job_id'])
            
            # 向量化
            try:
                embeddings = self.encode(documents, batch_size=len(documents))
                
                # 添加到ChromaDB（upsert：已存在则覆盖，不存在则新增，避免重复报错）
                self.collection.upsert(
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
            except Exception as e:
                logger.error(f"批次 {i//batch_size} 添加失败: {e}")
                continue
        
        logger.info(f"添加完成！当前总文档数: {self.collection.count()}")
    
    def _build_document(self, job: Dict) -> str:
        """
        构建用于检索的文档文本。

        使用结构化字段拼出语义丰富的描述，让向量编码能同时捕获
        岗位类型、技能要求、城市、经验、薪资等维度，提升搜索质量。
        不依赖 JD 详情文本（质量参差不齐）。
        """
        title    = job.get('title', '')
        skills   = job.get('skills', [])
        city     = job.get('city', '')
        company  = job.get('company', '')
        exp      = job.get('experience', '')
        edu      = job.get('education', '')
        sal_min  = job.get('salary_min', 0)
        sal_max  = job.get('salary_max', 0)

        industry = job.get('company_industry', '')
        welfare  = job.get('welfare', [])

        parts = []

        if title:
            parts.append(f"岗位：{title}")

        if skills:
            # 技能重复一次增强权重（小trick，对短文本向量化有帮助）
            skills_str = ' '.join(skills)
            parts.append(f"技能要求：{skills_str}")
            parts.append(skills_str)   # 权重加倍

        if city:
            parts.append(f"工作城市：{city}")

        if exp:
            parts.append(f"工作经验：{exp}")

        if edu:
            parts.append(f"学历要求：{edu}")

        if sal_min and sal_max and (int(float(sal_min)) > 0 or int(float(sal_max)) > 0):
            parts.append(f"薪资范围：{sal_min}-{sal_max}K")

        if industry:
            parts.append(f"行业：{industry}")

        if company:
            parts.append(f"公司：{company}")

        if welfare and isinstance(welfare, list):
            parts.append(f"福利：{' '.join(welfare[:5])}")   # 最多取5条，避免噪音

        return ' | '.join(filter(None, parts))
    
    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict] = None
    ) -> Dict:
        """
        语义搜索
        
        Args:
            query: 查询文本
            top_k: 返回TOP K个结果
            filters: 过滤条件，例如: {"city": "北京"}
            
        Returns:
            {
                'ids': [[...]],
                'distances': [[...]],
                'metadatas': [[...]],
                'documents': [[...]]
            }
        """
        # 向量化查询
        query_embedding = self.encode([query])[0]
        
        # ChromaDB 底层 SQLite 有变量数量限制，n_results 不能过大
        # 实际上向量搜索返回超过 500 条后相似度已很低，没有意义
        MAX_RESULTS = 500
        total = self.collection.count()
        if total == 0:
            return {'ids': [[]], 'distances': [[]], 'metadatas': [[]], 'documents': [[]]}
        n = min(top_k or MAX_RESULTS, MAX_RESULTS, total)

        # 检索
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n,
            where=filters
        )
        
        return results
    
    def search_by_skills(
        self,
        skills: List[str],
        top_k: int = 10,
        filters: Optional[Dict] = None
    ) -> Dict:
        """
        基于技能列表搜索
        
        Args:
            skills: 技能列表
            top_k: 返回TOP K个结果
            filters: 过滤条件
            
        Returns:
            搜索结果
        """
        query = "需要以下技能: " + ", ".join(skills)
        return self.search(query, top_k, filters)
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'total_documents': self.collection.count(),
            'embedding_dim': len(self.model.encode(["test"])[0]),
            'model_name': self.embedding_config['model_name']
        }
    
    def clear(self):
        """清空 collection（删除后重建，避免 ChromaDB get() 默认 100 条限制导致未完全清空）"""
        logger.warning("正在清空向量数据库...")
        count = self.collection.count()
        collection_name = self.vector_config['collection_name']
        self.client.delete_collection(collection_name)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={
                "description": "招聘岗位JD向量",
                "hnsw:space": "cosine"
            }
        )
        logger.info(f"已清空 {count} 个文档（collection 已重建）")


# 测试代码
def test_vector_db():
    """测试向量数据库"""
    import json
    
    print("="*80)
    print("测试向量数据库")
    print("="*80)
    
    # 初始化
    print("\n【初始化向量数据库】")
    db = VectorDB()
    print(f"✅ 初始化成功")
    
    # 统计信息
    stats = db.get_stats()
    print(f"\n📊 统计信息:")
    print(f"  文档总数: {stats['total_documents']}")
    print(f"  向量维度: {stats['embedding_dim']}")
    print(f"  模型: {stats['model_name']}")
    
    # 如果数据库为空，添加测试数据
    if stats['total_documents'] == 0:
        print("\n【添加测试数据】")
        test_jobs = [
            {
                'job_id': 'test_001',
                'title': 'Python后端开发工程师',
                'skills': ['Python', 'Django', 'MySQL', 'Redis'],
                'city': '北京',
                'company': '测试公司A',
                'salary_min': 15,
                'salary_max': 25,
                'jd_text': '负责后端服务开发，使用Python和Django框架，熟悉MySQL和Redis'
            },
            {
                'job_id': 'test_002',
                'title': 'Java高级开发工程师',
                'skills': ['Java', 'Spring Boot', 'MySQL', 'Redis'],
                'city': '上海',
                'company': '测试公司B',
                'salary_min': 20,
                'salary_max': 35,
                'jd_text': '负责Java后端开发，精通Spring Boot，熟悉微服务架构'
            }
        ]
        
        db.add_jobs(test_jobs, show_progress=False)
        print(f"✅ 添加了 {len(test_jobs)} 条测试数据")
    
    # 测试搜索
    print("\n【测试语义搜索】")
    queries = [
        "Python后端开发，熟悉Django",
        "Java微服务开发",
        "前端React开发"
    ]
    
    for query in queries:
        print(f"\n查询: {query}")
        results = db.search(query, top_k=2)
        
        if results['metadatas'] and results['metadatas'][0]:
            print(f"找到 {len(results['metadatas'][0])} 个结果:")
            for i, meta in enumerate(results['metadatas'][0]):
                distance = results['distances'][0][i]
                similarity = 1 / (1 + max(0, distance))  # 距离转相似度，兼容L2/cosine
                print(f"  {i+1}. {meta['title']} - {meta['city']} (相似度: {similarity:.2f})")
        else:
            print("  未找到结果")
    
    print("\n" + "="*80)
    print("🎉 测试完成！")
    print("="*80)


if __name__ == "__main__":
    import sys
    sys.path.append(str(Path(__file__).parent.parent.parent))
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    test_vector_db()
