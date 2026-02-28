"""
Neo4j数据导入模块
将清洗后的招聘数据和技能关系导入Neo4j图数据库
"""
from py2neo import Graph, Node, Relationship, NodeMatcher
from typing import List, Dict
import logging
from datetime import datetime
from collections import Counter
import math

logger = logging.getLogger(__name__)


class Neo4jImporter:
    """Neo4j数据导入器"""
    
    def __init__(self, uri: str = "neo4j://127.0.0.1:7687",
                 user: str = "neo4j", 
                 password: str = "password",
                 skill_dictionary=None):
        """
        初始化导入器
        
        Args:
            uri: Neo4j连接URI
            user: 用户名
            password: 密码
            skill_dictionary: SkillDictionary实例（用于技能标准化）
        """
        try:
            self.graph = Graph(uri, auth=(user, password))
            self.matcher = NodeMatcher(self.graph)
            logger.info(f"成功连接到Neo4j: {uri}")
        except Exception as e:
            logger.error(f"连接Neo4j失败: {e}")
            raise
        
        self.stats = {
            'skills_created': 0,
            'jobs_created': 0,
            'companies_created': 0,
            'requires_created': 0,
            'related_to_created': 0,
            'posted_by_created': 0,
            'skills_normalized': 0  # 标准化的技能数量
        }
        
        # 用于跟踪已警告过的未定义技能，避免重复日志
        self._warned_skills = set()
        
        # 技能词典（用于标准化）
        self.skill_dictionary = skill_dictionary
        
        # 构建技能标准化映射表（别名 -> 标准名称）
        self._skill_alias_map = {}
        if self.skill_dictionary:
            self._build_alias_map()
    
    def _build_alias_map(self):
        """
        构建技能别名映射表
        将所有别名映射到标准技能名称，用于技能标准化
        """
        logger.info("构建技能别名映射表...")
        
        for skill in self.skill_dictionary.all_skills:
            standard_name = skill['name']
            
            # 标准名称也加入映射（自己映射到自己）
            self._skill_alias_map[standard_name.lower()] = standard_name
            
            # 添加所有别名的映射
            for alias in skill.get('aliases', []):
                self._skill_alias_map[alias.lower()] = standard_name
        
        logger.info(f"别名映射表构建完成，共 {len(self._skill_alias_map)} 个映射")
    
    def normalize_skill_name(self, skill_name: str) -> str:
        """
        标准化技能名称
        通过别名映射表将各种变体统一到标准名称
        
        Args:
            skill_name: 原始技能名称
            
        Returns:
            标准化后的技能名称，如果未找到映射则返回原名称
        """
        if not self._skill_alias_map:
            return skill_name
        
        # 尝试精确匹配（不区分大小写）
        normalized = self._skill_alias_map.get(skill_name.lower())
        
        if normalized and normalized != skill_name:
            self.stats['skills_normalized'] += 1
            logger.debug(f"技能标准化: {skill_name} -> {normalized}")
        
        return normalized if normalized else skill_name
    
    def create_indexes(self):
        """创建索引和约束"""
        logger.info("创建索引和约束...")
        
        # 创建约束（唯一性）
        constraints = [
            "CREATE CONSTRAINT skill_id IF NOT EXISTS FOR (s:Skill) REQUIRE s.skill_id IS UNIQUE",
            "CREATE CONSTRAINT skill_name IF NOT EXISTS FOR (s:Skill) REQUIRE s.name IS UNIQUE",
            "CREATE CONSTRAINT job_id IF NOT EXISTS FOR (j:Job) REQUIRE j.job_id IS UNIQUE",
            "CREATE CONSTRAINT company_id IF NOT EXISTS FOR (c:Company) REQUIRE c.company_id IS UNIQUE",
        ]
        
        for constraint in constraints:
            try:
                self.graph.run(constraint)
                logger.info(f"创建约束: {constraint.split()[2]}")
            except Exception as e:
                logger.warning(f"约束可能已存在: {e}")
        
        # 创建索引
        indexes = [
            "CREATE INDEX skill_category_idx IF NOT EXISTS FOR (s:Skill) ON (s.category)",
            "CREATE INDEX skill_hot_score_idx IF NOT EXISTS FOR (s:Skill) ON (s.hot_score)",
            "CREATE INDEX job_city_idx IF NOT EXISTS FOR (j:Job) ON (j.city)",
            "CREATE INDEX job_salary_idx IF NOT EXISTS FOR (j:Job) ON (j.salary_min, j.salary_max)",
            "CREATE INDEX company_name_idx IF NOT EXISTS FOR (c:Company) ON (c.name)",
        ]
        
        for index in indexes:
            try:
                self.graph.run(index)
                logger.info(f"创建索引: {index.split()[2]}")
            except Exception as e:
                logger.warning(f"索引可能已存在: {e}")
        
        # 创建全文索引（用于技能搜索）
        try:
            self.graph.run(
                "CREATE FULLTEXT INDEX skill_fulltext IF NOT EXISTS "
                "FOR (s:Skill) ON EACH [s.name, s.aliases]"
            )
            logger.info("创建全文索引: skill_fulltext")
        except Exception as e:
            logger.warning(f"全文索引可能已存在: {e}")
    
    def import_skills_from_dictionary(self, skill_dictionary) -> int:
        """
        从技能词典导入技能节点
        
        Args:
            skill_dictionary: SkillDictionary实例
            
        Returns:
            创建的技能节点数
        """
        logger.info("开始导入技能节点...")
        
        tx = self.graph.begin()
        
        for skill_info in skill_dictionary.all_skills:
            # 创建技能节点
            skill_node = Node(
                "Skill",
                skill_id=f"skill_{skill_info['name'].lower().replace(' ', '_')}",
                name=skill_info['name'],
                category=skill_info.get('category', 'unknown'),
                sub_category=skill_info.get('sub_category', ''),
                level=skill_info.get('level', ''),
                hot_score=skill_info.get('hot_score', 0),
                aliases=skill_info.get('aliases', []),
                description=skill_info.get('description', ''),
                parent=skill_info.get('parent', ''),
                demand_count=0,  # 初始值，后续更新
                avg_salary_min=0.0,
                avg_salary_max=0.0,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
            
            tx.merge(skill_node, "Skill", "skill_id")  # 使用skill_id作为merge key
            self.stats['skills_created'] += 1
        
        self.graph.commit(tx)
        logger.info(f"技能节点导入完成: {self.stats['skills_created']} 个")
        
        return self.stats['skills_created']
    
    def import_jobs(self, jobs: List[Dict], batch_size: int = 100) -> int:
        """
        导入岗位节点和关系
        
        Args:
            jobs: 岗位列表
            batch_size: 批处理大小
            
        Returns:
            创建的岗位节点数
        """
        logger.info(f"开始导入岗位节点和关系，共 {len(jobs)} 个岗位")
        
        company_cache = {}  # 公司缓存
        skill_cache = {}    # 技能缓存
        failed_jobs = []    # 记录失败的岗位
        
        for i in range(0, len(jobs), batch_size):
            batch = jobs[i:i+batch_size]
            
            for job in batch:
                tx = None
                try:
                    # 为每个岗位创建独立事务，避免一个失败影响整批
                    tx = self.graph.begin()
                    
                    # 1. 创建岗位节点
                    job_node = self._create_job_node(job, tx)
                    
                    # 2. 创建/获取公司节点
                    company_node = self._get_or_create_company(
                        job, company_cache, tx
                    )
                    
                    # 3. 创建 POSTED_BY 关系
                    if company_node:
                        posted_by = Relationship(
                            job_node, "POSTED_BY", company_node,
                            post_date=job.get('publish_date', '')
                        )
                        tx.merge(posted_by)
                        self.stats['posted_by_created'] += 1
                    
                    # 4. 创建 REQUIRES 关系（岗位要求技能）
                    skills = job.get('skills', [])
                    if isinstance(skills, list):
                        for skill_name in skills:
                            skill_node = self._get_skill_node(
                                skill_name, skill_cache, tx
                            )
                            if skill_node:
                                requires = Relationship(
                                    job_node, "REQUIRES", skill_node,
                                    importance="must",  # 可以从_extracted_skills获取更详细信息
                                    source="explicit",
                                    confidence=1.0,
                                    extracted_at=datetime.now().isoformat()
                                )
                                tx.merge(requires)
                                self.stats['requires_created'] += 1
                    
                    # 提交事务
                    self.graph.commit(tx)
                    self.stats['jobs_created'] += 1
                    
                except Exception as e:
                    logger.error(f"导入岗位失败 {job.get('job_id')}: {e}")
                    failed_jobs.append((job.get('job_id'), str(e)))
                    # 回滚失败的事务
                    if tx:
                        try:
                            self.graph.rollback(tx)
                        except:
                            pass
                    continue
            
            if (i + batch_size) % 1000 == 0 or (i + batch_size) >= len(jobs):
                logger.info(f"已处理 {min(i+batch_size, len(jobs))}/{len(jobs)} 个岗位，成功: {self.stats['jobs_created']}, 失败: {len(failed_jobs)}")
        
        if failed_jobs:
            logger.warning(f"共有 {len(failed_jobs)} 个岗位导入失败")
            # 只显示前10个失败案例
            for job_id, error in failed_jobs[:10]:
                logger.warning(f"  - {job_id}: {error}")
        
        logger.info(f"岗位导入完成: {self.stats['jobs_created']} 个")
        return self.stats['jobs_created']
    
    def _create_job_node(self, job: Dict, tx) -> Node:
        """创建岗位节点"""
        job_node = Node(
            "Job",
            job_id=job['job_id'],
            title=job.get('title', ''),
            city=job.get('city', ''),
            district=job.get('district', ''),
            business_district=job.get('business_district', ''),
            salary_min=job.get('salary_min', 0),
            salary_max=job.get('salary_max', 0),
            salary_text=job.get('salary_text', ''),
            experience=job.get('experience', ''),
            education=job.get('education', ''),
            publish_date=job.get('publish_date', ''),
            source=job.get('source', ''),
            welfare=job.get('welfare', []),
            jd_text=job.get('jd_text', ''),
            skill_count=len(job.get('skills', [])),
            created_at=datetime.now().isoformat()
        )
        
        tx.merge(job_node, "Job", "job_id")
        return job_node
    
    def _get_or_create_company(self, job: Dict, cache: Dict, tx) -> Node:
        """获取或创建公司节点"""
        company_name = job.get('company', '').strip()
        if not company_name:
            return None
        
        # 检查缓存
        if company_name in cache:
            return cache[company_name]
        
        # 生成公司ID
        company_id = f"company_{company_name.lower().replace(' ', '_')}"
        
        # 尝试从数据库获取
        company_node = self.matcher.match("Company", company_id=company_id).first()
        
        if not company_node:
            # 创建新公司节点
            company_node = Node(
                "Company",
                company_id=company_id,
                name=company_name,
                industry=job.get('company_industry', ''),
                size=job.get('company_size', ''),
                stage=job.get('company_stage', ''),
                city=job.get('city', ''),
                job_count=0,  # 后续更新
                avg_salary_min=0.0,
                avg_salary_max=0.0,
                top_skills=[],
                created_at=datetime.now().isoformat()
            )
            tx.merge(company_node, "Company", "company_id")
            self.stats['companies_created'] += 1
        
        # 添加到缓存
        cache[company_name] = company_node
        return company_node
    
    def _get_skill_node(self, skill_name: str, cache: Dict, tx) -> Node:
        """
        获取技能节点（只使用已存在的技能，不自动创建）
        支持技能标准化：自动将别名映射到标准名称
        
        Args:
            skill_name: 技能名称（可能是别名）
            cache: 缓存字典
            tx: 事务对象
            
        Returns:
            技能节点（如果存在），否则返回None
        """
        # 步骤1：技能标准化（别名 -> 标准名称）
        normalized_name = self.normalize_skill_name(skill_name)
        
        # 步骤2：检查缓存
        if normalized_name in cache:
            return cache[normalized_name]
        
        # 步骤3：从数据库获取（使用标准化后的名称）
        skill_node = self.matcher.match("Skill", name=normalized_name).first()
        
        if skill_node:
            cache[normalized_name] = skill_node
            # 也缓存原始名称，避免重复标准化
            if skill_name != normalized_name:
                cache[skill_name] = skill_node
            return skill_node
        else:
            # 技能不在skill_taxonomy.json中，跳过
            # 使用debug级别避免日志过多
            if skill_name not in self._warned_skills:
                logger.debug(f"跳过未定义的技能: {skill_name}")
                self._warned_skills.add(skill_name)
            return None
    
    def build_skill_relationships(self, min_co_occurrence: int = 10):
        """
        构建技能关联关系
        基于岗位共现频率计算技能之间的关联度
        
        Args:
            min_co_occurrence: 最小共现次数阈值
        """
        logger.info("开始构建技能关联关系...")
        
        # Cypher查询：计算技能共现
        query = f"""
        MATCH (s1:Skill)<-[:REQUIRES]-(j:Job)-[:REQUIRES]->(s2:Skill)
        WHERE s1.skill_id < s2.skill_id
        WITH s1, s2, COUNT(j) as co_occurrence
        WHERE co_occurrence >= {min_co_occurrence}
        
        // 计算相关性分数（使用点互信息PMI）
        MATCH (s1)<-[:REQUIRES]-(j1:Job)
        WITH s1, s2, co_occurrence, COUNT(DISTINCT j1) as s1_count
        
        MATCH (s2)<-[:REQUIRES]-(j2:Job)
        WITH s1, s2, co_occurrence, s1_count, COUNT(DISTINCT j2) as s2_count
        
        MATCH (j:Job)
        WITH s1, s2, co_occurrence, s1_count, s2_count, COUNT(j) as total_jobs
        
        // 计算correlation和strength
        WITH s1, s2, co_occurrence, s1_count, s2_count, total_jobs,
             co_occurrence * 1.0 / sqrt(s1_count * s2_count) as correlation,
             toFloat(co_occurrence) / 1000.0 as strength
        
        MERGE (s1)-[r:RELATED_TO]-(s2)
        SET r.co_occurrence = co_occurrence,
            r.correlation = correlation,
            r.strength = CASE WHEN strength > 1.0 THEN 1.0 ELSE strength END,
            r.relation_type = 'complementary',
            r.created_at = datetime()
        
        RETURN COUNT(r) as relationship_count
        """
        
        try:
            result = self.graph.run(query).data()
            count = result[0]['relationship_count'] if result else 0
            self.stats['related_to_created'] = count
            logger.info(f"技能关联关系创建完成: {count} 条")
        except Exception as e:
            logger.error(f"构建技能关系失败: {e}")
    
    def update_statistics(self):
        """更新图谱统计信息"""
        logger.info("更新图谱统计信息...")
        
        # 1. 更新技能的需求数量和平均薪资
        query_skill_stats = """
        MATCH (s:Skill)<-[:REQUIRES]-(j:Job)
        WITH s, COUNT(j) as demand_count, 
             AVG(j.salary_min) as avg_min, 
             AVG(j.salary_max) as avg_max
        SET s.demand_count = demand_count,
            s.avg_salary_min = avg_min,
            s.avg_salary_max = avg_max,
            s.updated_at = datetime()
        RETURN COUNT(s) as updated_skills
        """
        
        result = self.graph.run(query_skill_stats).data()
        logger.info(f"更新技能统计: {result[0]['updated_skills']} 个")
        
        # 2. 更新公司的岗位数量和平均薪资
        query_company_stats = """
        MATCH (c:Company)<-[:POSTED_BY]-(j:Job)
        WITH c, COUNT(j) as job_count,
             AVG(j.salary_min) as avg_min,
             AVG(j.salary_max) as avg_max
        SET c.job_count = job_count,
            c.avg_salary_min = avg_min,
            c.avg_salary_max = avg_max
        RETURN COUNT(c) as updated_companies
        """
        
        result = self.graph.run(query_company_stats).data()
        logger.info(f"更新公司统计: {result[0]['updated_companies']} 个")
        
        # 3. 更新公司的TOP技能
        query_company_top_skills = """
        MATCH (c:Company)<-[:POSTED_BY]-(j:Job)-[:REQUIRES]->(s:Skill)
        WITH c, s.name as skill_name, COUNT(j) as skill_count
        ORDER BY skill_count DESC
        WITH c, COLLECT(skill_name)[0..10] as top_skills
        SET c.top_skills = top_skills
        RETURN COUNT(c) as updated_companies
        """
        
        result = self.graph.run(query_company_top_skills).data()
        logger.info(f"更新公司TOP技能: {result[0]['updated_companies']} 个")
    
    def get_import_stats(self) -> Dict:
        """获取导入统计信息"""
        return self.stats
    
    def get_graph_stats(self) -> Dict:
        """获取图谱统计信息"""
        stats = {}
        
        # 节点统计
        queries = {
            'skill_count': "MATCH (s:Skill) RETURN COUNT(s) as count",
            'job_count': "MATCH (j:Job) RETURN COUNT(j) as count",
            'company_count': "MATCH (c:Company) RETURN COUNT(c) as count",
            'requires_count': "MATCH ()-[r:REQUIRES]->() RETURN COUNT(r) as count",
            'related_to_count': "MATCH ()-[r:RELATED_TO]-() RETURN COUNT(r) as count",
            'posted_by_count': "MATCH ()-[r:POSTED_BY]->() RETURN COUNT(r) as count",
        }
        
        for key, query in queries.items():
            result = self.graph.run(query).data()
            stats[key] = result[0]['count'] if result else 0
        
        return stats


def import_data_pipeline(skill_dict_path: str, cleaned_data_paths: List[str],
                         neo4j_uri: str, neo4j_user: str, neo4j_password: str):
    """
    完整的数据导入流程
    
    Args:
        skill_dict_path: 技能词典路径
        cleaned_data_paths: 清洗后数据文件路径列表
        neo4j_uri: Neo4j连接URI
        neo4j_user: 用户名
        neo4j_password: 密码
    """
    import json
    import sys
    from pathlib import Path
    
    # 添加项目根目录到path
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    from src.graph_builder.skill_dictionary import SkillDictionary
    
    # 1. 加载技能词典
    logger.info("加载技能词典...")
    skill_dict = SkillDictionary(skill_dict_path)
    
    # 2. 连接Neo4j（传入技能词典以支持技能标准化）
    importer = Neo4jImporter(neo4j_uri, neo4j_user, neo4j_password, skill_dictionary=skill_dict)
    
    # 3. 创建索引
    importer.create_indexes()
    
    # 4. 导入技能节点
    importer.import_skills_from_dictionary(skill_dict)
    
    # 5. 导入岗位数据
    all_jobs = []
    for data_path in cleaned_data_paths:
        with open(data_path, 'r', encoding='utf-8') as f:
            jobs = json.load(f)
            all_jobs.extend(jobs)
    
    logger.info(f"加载了 {len(all_jobs)} 个岗位数据")
    importer.import_jobs(all_jobs, batch_size=100)
    
    # 6. 构建技能关系
    importer.build_skill_relationships(min_co_occurrence=10)
    
    # 7. 更新统计信息
    importer.update_statistics()
    
    # 8. 输出统计报告
    print("\n" + "="*50)
    print("=== Neo4j导入统计 ===")
    import_stats = importer.get_import_stats()
    for key, value in import_stats.items():
        print(f"{key}: {value}")
    
    print("\n=== 图谱统计 ===")
    graph_stats = importer.get_graph_stats()
    for key, value in graph_stats.items():
        print(f"{key}: {value}")
    
    logger.info("数据导入完成！")


if __name__ == '__main__':
    import sys
    from pathlib import Path
    
    # 添加项目根目录到sys.path（必须在其他导入之前）
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    skill_dict_path = str(project_root / 'data' / 'skill_dict' / 'skill_taxonomy.json')
    cleaned_dir = project_root / 'data' / 'cleaned'
    
    # 获取所有清洗后的数据文件
    cleaned_files = list(cleaned_dir.glob('boss_*_cleaned.json'))
    
    if not cleaned_files:
        logger.error("未找到清洗后的数据文件，请先运行data_cleaner.py")
        sys.exit(1)
    
    logger.info(f"找到 {len(cleaned_files)} 个清洗后的数据文件")
    
    # 执行导入
    import_data_pipeline(
        skill_dict_path=skill_dict_path,
        cleaned_data_paths=[str(f) for f in cleaned_files],
        neo4j_uri="neo4j://127.0.0.1:7687",
        neo4j_user="neo4j",
        neo4j_password="Qsgx@15115932429"  # 请修改为实际密码
    )
