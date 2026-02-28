"""
Neo4j数据库管理器
"""
from neo4j import GraphDatabase
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class Neo4jManager:
    """Neo4j连接和操作管理"""

    def __init__(self, uri: str, user: str, password: str):
        """
        初始化Neo4j连接

        Args:
            uri: Neo4j连接URI，如 bolt://localhost:7687
            user: 用户名
            password: 密码
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        logger.info(f"Neo4j连接成功: {uri}")

    def close(self):
        """关闭连接"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j连接已关闭")

    def test_connection(self):
        """测试连接"""
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 'Connection OK' as message")
                message = result.single()['message']
                logger.info(f"连接测试: {message}")
                return True
        except Exception as e:
            logger.error(f"连接失败: {str(e)}")
            return False

    def execute_query(self, query: str, parameters: Dict = None) -> List[Dict]:
        """
        执行Cypher查询

        Args:
            query: Cypher查询语句
            parameters: 查询参数

        Returns:
            查询结果列表
        """
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]

    def execute_write(self, query: str, parameters: Dict = None):
        """
        执行写入操作

        Args:
            query: Cypher语句
            parameters: 参数
        """
        with self.driver.session() as session:
            session.run(query, parameters or {})

    def clear_database(self):
        """清空数据库（谨慎使用）"""
        query = "MATCH (n) DETACH DELETE n"
        self.execute_write(query)
        logger.warning("数据库已清空")

    def create_indexes(self):
        """创建索引"""
        indexes = [
            "CREATE INDEX skill_name_idx IF NOT EXISTS FOR (s:Skill) ON (s.name)",
            "CREATE INDEX job_id_idx IF NOT EXISTS FOR (j:Job) ON (j.job_id)",
            "CREATE INDEX job_title_idx IF NOT EXISTS FOR (j:Job) ON (j.title)",
            "CREATE INDEX job_city_idx IF NOT EXISTS FOR (j:Job) ON (j.city)",
        ]

        for index_query in indexes:
            try:
                self.execute_write(index_query)
                logger.info(f"索引创建成功: {index_query[:50]}...")
            except Exception as e:
                logger.warning(f"索引可能已存在: {str(e)}")

    def get_node_count(self, label: str = None) -> int:
        """获取节点数量"""
        if label:
            query = f"MATCH (n:{label}) RETURN count(n) as count"
        else:
            query = "MATCH (n) RETURN count(n) as count"

        result = self.execute_query(query)
        return result[0]['count'] if result else 0

    def get_relationship_count(self, rel_type: str = None) -> int:
        """获取关系数量"""
        if rel_type:
            query = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count"
        else:
            query = "MATCH ()-[r]->() RETURN count(r) as count"

        result = self.execute_query(query)
        return result[0]['count'] if result else 0

    def get_city_count(self) -> int:
        """获取 Job 节点中不重复城市的数量"""
        query = (
            "MATCH (j:Job) WHERE j.city IS NOT NULL AND j.city <> '' "
            "RETURN count(DISTINCT j.city) AS count"
        )
        result = self.execute_query(query)
        return result[0]['count'] if result else 0

    def get_database_stats(self) -> Dict:
        """获取数据库统计信息"""
        return {
            'skills': self.get_node_count('Skill'),
            'jobs': self.get_node_count('Job'),
            'cities': self.get_city_count(),
            'total_nodes': self.get_node_count(),
            'requires_relationships': self.get_relationship_count('REQUIRES'),
            'related_relationships': self.get_relationship_count('RELATED_TO'),
            'total_relationships': self.get_relationship_count()
        }


# 使用示例
if __name__ == "__main__":
    from src.utils.config import config

    # 初始化管理器
    neo4j_config = config.neo4j_config
    manager = Neo4jManager(
        uri=neo4j_config['uri'],
        user=neo4j_config['user'],
        password=neo4j_config['password']
    )

    # 测试连接
    if manager.test_connection():
        print("✅ Neo4j连接成功！")

        # 显示统计信息
        stats = manager.get_database_stats()
        print("\n数据库统计：")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    else:
        print("❌ Neo4j连接失败，请检查配置")

    manager.close()