"""
技能抽取模块（规则匹配 + NLP增强）
这是毕业设计的核心创新点之一
"""
import re
from typing import List, Dict, Tuple, Set
import jieba
import jieba.posseg as pseg
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class SkillExtractor:
    """
    技能抽取器
    
    结合规则匹配和NLP方法从职位描述中抽取技能
    """
    
    def __init__(self, skill_dictionary):
        """
        初始化抽取器
        
        Args:
            skill_dictionary: SkillDictionary实例
        """
        self.skill_dict = skill_dictionary
        self.all_skills = skill_dictionary.all_skills
        
        # 构建技能名称和别名的集合（用于快速匹配）
        self._build_skill_index()
        
        # 加载停用词
        self.stopwords = self._load_stopwords()
        
        # 技能抽取的上下文关键词
        self.context_keywords = [
            '熟悉', '精通', '掌握', '了解', '熟练', '使用', '运用',
            '经验', '能力', '技能', '技术', '框架', '工具', '语言',
            '开发', '设计', '实现', '优化', '负责', '参与',
            '要求', '需要', '具备', '擅长', '会', '懂',
        ]
        
        logger.info(f"技能抽取器初始化完成，技能词典包含 {len(self.all_skills)} 个技能")
    
    def _build_skill_index(self):
        """构建技能索引，用于快速匹配"""
        self.skill_name_map = {}  # 名称 -> 技能信息
        self.skill_alias_map = {}  # 别名 -> 标准名称
        
        for skill in self.all_skills:
            name = skill['name']
            name_lower = name.lower()
            
            # 索引标准名称
            self.skill_name_map[name_lower] = skill
            
            # 索引别名
            for alias in skill.get('aliases', []):
                alias_lower = alias.lower()
                self.skill_alias_map[alias_lower] = name
                
                # 将别名也添加到jieba词典
                jieba.add_word(alias, freq=10000)
            
            # 将技能名称添加到jieba词典（提高分词准确度）
            jieba.add_word(name, freq=10000)
        
        logger.info(f"技能索引构建完成: {len(self.skill_name_map)} 个标准名称, {len(self.skill_alias_map)} 个别名")
    
    def _load_stopwords(self) -> Set[str]:
        """加载停用词"""
        stopwords = {'的', '了', '和', '是', '与', '及', '或', '等', '、'}
        return stopwords
    
    def extract_from_job(self, job: Dict) -> List[Dict]:
        """
        从岗位数据中抽取技能
        
        Args:
            job: 岗位信息，包含title和可选的jd_text
            
        Returns:
            抽取的技能列表，格式:
            [
                {
                    'name': '技能标准名称',
                    'source': 'explicit'|'title'|'jd',
                    'confidence': 0-1,
                    'skill_info': {...}  # 完整技能信息
                }
            ]
        """
        extracted_skills = {}  # 使用dict去重，key为技能name
        
        # 1. 从已标注的skills字段提取（最高优先级）
        if job.get('skills'):
            for skill_text in job['skills']:
                skill_info = self._match_skill(skill_text)
                if skill_info:
                    name = skill_info['name']
                    if name not in extracted_skills:
                        extracted_skills[name] = {
                            'name': name,
                            'source': 'explicit',
                            'confidence': 1.0,
                            'skill_info': skill_info
                        }
        
        # 2. 从职位标题提取
        if job.get('title'):
            title_skills = self._extract_from_text(
                job['title'], 
                source='title', 
                base_confidence=0.9
            )
            for skill in title_skills:
                name = skill['name']
                if name not in extracted_skills or extracted_skills[name]['confidence'] < skill['confidence']:
                    extracted_skills[name] = skill
        
        # 3. 从职位描述提取（如果有JD文本）
        if job.get('jd_text'):
            jd_skills = self._extract_from_text(
                job['jd_text'], 
                source='jd', 
                base_confidence=0.7
            )
            for skill in jd_skills:
                name = skill['name']
                if name not in extracted_skills or extracted_skills[name]['confidence'] < skill['confidence']:
                    extracted_skills[name] = skill
        
        return list(extracted_skills.values())
    
    def _extract_from_text(self, text: str, source: str = 'text', base_confidence: float = 0.7) -> List[Dict]:
        """
        从文本中提取技能
        
        Args:
            text: 待提取文本
            source: 来源标记
            base_confidence: 基础置信度
            
        Returns:
            提取的技能列表
        """
        if not text:
            return []
        
        extracted = []
        
        # 方法1：直接字符串匹配（最精确）
        matched_skills = self._direct_match(text)
        for skill_info in matched_skills:
            extracted.append({
                'name': skill_info['name'],
                'source': source,
                'confidence': min(base_confidence + 0.2, 1.0),  # 直接匹配加分
                'skill_info': skill_info
            })
        
        # 方法2：基于分词的匹配
        word_skills = self._word_based_match(text)
        for skill_info in word_skills:
            name = skill_info['name']
            # 避免重复
            if not any(s['name'] == name for s in extracted):
                extracted.append({
                    'name': name,
                    'source': source,
                    'confidence': base_confidence,
                    'skill_info': skill_info
                })
        
        # 方法3：基于正则表达式的模式匹配
        pattern_skills = self._pattern_match(text)
        for skill_info, confidence_boost in pattern_skills:
            name = skill_info['name']
            if not any(s['name'] == name for s in extracted):
                extracted.append({
                    'name': name,
                    'source': source + '_pattern',
                    'confidence': min(base_confidence + confidence_boost, 1.0),
                    'skill_info': skill_info
                })
        
        return extracted
    
    def _direct_match(self, text: str) -> List[Dict]:
        """直接字符串匹配（不区分大小写）"""
        text_lower = text.lower()
        matched = []

        def _is_match(token: str, haystack: str) -> bool:
            """短名称（≤2字符）用全词边界匹配，避免 'c' 误匹配 'c端'/'c/c++' 等"""
            if len(token) <= 2:
                return bool(re.search(
                    r'(?<![a-zA-Z0-9+#])' + re.escape(token) + r'(?![a-zA-Z0-9+#])',
                    haystack
                ))
            return token in haystack

        # 匹配标准名称
        for name_lower, skill_info in self.skill_name_map.items():
            if _is_match(name_lower, text_lower):
                matched.append(skill_info)

        # 匹配别名
        for alias_lower, standard_name in self.skill_alias_map.items():
            if _is_match(alias_lower, text_lower):
                skill_info = self.skill_name_map.get(standard_name.lower())
                if skill_info and skill_info not in matched:
                    matched.append(skill_info)

        return matched
    
    def _word_based_match(self, text: str) -> List[Dict]:
        """基于分词的匹配（jieba 产出完整词，天然避免子串误匹配）"""
        words = jieba.lcut(text)

        matched = []
        for word in words:
            word_lower = word.lower()

            if word_lower in self.skill_name_map:
                matched.append(self.skill_name_map[word_lower])
            elif word_lower in self.skill_alias_map:
                standard_name = self.skill_alias_map[word_lower]
                skill_info = self.skill_name_map.get(standard_name.lower())
                if skill_info:
                    matched.append(skill_info)

        return matched
    
    def _pattern_match(self, text: str) -> List[Tuple[Dict, float]]:
        """
        基于正则表达式的模式匹配
        
        匹配常见的技能描述模式，如：
        - "熟悉Python开发"
        - "精通Java"
        - "掌握React框架"
        
        Returns:
            (skill_info, confidence_boost) 列表
        """
        matched = []
        
        # 构建模式：上下文关键词 + 技能名称
        for keyword in self.context_keywords:
            # 为每个技能构建模式
            for skill_info in self.all_skills:
                name = skill_info['name']
                
                # 构建正则模式
                pattern = rf'{keyword}.*?{re.escape(name)}'
                
                if re.search(pattern, text, re.IGNORECASE):
                    # 找到匹配，增加置信度
                    confidence_boost = 0.1
                    matched.append((skill_info, confidence_boost))
                    break  # 避免重复
        
        return matched
    
    def _match_skill(self, skill_text: str) -> Dict:
        """
        匹配单个技能文本到标准技能
        
        Args:
            skill_text: 技能文本
            
        Returns:
            匹配的技能信息，如果未匹配则返回None
        """
        skill_text_lower = skill_text.lower().strip()
        
        # 直接匹配标准名称
        if skill_text_lower in self.skill_name_map:
            return self.skill_name_map[skill_text_lower]
        
        # 匹配别名
        if skill_text_lower in self.skill_alias_map:
            standard_name = self.skill_alias_map[skill_text_lower]
            return self.skill_name_map.get(standard_name.lower())
        
        def _fuzzy_contains(token: str, haystack: str) -> bool:
            """短名称（≤2字符）要求全词边界，避免 'c' 误匹配 'c端'/'c/c++' 等"""
            if len(token) <= 2:
                return bool(re.search(
                    r'(?<![a-zA-Z0-9+#])' + re.escape(token) + r'(?![a-zA-Z0-9+#])',
                    haystack
                ))
            return token in haystack

        # 模糊匹配（包含关系）
        for name_lower, skill_info in self.skill_name_map.items():
            if _fuzzy_contains(name_lower, skill_text_lower) or _fuzzy_contains(skill_text_lower, name_lower):
                return skill_info

        # 别名模糊匹配
        for alias_lower, standard_name in self.skill_alias_map.items():
            if _fuzzy_contains(alias_lower, skill_text_lower) or _fuzzy_contains(skill_text_lower, alias_lower):
                return self.skill_name_map.get(standard_name.lower())
        
        return None
    
    def batch_extract(self, jobs: List[Dict], update_jobs: bool = True) -> List[Dict]:
        """
        批量提取技能
        
        Args:
            jobs: 岗位列表
            update_jobs: 是否更新jobs的skills字段
            
        Returns:
            更新后的岗位列表
        """
        logger.info(f"开始批量提取技能，共 {len(jobs)} 个岗位")
        
        for i, job in enumerate(jobs):
            extracted_skills = self.extract_from_job(job)
            
            if update_jobs:
                # 更新skills字段（仅保留标准名称）
                skill_names = [s['name'] for s in extracted_skills]
                job['skills'] = skill_names
                
                # 添加详细信息到新字段
                job['_extracted_skills'] = extracted_skills
            
            if (i + 1) % 1000 == 0:
                logger.info(f"已处理 {i + 1}/{len(jobs)} 个岗位")
        
        logger.info(f"技能提取完成")
        return jobs
    
    def extract_and_enrich(self, job: Dict) -> Dict:
        """
        提取技能并丰富岗位信息
        
        Args:
            job: 岗位信息
            
        Returns:
            丰富后的岗位信息，添加以下字段：
            - skills: 技能名称列表（标准化）
            - _extracted_skills: 详细提取信息
            - _skill_categories: 技能分类统计
            - _avg_skill_hot_score: 平均技能热度
        """
        extracted_skills = self.extract_from_job(job)
        
        # 更新基本skills字段
        job['skills'] = [s['name'] for s in extracted_skills]
        job['_extracted_skills'] = extracted_skills
        
        # 统计技能分类
        categories = {}
        hot_scores = []
        
        for skill_data in extracted_skills:
            skill_info = skill_data['skill_info']
            category = skill_info.get('category', 'unknown')
            categories[category] = categories.get(category, 0) + 1
            
            hot_score = skill_info.get('hot_score', 0)
            if hot_score > 0:
                hot_scores.append(hot_score)
        
        job['_skill_categories'] = categories
        job['_avg_skill_hot_score'] = sum(hot_scores) / len(hot_scores) if hot_scores else 0
        
        return job


def test_extractor():
    """测试技能抽取器"""
    from src.graph_builder.skill_dictionary import SkillDictionary
    from src.utils.config import config
    
    # 加载技能词典
    dict_path = config.data_config['skill_dict']
    skill_dict = SkillDictionary(dict_path)
    
    # 创建抽取器
    extractor = SkillExtractor(skill_dict)
    
    # 测试用例
    test_jobs = [
        {
            'job_id': 'test_1',
            'title': 'Python后端开发工程师',
            'skills': ['Python', 'Django', 'MySQL'],
            'jd_text': '岗位要求：1. 熟悉Python开发，精通Django框架；2. 熟练使用MySQL数据库；3. 了解Redis缓存技术。'
        },
        {
            'job_id': 'test_2',
            'title': 'Java高级开发工程师',
            'skills': [],
            'jd_text': '要求精通Java，掌握Spring Boot、MyBatis，熟悉微服务架构，有Docker和Kubernetes使用经验。'
        },
        {
            'job_id': 'test_3',
            'title': '前端开发',
            'skills': ['Vue', 'React'],
            'jd_text': '熟练掌握Vue3和React开发，了解TypeScript，有Webpack配置经验。'
        }
    ]
    
    print("=== 技能抽取测试 ===\n")
    
    for job in test_jobs:
        print(f"岗位: {job['title']}")
        print(f"原始skills: {job['skills']}")
        
        extracted = extractor.extract_from_job(job)
        print(f"抽取结果 ({len(extracted)}个):")
        for skill_data in extracted:
            print(f"  - {skill_data['name']} (来源: {skill_data['source']}, 置信度: {skill_data['confidence']:.2f})")
        
        print()


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    test_extractor()
