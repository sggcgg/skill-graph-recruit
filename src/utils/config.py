"""
配置管理模块
"""
import yaml
from pathlib import Path


class Config:
    """配置类"""

    def __init__(self, config_path='config.yaml'):
        # 获取项目根目录（向上查找包含config.yaml的目录）
        current_path = Path(__file__).resolve()
        project_root = current_path.parent.parent.parent  # src/utils/config.py -> src -> project_root
        
        # 如果传入的是相对路径，则基于项目根目录
        config_file = Path(config_path)
        if not config_file.is_absolute():
            self.config_path = project_root / config_path
        else:
            self.config_path = config_file
            
        self.config = self.load_config()

    def load_config(self):
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"配置文件不存在: {self.config_path}\n"
                f"请确保在项目根目录创建 config.yaml 文件"
            )
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    @property
    def neo4j_config(self):
        """Neo4j配置"""
        return self.config['neo4j']

    @property
    def data_config(self):
        """数据路径配置"""
        return self.config['data']

    @property
    def crawler_config(self):
        """爬虫配置"""
        return self.config['crawler']

    @property
    def api_config(self):
        """API配置"""
        return self.config['api']


# 全局配置对象
config = Config()