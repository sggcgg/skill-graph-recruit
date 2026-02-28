"""
初始化Neo4j数据库
导入技能词典，创建索引
"""
import sys
import json

sys.path.append('.')

from src.utils.config import config
from src.graph_builder.neo4j_manager import Neo4jManager
from src.graph_builder.skill_dictionary import SkillDictionary
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_database():
    """初始化数据库"""

    # 连接Neo4j
    neo4j_config = config.neo4j_config
    manager = Neo4jManager(
        uri=neo4j_config['uri'],
        user=neo4j_config['user'],
        password=neo4j_config['password']
    )

    # 测试连接
    if not manager.test_connection():
        logger.error("Neo4j连接失败")
        return


    # 创建索引
    logger.info("创建索引...")
    manager.create_indexes()

    # 导入技能词典
    logger.info("导入技能词典...")
    dict_path = config.data_config['skill_dict']
    skill_dict = SkillDictionary(dict_path)

    # 批量创建技能节点（v2.0优化）
    skills_data = []
    for skill in skill_dict.all_skills:
        skill_node = {
            'name': skill['name'],
            'category': skill['category'],
            'level': skill.get('level', '常用'),
            'hot_score': skill.get('hot_score', 0),  # v2.0: 使用词典中的热度
            'job_count': 0,  # 后续从实际职位数据中计算
            'description': skill.get('description', ''),  # v2.0: 添加描述
            'aliases': ','.join(skill.get('aliases', []))  # v2.0: 存储别名
        }
        skills_data.append(skill_node)

    # 使用UNWIND批量插入（v2.0增强）
    query = """
    UNWIND $skills as skill_data
    MERGE (s:Skill {name: skill_data.name})
    SET s.category = skill_data.category,
        s.level = skill_data.level,
        s.hot_score = skill_data.hot_score,
        s.job_count = skill_data.job_count,
        s.description = skill_data.description,
        s.aliases = skill_data.aliases
    """

    manager.execute_write(query, {'skills': skills_data})
    logger.info(f"成功导入 {len(skills_data)} 个技能节点（v2.0版本）")

    # 创建分类节点
    categories = set(s['category'] for s in skill_dict.all_skills)
    for category in categories:
        query = """
        MERGE (c:Category {name: $category})
        """
        manager.execute_write(query, {'category': category})

    logger.info(f"成功创建 {len(categories)} 个分类节点")

    # 创建技能-分类关系
    query = """
    MATCH (s:Skill)
    MATCH (c:Category {name: s.category})
    MERGE (s)-[:BELONGS_TO]->(c)
    """
    manager.execute_write(query)
    logger.info("技能-分类关系创建完成")

    # v2.0新增: 创建技能强关联关系
    logger.info("创建技能强关联关系...")
    # 使用绝对路径加载完整词典
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent
    full_dict_path = project_root / dict_path
    
    with open(full_dict_path, 'r', encoding='utf-8') as f:
        full_dict = json.load(f)

    if '技能关系' in full_dict and '强关联' in full_dict['技能关系']:
        relations = full_dict['技能关系']['强关联']
        for rel in relations:
            query_rel = """
            MATCH (s1:Skill {name: $source})
            MATCH (s2:Skill {name: $target})
            MERGE (s1)-[r:STRONG_RELATED]->(s2)
            SET r.strength = $strength
            """
            try:
                manager.execute_write(query_rel, {
                    'source': rel['source'],
                    'target': rel['target'],
                    'strength': rel['strength']
                })
            except Exception as e:
                logger.warning(f"创建关系失败 {rel['source']}->{rel['target']}: {str(e)}")
        logger.info(f"成功创建 {len(relations)} 个技能强关联关系")

    # 显示统计信息
    stats = manager.get_database_stats()
    print("\n✅ 初始化完成！")
    print("\n数据库统计：")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    manager.close()


if __name__ == "__main__":
    init_database()