"""
混合技能抽取器: 规则匹配 + Qwen3本地模型增强
这是项目的核心创新点之一

技术栈: Qwen3-7B本地部署 + vLLM高性能推理
"""
import logging
from typing import List, Dict, Set, Optional
from pathlib import Path
import sys

# 添加项目根目录到path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.nlp.skill_extractor import SkillExtractor

logger = logging.getLogger(__name__)


class HybridSkillExtractor:
    """
    混合技能抽取器
    
    结合规则匹配和LLM，提升技能抽取准确率
    
    工作流程:
    1. 规则抽取（基于skill_taxonomy.json，快速、准确）
    2. LLM增强（从JD文本提取遗漏的技能，覆盖面广）
    3. 合并去重（智能合并，避免重复）
    
    优势:
    - 准确率高：规则抽取的置信度高
    - 覆盖面广：LLM能发现规则遗漏的技能
    - 成本可控：只对有JD文本的岗位调用LLM
    """
    
    def __init__(
        self, 
        skill_dict_path: str = "data/skill_dict/skill_taxonomy.json",
        use_llm: bool = True,
        llm_model: Optional[str] = None
    ):
        """
        初始化混合抽取器
        
        Args:
            skill_dict_path: 技能词典路径
            use_llm: 是否使用Qwen3本地模型（默认True）
            llm_model: LLM模型名称（默认"Qwen/Qwen3-7B-Instruct"）
        """
        from src.graph_builder.skill_dictionary import SkillDictionary
        
        logger.info("="*80)
        logger.info("🔧 初始化混合技能抽取器")
        logger.info("="*80)
        
        # 加载技能词典
        logger.info(f"⏳ 加载技能词典: {skill_dict_path}")
        self.skill_dict = SkillDictionary(skill_dict_path)
        logger.info(f"✅ 技能词典加载完成")
        
        # 初始化规则抽取器
        self.rule_extractor = SkillExtractor(self.skill_dict)
        logger.info(f"✅ 规则抽取器初始化完成")
        
        # 初始化Qwen3本地模型
        self.llm_client = None
        self.llm_available = False
        self.llm_framework = None
        
        if use_llm:
            # 优先使用全局单例（已加载的 vLLM 实例），避免重复占用显存
            try:
                from src.llm.qwen3_local_client import get_qwen3_client
                logger.info("⏳ 获取 Qwen3 全局单例（vLLM）...")
                model_name = llm_model or "Qwen/Qwen2.5-1.5B-Instruct"
                self.llm_client = get_qwen3_client(model_name=model_name)
                self.llm_available = True
                self.llm_framework = "vLLM"
                logger.info("✅ Qwen3本地模型就绪（vLLM 单例）")
            except Exception as e:
                logger.warning(f"⚠️  vLLM单例获取失败: {e}")

                # 降级到Transformers版本（Windows兼容）
                try:
                    from src.llm.qwen3_transformers_client import Qwen3TransformersClient
                    logger.info("⏳ 降级到Transformers版本...")
                    model_name = llm_model or "Qwen/Qwen2.5-1.5B-Instruct"
                    self.llm_client = Qwen3TransformersClient(model_name=model_name)
                    self.llm_available = True
                    self.llm_framework = "Transformers"
                    logger.info("✅ Qwen3本地模型初始化成功（Transformers）")
                    logger.info("💡 提示: Transformers版本较慢，建议使用WSL2+vLLM")
                except Exception as e2:
                    logger.warning(f"⚠️  Transformers版本不可用（{e2}），将只使用规则抽取")
        else:
            logger.info("ℹ️  LLM模式: 禁用")
        
        # 获取所有已知技能名称（用于LLM参考）
        self.known_skills = [skill['name'] for skill in self.skill_dict.all_skills]
        
        logger.info("="*80)
        logger.info(f"✅ 混合技能抽取器初始化完成")
        logger.info(f"   规则抽取: 启用")
        logger.info(f"   Qwen3本地: {'启用' if self.llm_available else '禁用'}")
        if self.llm_available:
            logger.info(f"   推理框架: {self.llm_framework}")
        logger.info("="*80)
    
    def extract(self, job: Dict, use_llm: bool = True) -> Dict:
        """
        提取技能（混合方法）
        
        Args:
            job: 岗位信息，包含title, skills, jd_text等
            use_llm: 是否使用LLM增强（默认True）
            
        Returns:
            {
                'rule_skills': [...],      # 规则匹配结果
                'llm_skills': [...],       # LLM提取结果
                'merged_skills': [...],    # 合并去重后结果
                'confidence': {...},       # 每个技能的置信度
                'method': 'hybrid'|'rule'  # 使用的方法
            }
        """
        # 1. 规则抽取（始终执行）
        rule_result = self.rule_extractor.extract_from_job(job)
        rule_skills = [s['name'] for s in rule_result]
        rule_skills_info = {s['name']: s for s in rule_result}
        
        # 2. LLM增强（可选）
        llm_skills = []
        if use_llm and self.llm_available and job.get('jd_text'):
            try:
                llm_skills = self._llm_extract(job['jd_text'])
                logger.debug(f"LLM提取技能: {llm_skills}")
            except Exception as e:
                logger.warning(f"LLM提取失败: {e}")
                llm_skills = []
        
        # 3. 合并去重
        merged, confidence = self._merge_skills(
            rule_skills,
            rule_skills_info,
            llm_skills
        )
        
        # 4. 构建返回结果
        merged_skills_detail = []
        for skill_name in merged:
            if skill_name in rule_skills_info:
                skill_info = rule_skills_info[skill_name]
                skill_info['confidence'] = confidence.get(skill_name, 0.9)
                merged_skills_detail.append(skill_info)
            else:
                # LLM提取的新技能
                merged_skills_detail.append({
                    'name': skill_name,
                    'source': 'llm',
                    'confidence': confidence.get(skill_name, 0.7),
                    'skill_info': {'name': skill_name}
                })
        
        return {
            'rule_skills': rule_result,
            'llm_skills': llm_skills,
            'merged_skills': merged_skills_detail,
            'confidence': confidence,
            'method': 'hybrid' if (use_llm and self.llm_available and llm_skills) else 'rule',
            'stats': {
                'rule_count': len(rule_skills),
                'llm_count': len(llm_skills),
                'merged_count': len(merged),
                'new_from_llm': len(set(llm_skills) - set(rule_skills))
            }
        }
    
    def _llm_extract(self, jd_text: str) -> List[str]:
        """
        使用Qwen3本地模型提取技能
        
        Args:
            jd_text: 职位描述文本
            
        Returns:
            提取的技能列表
        """
        if not self.llm_client:
            return []
        
        try:
            # Qwen3本地模型
            skills = self.llm_client.extract_skills_from_jd(
                jd_text,
                known_skills=self.known_skills,
                temperature=0.1
            )
            return skills
        except Exception as e:
            logger.error(f"Qwen3提取失败: {e}")
            return []
    
    def _merge_skills(
        self,
        rule_skills: List[str],
        rule_skills_info: Dict,
        llm_skills: List[str]
    ) -> tuple[List[str], Dict[str, float]]:
        """
        合并规则和LLM提取的技能
        
        Args:
            rule_skills: 规则抽取的技能列表
            rule_skills_info: 规则抽取的详细信息
            llm_skills: LLM抽取的技能列表
            
        Returns:
            (合并后的技能列表, 置信度字典)
        """
        merged = []
        confidence = {}
        
        # 1. 添加规则匹配的技能（置信度高）
        for skill_name in rule_skills:
            merged.append(skill_name)
            skill_info = rule_skills_info.get(skill_name, {})
            confidence[skill_name] = skill_info.get('confidence', 0.9)
        
        # 2. 添加LLM提取的新技能（不在规则结果中）
        for skill_name in llm_skills:
            # 检查是否已存在（不区分大小写）
            if not self._skill_exists(skill_name, merged):
                # 验证是否在已知技能库中
                if skill_name in self.known_skills:
                    merged.append(skill_name)
                    confidence[skill_name] = 0.75  # LLM提取置信度稍低
                else:
                    # 模糊匹配（处理大小写、空格等差异）
                    matched_skill = self._fuzzy_match_skill(skill_name)
                    if matched_skill and not self._skill_exists(matched_skill, merged):
                        merged.append(matched_skill)
                        confidence[matched_skill] = 0.7
        
        return merged, confidence
    
    def _skill_exists(self, skill_name: str, skill_list: List[str]) -> bool:
        """检查技能是否已存在（不区分大小写）"""
        skill_lower = skill_name.lower().strip()
        return any(s.lower().strip() == skill_lower for s in skill_list)
    
    def _fuzzy_match_skill(self, skill_name: str) -> str:
        """模糊匹配技能名称"""
        skill_lower = skill_name.lower().strip()
        
        # 在已知技能中查找
        for known_skill in self.known_skills:
            if known_skill.lower().strip() == skill_lower:
                return known_skill
            # 包含关系
            if skill_lower in known_skill.lower() or known_skill.lower() in skill_lower:
                return known_skill
        
        return None
    
    def batch_extract(
        self,
        jobs: List[Dict],
        use_llm: bool = True,
        update_jobs: bool = True,
        batch_size: int = 32
    ) -> List[Dict]:
        """
        批量提取技能（支持Qwen3高性能批处理）
        
        Args:
            jobs: 岗位列表
            use_llm: 是否使用Qwen3增强
            update_jobs: 是否更新jobs的skills字段
            batch_size: 批处理大小
            
        Returns:
            处理后的岗位列表
        """
        logger.info(f"开始批量提取技能，共 {len(jobs)} 个岗位")
        logger.info(f"模式: {'混合(规则+Qwen3)' if use_llm else '仅规则'}")
        
        # 如果使用Qwen3且可用，使用批处理优化
        if use_llm and self.llm_available:
            return self._batch_extract_with_qwen3(jobs, update_jobs, batch_size)
        
        # 否则逐条处理
        for i, job in enumerate(jobs):
            try:
                result = self.extract(job, use_llm=use_llm)
                
                if update_jobs:
                    # 更新skills字段
                    skill_names = [s['name'] for s in result['merged_skills']]
                    job['skills'] = skill_names
                    
                    # 添加详细信息
                    job['_extraction_result'] = result
                
                if (i + 1) % 100 == 0:
                    logger.info(f"已处理 {i + 1}/{len(jobs)} ({(i+1)/len(jobs)*100:.1f}%)")
                    
            except Exception as e:
                logger.error(f"处理岗位失败 {job.get('job_id', 'unknown')}: {e}")
                continue
        
        logger.info(f"批量提取完成")
        return jobs
    
    def _batch_extract_with_qwen3(
        self,
        jobs: List[Dict],
        update_jobs: bool,
        batch_size: int
    ) -> List[Dict]:
        """使用Qwen3批处理优化"""
        logger.info(f"🚀 使用Qwen3批处理模式（batch_size={batch_size}）")
        
        # 1. 规则抽取（快速）
        logger.info("⏳ [1/3] 规则抽取...")
        try:
            from tqdm import tqdm
            iterator = tqdm(jobs, desc="规则抽取", unit="条")
        except ImportError:
            iterator = jobs
            total = len(jobs)
        
        for i, job in enumerate(iterator, 1):
            rule_result = self.rule_extractor.extract_from_job(job)
            job['_rule_skills'] = [s['name'] for s in rule_result]
            job['_rule_skills_info'] = {s['name']: s for s in rule_result}
            
            # 如果没有tqdm，每100条输出一次进度
            if not hasattr(iterator, '__class__') or 'tqdm' not in str(iterator.__class__):
                if i % 100 == 0 or i == total:
                    logger.info(f"   进度: {i}/{total} ({i/total*100:.1f}%)")
        
        logger.info("✅ 规则抽取完成")
        
        # 2. Qwen3批量提取
        logger.info(f"⏳ [2/3] Qwen3批量提取...")
        jd_texts = [job.get('jd_text', '') for job in jobs]
        
        # 统计有效JD数量
        valid_jd_count = sum(1 for jd in jd_texts if jd and len(jd.strip()) > 10)
        logger.info(f"   有效JD文本: {valid_jd_count}/{len(jd_texts)} 条")
        
        all_llm_skills = self.llm_client.batch_extract_skills(
            jd_texts,
            known_skills=self.known_skills,
            batch_size=batch_size,
            show_progress=True
        )
        logger.info("✅ Qwen3批量提取完成")
        
        # 3. 合并结果
        logger.info("⏳ [3/3] 合并结果...")
        try:
            from tqdm import tqdm
            merge_iterator = tqdm(enumerate(jobs), total=len(jobs), desc="合并结果", unit="条")
        except ImportError:
            merge_iterator = enumerate(jobs)
        
        for i, job in merge_iterator:
            try:
                rule_skills = job.get('_rule_skills', [])
                rule_skills_info = job.get('_rule_skills_info', {})
                llm_skills = all_llm_skills[i] if i < len(all_llm_skills) else []
                
                # 合并
                merged, confidence = self._merge_skills(
                    rule_skills,
                    rule_skills_info,
                    llm_skills
                )
            except Exception as e:
                logger.error(f"合并技能失败 (job {i}): {e}")
                merged = rule_skills  # 降级到只使用规则提取的结果
                confidence = {s: 0.9 for s in merged}
            
            # 构建详细结果
            merged_skills_detail = []
            for skill_name in merged:
                if skill_name in rule_skills_info:
                    skill_info = rule_skills_info[skill_name]
                    skill_info['confidence'] = confidence.get(skill_name, 0.9)
                    merged_skills_detail.append(skill_info)
                else:
                    merged_skills_detail.append({
                        'name': skill_name,
                        'source': 'llm',
                        'confidence': confidence.get(skill_name, 0.7),
                        'skill_info': {'name': skill_name}
                    })
            
            if update_jobs:
                job['skills'] = [s['name'] for s in merged_skills_detail]
                job['_extraction_result'] = {
                    'rule_skills': job.get('_rule_skills', []),
                    'llm_skills': llm_skills,
                    'merged_skills': merged_skills_detail,
                    'method': 'hybrid',
                    'stats': {
                        'rule_count': len(rule_skills),
                        'llm_count': len(llm_skills),
                        'merged_count': len(merged),
                        'new_from_llm': len(set(llm_skills) - set(rule_skills))
                    }
                }
            
            # 清理临时字段
            job.pop('_rule_skills', None)
            job.pop('_rule_skills_info', None)
        
        logger.info("✅ 合并完成")
        
        return jobs
    
    def get_all_skill_names(self) -> List[str]:
        """获取所有已知技能名称"""
        return self.known_skills


# 测试代码
def test_hybrid_extractor():
    """测试混合技能抽取器"""
    print("="*80)
    print("测试混合技能抽取器")
    print("="*80)
    
    # 初始化抽取器
    extractor = HybridSkillExtractor()
    
    # 测试用例
    test_jobs = [
        {
            'job_id': 'test_1',
            'title': 'Python后端开发工程师',
            'skills': ['Python', 'Django'],  # 显式标注的技能
            'jd_text': '''
岗位职责:
1. 负责后端服务开发，使用Python和Django框架
2. 熟练使用MySQL数据库，有Redis缓存使用经验
3. 了解Docker容器化部署，有Kubernetes经验优先
4. 参与系统架构设计和技术选型

任职要求:
1. 3年以上Python开发经验
2. 熟悉RESTful API设计
3. 熟悉Git版本控制
4. 良好的代码规范和文档习惯
            '''
        },
        {
            'job_id': 'test_2',
            'title': '前端开发工程师(React)',
            'skills': ['JavaScript', 'React'],
            'jd_text': '''
岗位要求:
- 精通JavaScript, TypeScript
- 熟练使用React, Redux
- 了解Webpack, Babel配置
- 有Vue.js经验加分
- 熟悉ES6+新特性
            '''
        }
    ]
    
    for job in test_jobs:
        print(f"\n{'='*80}")
        print(f"📋 岗位: {job['title']}")
        print(f"💼 Job ID: {job['job_id']}")
        print(f"📝 显式技能: {job['skills']}")
        print(f"-"*80)
        
        # 方法1: 仅规则
        print("\n【方法1: 仅规则匹配】")
        result_rule = extractor.extract(job, use_llm=False)
        print(f"提取技能 ({result_rule['stats']['rule_count']}个):")
        for skill in result_rule['merged_skills']:
            print(f"  - {skill['name']} (置信度: {skill['confidence']:.2f}, 来源: {skill['source']})")
        
        # 方法2: 混合方法（规则+LLM）
        print("\n【方法2: 混合方法(规则+LLM)】")
        result_hybrid = extractor.extract(job, use_llm=True)
        print(f"提取技能 ({result_hybrid['stats']['merged_count']}个):")
        for skill in result_hybrid['merged_skills']:
            print(f"  - {skill['name']} (置信度: {skill['confidence']:.2f}, 来源: {skill['source']})")
        
        # 统计对比
        print(f"\n📊 统计:")
        print(f"  规则匹配: {result_hybrid['stats']['rule_count']} 个")
        print(f"  LLM提取: {result_hybrid['stats']['llm_count']} 个")
        print(f"  新增: {result_hybrid['stats']['new_from_llm']} 个")
        print(f"  总计: {result_hybrid['stats']['merged_count']} 个")
        
        if result_hybrid['stats']['new_from_llm'] > 0:
            improvement = (result_hybrid['stats']['new_from_llm'] / 
                         result_hybrid['stats']['rule_count'] * 100)
            print(f"  提升: +{improvement:.1f}%")
    
    print(f"\n{'='*80}")
    print("[OK] 测试完成！")
    print("="*80)


if __name__ == "__main__":
    import logging
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    test_hybrid_extractor()
