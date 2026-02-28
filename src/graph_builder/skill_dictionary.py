"""
技能词典管理
"""
import json
from pathlib import Path
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class SkillDictionary:
    """技能词典管理类"""

    def __init__(self, dict_path: str):
        """
        初始化技能词典

        Args:
            dict_path: 技能词典JSON文件路径
        """
        # 处理路径：如果是相对路径，基于项目根目录
        config_file = Path(dict_path)
        if not config_file.is_absolute():
            # 获取项目根目录（src/graph_builder -> src -> project_root）
            project_root = Path(__file__).resolve().parent.parent.parent
            self.dict_path = project_root / dict_path
        else:
            self.dict_path = config_file
            
        self.skills_data = self.load_dictionary()
        self.all_skills = self.flatten_skills()

        logger.info(f"技能词典加载成功，共 {len(self.all_skills)} 个技能")

    def load_dictionary(self) -> Dict:
        """加载技能词典"""
        if not self.dict_path.exists():
            raise FileNotFoundError(
                f"技能词典文件不存在: {self.dict_path}\n"
                f"请确保在项目根目录有 data/skill_dict/skill_taxonomy.json 文件"
            )
        with open(self.dict_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data['技能分类体系']

    def flatten_skills(self) -> List[Dict]:
        """
        扁平化技能列表

        Returns:
            [
                {
                    'name': '技能名',
                    'category': '分类',
                    'level': '级别',
                    'aliases': ['别名1', '别名2'],
                    ...
                }
            ]
        """
        all_skills = []

        for category_key, skills_list in self.skills_data.items():
            # 提取分类名（去除序号）
            category_name = category_key.split('_')[1] if '_' in category_key else category_key

            for skill_info in skills_list:
                skill_dict = skill_info.copy()
                skill_dict['category'] = category_name
                all_skills.append(skill_dict)

        return all_skills

    def get_skills_by_category(self, category: str) -> List[Dict]:
        """按分类获取技能"""
        return [s for s in self.all_skills if s['category'] == category]

    def get_skills_by_level(self, level: str) -> List[Dict]:
        """按级别获取技能"""
        return [s for s in self.all_skills if s.get('level') == level]

    def get_skills_by_hot_score(self, min_score: int = 70) -> List[Dict]:
        """按热度获取技能（v2.0新增）"""
        return sorted(
            [s for s in self.all_skills if s.get('hot_score', 0) >= min_score],
            key=lambda x: x.get('hot_score', 0),
            reverse=True
        )

    def search_skill(self, keyword: str) -> List[Dict]:
        """搜索技能"""
        keyword_lower = keyword.lower()
        results = []

        for skill in self.all_skills:
            # 在名称和别名中搜索
            if keyword_lower in skill['name'].lower():
                results.append(skill)
                continue

            aliases = skill.get('aliases', [])
            if any(keyword_lower in alias.lower() for alias in aliases):
                results.append(skill)

        return results

    def get_skill_by_name(self, skill_name: str) -> Dict:
        """根据名称获取技能信息"""
        for skill in self.all_skills:
            if skill['name'].lower() == skill_name.lower():
                return skill
        return None

    def match_skill_by_alias(self, text: str) -> List[Dict]:
        """
        通过别名匹配技能（v2.0优化）
        支持更灵活的匹配策略
        """
        text_lower = text.lower()
        matched = []

        for skill in self.all_skills:
            # 精确匹配名称
            if skill['name'].lower() == text_lower:
                matched.append(skill)
                continue

            # 匹配别名
            aliases = skill.get('aliases', [])
            if text_lower in [a.lower() for a in aliases]:
                matched.append(skill)

        return matched

    def get_statistics(self) -> Dict:
        """获取统计信息（v2.0增强）"""
        from collections import Counter

        categories = Counter(s['category'] for s in self.all_skills)
        levels = Counter(s.get('level', 'unknown') for s in self.all_skills)

        # v2.0: 添加热度统计
        hot_skills = len([s for s in self.all_skills if s.get('hot_score', 0) >= 80])
        avg_hot_score = sum(s.get('hot_score', 0) for s in self.all_skills) / len(self.all_skills)

        return {
            'total_skills': len(self.all_skills),
            'categories': dict(categories),
            'levels': dict(levels),
            'hot_skills_count': hot_skills,  # 新增
            'avg_hot_score': round(avg_hot_score, 2)  # 新增
        }


# 使用示例
if __name__ == "__main__":
    from src.utils.config import config

    # 加载词典
    dict_path = config.data_config['skill_dict']
    skill_dict = SkillDictionary(dict_path)

    # 显示统计信息
    stats = skill_dict.get_statistics()
    print("技能词典统计（v2.0）：")
    print(f"  总技能数: {stats['total_skills']}")
    print(f"  高热度技能(≥80分): {stats['hot_skills_count']}")
    print(f"  平均热度分数: {stats['avg_hot_score']}")
    print(f"\n分类分布:")
    for cat, count in sorted(stats['categories'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {cat}: {count}")
    print(f"\n级别分布:")
    for level, count in stats['levels'].items():
        print(f"  {level}: {count}")

    # 测试搜索
    print("\n搜索'Python':")
    results = skill_dict.search_skill('Python')
    for skill in results:
        hot_score = skill.get('hot_score', 0)
        print(f"  - {skill['name']} ({skill['category']}) - 热度: {hot_score}")

    # v2.0: 测试热门技能
    print("\n热门技能(热度≥90):")
    hot_skills = skill_dict.get_skills_by_hot_score(min_score=90)
    for skill in hot_skills[:10]:
        print(f"  - {skill['name']}: {skill['hot_score']}")