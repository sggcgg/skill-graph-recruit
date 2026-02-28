"""
招聘数据清洗模块
处理空值、异常薪资、重复数据、文本规范化等问题
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import hashlib
import logging

logger = logging.getLogger(__name__)

# ─────────────────────── 常量 ───────────────────────

# 无意义/通用词，不算有效技能
INVALID_SKILL_TOKENS = {
    '熟悉', '了解', '掌握', '精通', '具备', '能力', '工作',
    '项目', '经验', '开发', '设计', '测试', '管理', '分析',
    '优化', '维护', '以上', '相关', '良好', '较强', '熟练',
    '技术', '系统', '平台', '框架', '工具', '语言',
}


# 薪资月数正则：匹配 "·16薪" / "·14薪" 等
_SALARY_MONTHS_RE = re.compile(r'[·・•]\s*(\d{1,2})\s*薪')

# HTML 标签正则
_HTML_TAG_RE = re.compile(r'<[^>]+>')
# 连续空白正则
_WHITESPACE_RE = re.compile(r'\s+')

# 别名映射缓存：key 为词典文件的绝对路径（或 '__builtin__'），避免多城市重复解析
_ALIAS_MAP_CACHE: Dict[str, Dict[str, str]] = {}

# 回退用的内置别名映射（当 SkillDictionary 不可用时使用）
_BUILTIN_ALIAS_MAP: Dict[str, str] = {
    'js': 'JavaScript', 'javascript': 'JavaScript',
    'ts': 'TypeScript', 'typescript': 'TypeScript',
    'py': 'Python', 'python': 'Python',
    'vue': 'Vue.js', 'vue.js': 'Vue.js', 'vue3': 'Vue.js',
    'react': 'React', 'reactjs': 'React', 'react.js': 'React',
    'node': 'Node.js', 'nodejs': 'Node.js', 'node.js': 'Node.js',
    'mysql': 'MySQL', 'postgresql': 'PostgreSQL', 'pg': 'PostgreSQL',
    'mongo': 'MongoDB', 'mongodb': 'MongoDB',
    'redis': 'Redis', 'docker': 'Docker',
    'k8s': 'Kubernetes', 'kubernetes': 'Kubernetes',
    'git': 'Git', 'linux': 'Linux', 'java': 'Java',
    'golang': 'Go', 'go语言': 'Go',
    'c++': 'C++', 'cpp': 'C++',
    'c#': 'C#', 'csharp': 'C#',
    '.net': '.NET', 'dotnet': '.NET',
    'spring': 'Spring', 'springboot': 'Spring Boot',
    'spring boot': 'Spring Boot', 'springcloud': 'Spring Cloud',
    'spring cloud': 'Spring Cloud',
    'hadoop': 'Hadoop', 'spark': 'Spark',
    'tensorflow': 'TensorFlow', 'pytorch': 'PyTorch',
    'scikit-learn': 'scikit-learn', 'sklearn': 'scikit-learn',
    'pandas': 'Pandas', 'numpy': 'NumPy',
    'es': 'Elasticsearch', 'elasticsearch': 'Elasticsearch',
    'kafka': 'Kafka', 'rabbitmq': 'RabbitMQ', 'nginx': 'Nginx',
    'aws': 'AWS', 'azure': 'Azure',
    'html': 'HTML', 'html5': 'HTML5',
    'css': 'CSS', 'css3': 'CSS3',
    'sass': 'Sass', 'less': 'Less',
    'webpack': 'Webpack', 'vite': 'Vite',
    'flutter': 'Flutter', 'swift': 'Swift', 'kotlin': 'Kotlin',
    'android': 'Android', 'ios': 'iOS',
    'uniapp': 'uni-app', 'uni-app': 'uni-app',
    'miniprogram': '微信小程序', '小程序': '微信小程序', 'wechat': '微信小程序',
    'restful': 'RESTful API', 'rest': 'RESTful API', 'api': 'API',
    'graphql': 'GraphQL', 'grpc': 'gRPC',
    'ci/cd': 'CI/CD', 'cicd': 'CI/CD',
    'devops': 'DevOps', 'agile': '敏捷开发', '敏捷': '敏捷开发',
    'scrum': 'Scrum', 'nlp': 'NLP',
    'llm': 'LLM', 'aigc': 'AIGC', 'rag': 'RAG',
}


class JobDataCleaner:
    """招聘数据清洗器"""

    def __init__(self, config: Dict = None, skill_dict_path: str = None):
        """
        Args:
            config: 清洗配置，None 使用默认配置
            skill_dict_path: skill_taxonomy.json 路径，用于技能别名归一化。
                             None 时自动探测项目内路径，找不到则回退内置映射。
        """
        self.config = config or self.get_default_config()
        self.stats = {
            'total': 0,
            'removed_missing_required': 0,
            'removed_empty_skills': 0,
            'removed_salary_issues': 0,
            'removed_duplicates': 0,
            'removed_invalid_experience': 0,
            'removed_invalid_education': 0,
            'normalized_salary': 0,
            'skills_deduped': 0,
            'skills_dict_normalized': 0,    # 通过 SkillDictionary 规范化的技能次数
            'cleaned': 0,
        }
        self.seen_jobs: set = set()

        # 初始化技能别名映射
        self._alias_map: Dict[str, str] = self._build_alias_map(skill_dict_path)

    # ─────────────────── 配置 ───────────────────

    @staticmethod
    def get_default_config() -> Dict:
        """获取默认清洗配置"""
        return {
            # 薪资范围（单位：K/月）
            'salary_min_threshold': 1,
            'salary_max_threshold': 200,
            # 是否保留 skills 为空的数据
            'keep_empty_skills': False,
            # 是否启用技能别名归一化
            'normalize_skills': True,
            # 是否标准化薪资（处理实习日薪等）
            'normalize_salary': True,
            # 是否预构建 jd_text 字段（供 Neo4j 导入和 enhance 步骤使用）
            'build_jd_text': True,
            # 是否剔除爬虫内部字段 _raw（下游无用，减少文件体积）
            'strip_raw': True,
            # 去重策略
            'dedup_by': ['job_id', 'title_company_city'],
            # 合法的经验要求关键词（None = 不过滤）
            'valid_experience_keywords': None,
            # 合法的学历要求关键词（None = 不过滤）
            'valid_education_keywords': None,
        }

    # ─────────────────── 技能别名映射初始化 ───────────────────

    def _build_alias_map(self, skill_dict_path: Optional[str]) -> Dict[str, str]:
        """
        优先使用项目的 SkillDictionary（skill_taxonomy.json）构建别名映射，
        保持与 Neo4j 导入侧（neo4j_importer._build_alias_map）完全一致。
        找不到词典文件时回退到内置映射。
        结果缓存在模块级 _ALIAS_MAP_CACHE，多城市批量清洗只读一次文件。
        """
        # 尝试自动探测词典路径，并转为规范绝对路径用作缓存 key
        if skill_dict_path is None:
            project_root = Path(__file__).resolve().parent.parent.parent
            candidate = project_root / 'data' / 'skill_dict' / 'skill_taxonomy.json'
            skill_dict_path = str(candidate) if candidate.exists() else None

        cache_key = str(Path(skill_dict_path).resolve()) if skill_dict_path else '__builtin__'

        if cache_key in _ALIAS_MAP_CACHE:
            logger.debug(f"技能别名映射命中缓存（key: {cache_key}）")
            return _ALIAS_MAP_CACHE[cache_key]

        if skill_dict_path and Path(skill_dict_path).exists():
            try:
                alias_map: Dict[str, str] = {}
                with open(skill_dict_path, 'r', encoding='utf-8') as f:
                    taxonomy = json.load(f)
                for skills_list in taxonomy.get('技能分类体系', {}).values():
                    for skill_info in skills_list:
                        std_name = skill_info['name']
                        alias_map[std_name.lower()] = std_name
                        for alias in skill_info.get('aliases', []):
                            alias_map[alias.lower()] = std_name
                logger.info(f"技能别名映射已从词典加载，共 {len(alias_map)} 条（{skill_dict_path}）")
                _ALIAS_MAP_CACHE[cache_key] = alias_map
                return alias_map
            except Exception as e:
                logger.warning(f"加载技能词典失败，回退到内置映射: {e}")

        builtin = dict(_BUILTIN_ALIAS_MAP)
        logger.info(f"使用内置技能别名映射（{len(builtin)} 条）")
        _ALIAS_MAP_CACHE[cache_key] = builtin
        return builtin

    # ─────────────────── 主流程 ───────────────────

    def _reset_state(self):
        """重置统计和去重状态，允许同一实例多次调用 clean_dataset"""
        for key in self.stats:
            self.stats[key] = 0
        self.seen_jobs.clear()

    def clean_dataset(self, input_file: Path, output_file: Path) -> Dict:
        """清洗数据集，返回统计信息"""
        self._reset_state()
        logger.info(f"开始清洗数据: {input_file}")

        with open(input_file, 'r', encoding='utf-8') as f:
            jobs = json.load(f)

        self.stats['total'] = len(jobs)

        cleaned_jobs = []
        for job in jobs:
            if self.is_valid_job(job):
                cleaned_job = self.clean_job(job)
                if cleaned_job:
                    cleaned_jobs.append(cleaned_job)

        self.stats['cleaned'] = len(cleaned_jobs)

        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(cleaned_jobs, f, ensure_ascii=False, indent=2)

        total = self.stats['total']
        logger.info(f"清洗完成: {input_file.name}")
        if total > 0:
            logger.info(f"  原始: {total} 条  →  清洗后: {self.stats['cleaned']} 条"
                        f"  保留率: {self.stats['cleaned'] / total * 100:.2f}%")
        else:
            logger.warning(f"  原始文件为空: {input_file.name}")
        # 返回副本，防止调用方持有引用后被 _reset_state() 清零
        return dict(self.stats)

    # ─────────────────── 过滤逻辑 ───────────────────

    def is_valid_job(self, job: Dict) -> bool:
        """判断岗位是否有效（过滤阶段）"""
        # 1. 必填字段
        if not job.get('title', '').strip() or not job.get('company', '').strip():
            self.stats['removed_missing_required'] += 1
            return False

        # 2. skills 为空
        if not self.config['keep_empty_skills']:
            if not job.get('skills'):
                self.stats['removed_empty_skills'] += 1
                return False

        # 3. 薪资合法性
        if not self._is_valid_salary(job):
            self.stats['removed_salary_issues'] += 1
            return False

        # 4. 去重
        if not self._is_unique_job(job):
            self.stats['removed_duplicates'] += 1
            return False

        # 5. 经验要求（可选）
        if not self._is_valid_field(
            job.get('experience', ''),
            self.config.get('valid_experience_keywords'),
        ):
            self.stats['removed_invalid_experience'] += 1
            return False

        # 6. 学历要求（可选）
        if not self._is_valid_field(
            job.get('education', ''),
            self.config.get('valid_education_keywords'),
        ):
            self.stats['removed_invalid_education'] += 1
            return False

        return True

    def _is_valid_salary(self, job: Dict) -> bool:
        """检查薪资是否有效（单位：K/月）"""
        salary_min = job.get('salary_min', 0)
        salary_max = job.get('salary_max', 0)
        if not isinstance(salary_min, (int, float)) or not isinstance(salary_max, (int, float)):
            return False
        if salary_min <= 0 or salary_max <= 0:
            return False
        if salary_min > salary_max:
            return False
        if (salary_min < self.config['salary_min_threshold'] or
                salary_max > self.config['salary_max_threshold']):
            return False
        return True

    def _is_unique_job(self, job: Dict) -> bool:
        """检查岗位是否重复"""
        job_id = job.get('job_id')
        if job_id and job_id in self.seen_jobs:
            return False
        dedup_key = self._generate_dedup_key(job)
        if dedup_key in self.seen_jobs:
            return False
        if job_id:
            self.seen_jobs.add(job_id)
        self.seen_jobs.add(dedup_key)
        return True

    def _generate_dedup_key(self, job: Dict) -> str:
        """title + company + city 的 MD5"""
        title = _WHITESPACE_RE.sub('', job.get('title', '')).lower()
        company = _WHITESPACE_RE.sub('', job.get('company', '')).lower()
        city = job.get('city', '').strip().lower()
        return hashlib.md5(f"{title}_{company}_{city}".encode()).hexdigest()

    @staticmethod
    def _is_valid_field(value: str, keywords: Optional[List[str]]) -> bool:
        if keywords is None:
            return True
        if not value:
            return True
        return any(kw in value for kw in keywords)

    # ─────────────────── 标准化逻辑 ───────────────────

    def clean_job(self, job: Dict) -> Dict:
        """清洗单条岗位数据（标准化阶段）"""
        cleaned = job.copy()

        # 1. 剔除 _raw（爬虫内部元数据，下游无用）
        if self.config.get('strip_raw', True):
            cleaned.pop('_raw', None)

        # 2. 公司名标准化
        if 'company' in cleaned:
            cleaned['company'] = self._normalize_company_name(cleaned['company'])

        # 3. 城市名标准化（去"市"后缀，统一为简称）
        if 'city' in cleaned:
            cleaned['city'] = self._normalize_city(cleaned['city'])

        # 4. 职位名称清洗
        if 'title' in cleaned:
            cleaned['title'] = self._clean_text(cleaned['title'])

        # 5. 文本描述字段去 HTML / 多余空白
        for field in ('description', 'job_detail', 'responsibilities', 'requirements'):
            if cleaned.get(field):
                cleaned[field] = self._clean_text(cleaned[field])

        # 6. skills 深度清洗（过滤 + 别名归一 + 去重）
        if 'skills' in cleaned:
            before = len(cleaned['skills'])
            cleaned['skills'], dict_norm_count = self._clean_skills(cleaned['skills'])
            self.stats['skills_deduped'] += max(0, before - len(cleaned['skills']))
            self.stats['skills_dict_normalized'] += dict_norm_count

        # 7. welfare 清洗（去空、去重、去 HTML）
        if 'welfare' in cleaned:
            cleaned['welfare'] = self._clean_welfare(cleaned['welfare'])

        # 8. 薪资：提取 salary_months + 实习日薪换算
        cleaned = self._process_salary(cleaned)

        # 9. publish_date 格式验证与修复
        if 'publish_date' in cleaned:
            cleaned['publish_date'] = self._normalize_date(cleaned['publish_date'])

        # 10. 预构建 jd_text（供 Neo4j 导入和 enhance 步骤直接使用）
        if self.config.get('build_jd_text', True):
            cleaned['jd_text'] = self._build_jd_text(cleaned)

        # 11. 清洗标记
        cleaned['_cleaned'] = True
        cleaned['_cleaned_at'] = datetime.now().isoformat()

        return cleaned

    # ─────────────────── 字段级清洗方法 ───────────────────

    @staticmethod
    def _clean_text(text: str) -> str:
        """去除 HTML 标签，统一空白字符"""
        if not text:
            return text
        text = _HTML_TAG_RE.sub(' ', text)
        return _WHITESPACE_RE.sub(' ', text).strip()

    @staticmethod
    def _normalize_company_name(company: str) -> str:
        """标准化公司名称：去多余空白、去末尾括号内容"""
        company = _WHITESPACE_RE.sub(' ', company).strip()
        # 去除末尾括号内容（半角/全角），如 "XX科技(上海)" → "XX科技"
        company = re.sub(r'\s*[(\（][^)）]{1,20}[)）]\s*$', '', company).strip()
        return company

    @staticmethod
    def _normalize_city(city: str) -> str:
        """
        城市名标准化：去尾部"市"字，统一为简称，与图谱节点保持一致。
        如 "北京市" → "北京"，"杭州市" → "杭州"，"东莞市" → "东莞"。
        len > 2 防止 "市" 这种单字城市被误截。
        """
        city = city.strip()
        if city.endswith('市') and len(city) > 2:
            city = city[:-1]
        return city

    def _clean_skills(self, skills: List[str]) -> Tuple[List[str], int]:
        """
        技能列表深度清洗：过滤 + 别名归一 + 去重。
        Returns:
            (cleaned_list, dict_normalized_count)
        """
        if not skills:
            return [], 0

        seen: set = set()
        result: List[str] = []
        dict_norm_count = 0

        for skill in skills:
            skill = _HTML_TAG_RE.sub('', skill).strip()
            if not skill or len(skill) > 30:
                continue
            # 含全角标点或控制字符，无效
            if re.search(r'[，。！？；：""''【】\n\r\t]', skill):
                continue
            # 纯通用词
            if skill in INVALID_SKILL_TOKENS:
                continue

            # 别名归一化（优先使用 SkillDictionary，否则内置映射）
            if self.config.get('normalize_skills', True):
                normalized = self._alias_map.get(skill.lower())
                if normalized and normalized != skill:
                    dict_norm_count += 1
                    skill = normalized

            # 去重
            skill_lower = skill.lower()
            if skill_lower in seen:
                continue
            seen.add(skill_lower)
            result.append(skill)

        return result, dict_norm_count

    @staticmethod
    def _clean_welfare(welfare) -> List[str]:
        """福利列表清洗：去 HTML、strip、去空、去重"""
        if not welfare:
            return []
        if isinstance(welfare, str):
            welfare = [welfare]
        seen: set = set()
        result: List[str] = []
        for item in welfare:
            item = _HTML_TAG_RE.sub('', str(item)).strip()
            if not item or item.lower() in seen:
                continue
            seen.add(item.lower())
            result.append(item)
        return result

    def _process_salary(self, job: Dict) -> Dict:
        """
        薪资处理：
        1. 从 salary_text 提取 salary_months（如 "20-30K·16薪" → 16）
        2. 实习日薪换算（salary_min/max < 1K 且 title 含"实习"）
        """
        # 提取薪资月数
        salary_text = job.get('salary_text', '')
        if salary_text and 'salary_months' not in job:
            m = _SALARY_MONTHS_RE.search(salary_text)
            if m:
                job['salary_months'] = int(m.group(1))

        # 日薪/时薪换算为月薪（统一单位为 K/月）
        if self.config.get('normalize_salary', True):
            salary_min = job.get('salary_min', 0)
            salary_max = job.get('salary_max', 0)
            if '元/时' in salary_text and salary_min > 1:
                # 150元/时 × 8小时 × 22天 / 1000 = 26.4K/月
                job['salary_min'] = round(salary_min * 8 * 22 / 1000, 2)
                job['salary_max'] = round(salary_max * 8 * 22 / 1000, 2)
                job['_salary_normalized'] = 'hourly_yuan_to_monthly_k'
                self.stats['normalized_salary'] += 1
            elif '元/天' in salary_text and salary_min > 1:
                # 190元/天 × 22天 / 1000 = 4.18K/月
                job['salary_min'] = round(salary_min * 22 / 1000, 2)
                job['salary_max'] = round(salary_max * 22 / 1000, 2)
                job['_salary_normalized'] = 'daily_yuan_to_monthly_k'
                self.stats['normalized_salary'] += 1
            elif (0 < salary_max < 1) and '实习' in job.get('title', ''):
                # 兼容旧格式：日薪以 K 分之一存储（0.19K/天）
                job['salary_min'] = round(salary_min * 22, 1)
                job['salary_max'] = round(salary_max * 22, 1)
                job['_salary_normalized'] = 'daily_k_to_monthly_k'
                self.stats['normalized_salary'] += 1

        return job

    @staticmethod
    def _normalize_date(date_str: str) -> str:
        """
        验证并修复 publish_date 格式，统一为 YYYY-MM-DD。
        无法解析时返回原值。
        """
        if not date_str:
            return date_str
        for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%Y%m%d', '%Y.%m.%d'):
            try:
                return datetime.strptime(date_str.strip(), fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
        return date_str

    @staticmethod
    def _build_jd_text(job: Dict) -> str:
        """
        预构建 JD 文本，与 enhance_with_qwen3.build_jd_text_from_job 保持一致。
        Neo4j _create_job_node 读取 jd_text 字段，此处提前生成可避免重复计算。
        """
        parts = []
        if job.get('title'):
            parts.append(f"岗位：{job['title']}")
        if job.get('salary_text'):
            parts.append(f"薪资：{job['salary_text']}")
        requirements = []
        if job.get('experience'):
            requirements.append(f"经验：{job['experience']}")
        if job.get('education'):
            requirements.append(f"学历：{job['education']}")
        if requirements:
            parts.append("要求：" + "，".join(requirements))
        if job.get('skills'):
            parts.append(f"技能：{'、'.join(job['skills'])}")
        if job.get('welfare'):
            welfare_list = job['welfare'] if isinstance(job['welfare'], list) else [job['welfare']]
            parts.append(f"福利：{'、'.join(welfare_list[:5])}")
        if job.get('description'):
            parts.append(f"描述：{job['description'][:500]}")
        return '\n'.join(parts)

    # ─────────────────── 报告 ───────────────────

    def generate_report(self) -> str:
        """生成清洗报告"""
        total = self.stats['total']
        if total == 0:
            return "暂无数据"

        def pct(n: int) -> str:
            return f"{n / total * 100:.2f}%"

        return (
            f"=== 数据清洗报告 ===\n"
            f"总数据量:   {total:,}\n"
            f"清洗后:     {self.stats['cleaned']:,}\n"
            f"保留率:     {self.stats['cleaned'] / total * 100:.2f}%\n"
            f"\n移除原因:\n"
            f"  必填字段缺失:  {self.stats['removed_missing_required']:,} ({pct(self.stats['removed_missing_required'])})\n"
            f"  skills 为空:   {self.stats['removed_empty_skills']:,} ({pct(self.stats['removed_empty_skills'])})\n"
            f"  薪资异常:      {self.stats['removed_salary_issues']:,} ({pct(self.stats['removed_salary_issues'])})\n"
            f"  重复数据:      {self.stats['removed_duplicates']:,} ({pct(self.stats['removed_duplicates'])})\n"
            f"  经验无效:      {self.stats['removed_invalid_experience']:,} ({pct(self.stats['removed_invalid_experience'])})\n"
            f"  学历无效:      {self.stats['removed_invalid_education']:,} ({pct(self.stats['removed_invalid_education'])})\n"
            f"\n数据处理:\n"
            f"  薪资标准化:    {self.stats['normalized_salary']:,}\n"
            f"  skills 去重:   {self.stats['skills_deduped']:,} 条次\n"
            f"  技能规范化:    {self.stats['skills_dict_normalized']:,} 条次（来自词典）"
        )


# ─────────────────── 向后兼容入口 ───────────────────

def clean_all_cities():
    """清洗所有城市的数据（向后兼容入口，自动探测 data/raw/ 下所有 boss_*.json）"""
    project_root = Path(__file__).parent.parent.parent
    raw_dir = project_root / 'data' / 'raw'
    cleaned_dir = project_root / 'data' / 'cleaned'

    input_files = sorted(raw_dir.glob('boss_*.json'))
    if not input_files:
        logger.warning(f"data/raw/ 下未找到任何 boss_*.json 文件")
        return

    all_stats = []
    cleaner = JobDataCleaner()   # 单实例，clean_dataset 内部会自动 reset

    for input_file in input_files:
        city = input_file.stem.replace('boss_', '')
        output_file = cleaned_dir / f'boss_{city}_cleaned.json'
        try:
            stats = cleaner.clean_dataset(input_file, output_file)
            stats['city'] = city
            print(f"\n{city}:")
            print(cleaner.generate_report())
        except Exception as e:
            logger.error(f"清洗 {input_file.name} 失败: {e}", exc_info=True)
            stats = {'city': city, 'error': str(e), 'total': 0, 'cleaned': 0}
        all_stats.append(stats)

    if not all_stats:
        return

    print("\n" + "=" * 50)
    total_all = sum(s['total'] for s in all_stats)
    cleaned_all = sum(s['cleaned'] for s in all_stats)
    retention = f"{cleaned_all / total_all * 100:.2f}%" if total_all else "N/A"
    print(f"=== 全部城市汇总 ===\n总数据量: {total_all:,}  清洗后: {cleaned_all:,}"
          f"  总保留率: {retention}")

    summary_file = cleaned_dir / 'cleaning_summary.json'
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            'cleaned_at': datetime.now().isoformat(),
            'cities': all_stats,
            'total': {
                'total': total_all,
                'cleaned': cleaned_all,
                'retention_rate': cleaned_all / total_all if total_all else 0,
            },
        }, f, ensure_ascii=False, indent=2)

    print(f"\n清洗完成！数据: {cleaned_dir}  统计: {summary_file}")


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
    clean_all_cities()
