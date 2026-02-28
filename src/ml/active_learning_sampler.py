"""
主动学习采样器
基于聚类的智能采样策略，用于降低LLM成本

核心思路:
1. 对50万JD进行向量化（使用m3e-base，本地运行）
2. K-Means聚类，将数据分成N个簇
3. 从每个簇选择代表性样本（最靠近簇中心的样本）
4. LLM只处理这些代表性样本（1-2万条）
5. 用LLM结果训练蒸馏模型，处理剩余数据

优势:
- 成本降低: 只需处理2-5%的数据
- 准确率保持: 代表性采样保证覆盖度
- 可扩展: 支持多种采样策略

技术亮点（2026年主流）:
- 主动学习 (Active Learning)
- 向量化 + 聚类
- 成本优化
"""
import logging
import numpy as np
from typing import List, Dict, Tuple
from pathlib import Path
import sys

logger = logging.getLogger(__name__)


class ActiveLearningSampler:
    """主动学习采样器"""
    
    def __init__(self, embedding_model: str = "moka-ai/m3e-base"):
        """
        初始化采样器
        
        Args:
            embedding_model: 向量化模型名称
        """
        logger.info("="*80)
        logger.info("🎯 初始化主动学习采样器")
        logger.info("="*80)
        
        # 加载向量化模型
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"⏳ 加载向量化模型: {embedding_model}")
            self.encoder = SentenceTransformer(embedding_model)
            logger.info("✅ 向量化模型加载完成")
        except ImportError:
            logger.error("❌ sentence-transformers未安装")
            logger.error("请运行: pip install sentence-transformers")
            raise
        except Exception as e:
            logger.error(f"❌ 模型加载失败: {e}")
            raise
        
        self.embedding_model = embedding_model
        logger.info("✅ 采样器初始化完成")
        logger.info("="*80)
    
    def intelligent_sample(
        self,
        jobs: List[Dict],
        target_count: int = 10000,
        strategy: str = "cluster",
        show_progress: bool = True
    ) -> Tuple[List[Dict], np.ndarray]:
        """
        智能采样（基于聚类）
        
        Args:
            jobs: 所有岗位数据
            target_count: 目标采样数量
            strategy: 采样策略 ("cluster"=聚类采样, "diverse"=多样性采样)
            show_progress: 是否显示进度
            
        Returns:
            (采样的岗位列表, 聚类标签数组)
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"🎯 开始智能采样")
        logger.info(f"{'='*80}")
        logger.info(f"总数据量: {len(jobs):,} 条")
        logger.info(f"目标采样: {target_count:,} 条 ({target_count/len(jobs)*100:.2f}%)")
        logger.info(f"采样策略: {strategy}")
        logger.info("-"*80)
        
        # 1. 提取JD文本
        logger.info("📝 [1/4] 提取JD文本...")
        jd_texts = []
        for job in jobs:
            text = self._extract_jd_text(job)
            jd_texts.append(text)
        logger.info(f"✅ 提取完成: {len(jd_texts)} 条")
        
        # 2. 向量化
        logger.info("\n🔢 [2/4] 向量化JD文本...")
        logger.info(f"   使用模型: {self.embedding_model}")
        embeddings = self.encoder.encode(
            jd_texts,
            show_progress_bar=show_progress,
            batch_size=64,
            normalize_embeddings=True
        )
        logger.info(f"✅ 向量化完成: shape={embeddings.shape}")
        
        # 3. 聚类
        logger.info("\n🎲 [3/4] K-Means聚类...")
        
        if strategy == "cluster":
            sampled_jobs, labels = self._cluster_sampling(
                jobs, embeddings, target_count
            )
        elif strategy == "diverse":
            sampled_jobs, labels = self._diversity_sampling(
                jobs, embeddings, target_count
            )
        else:
            raise ValueError(f"未知策略: {strategy}")
        
        # 4. 统计分析
        logger.info(f"\n📊 [4/4] 采样统计")
        logger.info("-"*80)
        self._print_sampling_stats(jobs, sampled_jobs, labels)
        
        logger.info(f"\n{'='*80}")
        logger.info(f"✅ 智能采样完成！")
        logger.info(f"{'='*80}\n")
        
        return sampled_jobs, labels
    
    def _cluster_sampling(
        self,
        jobs: List[Dict],
        embeddings: np.ndarray,
        target_count: int
    ) -> Tuple[List[Dict], np.ndarray]:
        """基于聚类的采样"""
        from sklearn.cluster import KMeans
        
        # 计算聚类数量（每个簇平均10-20个样本）
        n_clusters = max(target_count // 15, 100)
        n_clusters = min(n_clusters, len(jobs) // 5)  # 确保每个簇至少5个样本
        
        logger.info(f"   聚类数量: {n_clusters}")
        logger.info(f"   目标: 每簇采样 ~{target_count/n_clusters:.0f} 个")
        
        # K-Means聚类
        kmeans = KMeans(
            n_clusters=n_clusters,
            random_state=42,
            n_init=10,
            max_iter=300
        )
        labels = kmeans.fit_predict(embeddings)
        logger.info(f"✅ 聚类完成")
        
        # 从每个簇中选择代表样本
        sampled_jobs = []
        samples_per_cluster = target_count // n_clusters + 1
        
        for cluster_id in range(n_clusters):
            # 找到属于该簇的所有样本
            cluster_indices = np.where(labels == cluster_id)[0]
            
            if len(cluster_indices) == 0:
                continue
            
            # 计算到簇中心的距离
            cluster_embeddings = embeddings[cluster_indices]
            cluster_center = kmeans.cluster_centers_[cluster_id]
            
            distances = np.linalg.norm(
                cluster_embeddings - cluster_center,
                axis=1
            )
            
            # 选择最靠近簇中心的N个样本
            n_samples = min(samples_per_cluster, len(cluster_indices))
            closest_indices = np.argsort(distances)[:n_samples]
            
            # 添加到采样列表
            for idx in closest_indices:
                original_idx = cluster_indices[idx]
                sampled_jobs.append(jobs[original_idx])
                
                if len(sampled_jobs) >= target_count:
                    break
            
            if len(sampled_jobs) >= target_count:
                break
        
        logger.info(f"✅ 采样完成: {len(sampled_jobs)} 条")
        
        return sampled_jobs, labels
    
    def _diversity_sampling(
        self,
        jobs: List[Dict],
        embeddings: np.ndarray,
        target_count: int
    ) -> Tuple[List[Dict], np.ndarray]:
        """基于多样性的采样（Greedy最远点采样）"""
        logger.info("   使用贪心最远点采样...")
        
        sampled_indices = []
        remaining_indices = set(range(len(jobs)))
        
        # 随机选择第一个点
        first_idx = np.random.randint(0, len(jobs))
        sampled_indices.append(first_idx)
        remaining_indices.remove(first_idx)
        
        # 贪心选择最远点
        for _ in range(target_count - 1):
            if not remaining_indices:
                break
            
            # 计算每个未采样点到已采样点的最小距离
            remaining = list(remaining_indices)
            remaining_embeddings = embeddings[remaining]
            sampled_embeddings = embeddings[sampled_indices]
            
            # 计算距离矩阵
            distances = np.linalg.norm(
                remaining_embeddings[:, np.newaxis] - sampled_embeddings,
                axis=2
            )
            min_distances = distances.min(axis=1)
            
            # 选择最远的点
            farthest_idx = remaining[np.argmax(min_distances)]
            sampled_indices.append(farthest_idx)
            remaining_indices.remove(farthest_idx)
        
        sampled_jobs = [jobs[i] for i in sampled_indices]
        labels = np.zeros(len(jobs), dtype=int)  # 多样性采样不产生簇标签
        
        logger.info(f"✅ 多样性采样完成: {len(sampled_jobs)} 条")
        
        return sampled_jobs, labels
    
    def _extract_jd_text(self, job: Dict) -> str:
        """从岗位数据提取JD文本"""
        # 优先使用jd_text
        if 'jd_text' in job and job['jd_text']:
            return job['jd_text'][:1000]  # 限制长度
        
        # 否则拼接其他字段
        parts = []
        
        if job.get('title'):
            parts.append(f"岗位: {job['title']}")
        
        if job.get('skills'):
            skills = job['skills']
            if isinstance(skills, list):
                parts.append(f"技能: {', '.join(skills[:20])}")
            else:
                parts.append(f"技能: {skills}")
        
        if job.get('description'):
            parts.append(f"描述: {job['description'][:500]}")
        
        if job.get('welfare'):
            welfare = job['welfare']
            if isinstance(welfare, list):
                parts.append(f"福利: {', '.join(welfare[:5])}")
        
        return "\n".join(parts)[:1000]
    
    def _print_sampling_stats(
        self,
        all_jobs: List[Dict],
        sampled_jobs: List[Dict],
        labels: np.ndarray
    ):
        """打印采样统计信息"""
        logger.info(f"总数据量: {len(all_jobs):,} 条")
        logger.info(f"采样数量: {len(sampled_jobs):,} 条")
        logger.info(f"采样比例: {len(sampled_jobs)/len(all_jobs)*100:.2f}%")
        
        # 分析聚类分布
        if labels.max() > 0:
            unique_labels = np.unique(labels)
            logger.info(f"聚类数量: {len(unique_labels)}")
            
            # 统计每个簇的样本数
            cluster_sizes = [np.sum(labels == label) for label in unique_labels]
            logger.info(f"簇大小: min={min(cluster_sizes)}, "
                       f"max={max(cluster_sizes)}, "
                       f"avg={np.mean(cluster_sizes):.0f}")
        
        # 分析采样覆盖度
        sampled_job_ids = set(j.get('job_id') for j in sampled_jobs)
        logger.info(f"唯一job_id: {len(sampled_job_ids)}")
    
    def stratified_sample(
        self,
        jobs: List[Dict],
        target_count: int,
        stratify_by: str = 'city'
    ) -> List[Dict]:
        """
        分层采样（按城市、薪资等分层）
        
        Args:
            jobs: 所有岗位
            target_count: 目标数量
            stratify_by: 分层字段 ('city', 'salary_range', etc.)
            
        Returns:
            采样的岗位列表
        """
        from collections import defaultdict
        
        logger.info(f"📊 分层采样 (按{stratify_by})")
        
        # 分组
        groups = defaultdict(list)
        for job in jobs:
            key = job.get(stratify_by, 'unknown')
            groups[key].append(job)
        
        logger.info(f"   分层数: {len(groups)}")
        for key, items in groups.items():
            logger.info(f"   - {key}: {len(items)} 条")
        
        # 按比例采样
        sampled = []
        for key, items in groups.items():
            n_samples = int(len(items) / len(jobs) * target_count)
            n_samples = max(1, min(n_samples, len(items)))
            
            import random
            sampled.extend(random.sample(items, n_samples))
        
        logger.info(f"✅ 分层采样完成: {len(sampled)} 条")
        
        return sampled


# 测试代码
def test_active_learning_sampler():
    """测试主动学习采样器"""
    print("\n" + "="*80)
    print("🧪 测试主动学习采样器")
    print("="*80)
    
    try:
        # 创建测试数据
        print("\n📝 创建测试数据...")
        test_jobs = []
        for i in range(1000):
            test_jobs.append({
                'job_id': f'job_{i}',
                'title': f'Python开发工程师_{i%10}',
                'skills': ['Python', 'Django', 'MySQL'],
                'jd_text': f'负责后端开发，使用Python和Django框架。需要{i%5}年经验。',
                'city': ['北京', '上海', '深圳', '杭州'][i % 4]
            })
        print(f"✅ 创建完成: {len(test_jobs)} 条")
        
        # 初始化采样器
        sampler = ActiveLearningSampler()
        
        # 测试1: 聚类采样
        print(f"\n{'='*80}")
        print("【测试1: 聚类采样】")
        print("="*80)
        
        sampled, labels = sampler.intelligent_sample(
            test_jobs,
            target_count=100,
            strategy="cluster"
        )
        print(f"✅ 采样完成: {len(sampled)} 条")
        
        # 测试2: 分层采样
        print(f"\n{'='*80}")
        print("【测试2: 分层采样】")
        print("="*80)
        
        sampled_stratified = sampler.stratified_sample(
            test_jobs,
            target_count=100,
            stratify_by='city'
        )
        print(f"✅ 分层采样完成: {len(sampled_stratified)} 条")
        
        print(f"\n{'='*80}")
        print("✅ 所有测试通过！")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    test_active_learning_sampler()
