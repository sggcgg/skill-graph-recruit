"""
增量更新向量数据库
将新抓取的数据增量添加到ChromaDB（不清空已有数据）

使用场景：
1. 已经初始化过向量数据库
2. 新抓取了数据，需要添加到现有数据库
3. 不想重新处理所有数据

与 init_vector_db.py 的区别：
- init_vector_db.py: 清空并重新创建（全量）
- update_vector_db.py: 增量添加新数据（增量）
"""
import json
import logging
import sys
from pathlib import Path
from tqdm import tqdm
from typing import List, Set

# 添加项目根目录到path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.rag.vector_db import VectorDB

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_data_from_dir(data_dir: Path, pattern: str = "boss_*_cleaned.json") -> List[dict]:
    """
    从目录加载数据
    
    Args:
        data_dir: 数据目录
        pattern: 文件匹配模式
        
    Returns:
        岗位数据列表
    """
    all_jobs = []
    data_files = list(data_dir.glob(pattern))
    
    if not data_files:
        logger.warning(f"未找到数据文件: {data_dir}/{pattern}")
        return []
    
    logger.info(f"找到 {len(data_files)} 个数据文件")
    
    for file_path in data_files:
        logger.info(f"加载: {file_path.name}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            jobs = json.load(f)
            all_jobs.extend(jobs)
            logger.info(f"  加载了 {len(jobs)} 条数据")
    
    logger.info(f"总计加载 {len(all_jobs)} 条岗位数据")
    return all_jobs


def get_existing_job_ids(db: VectorDB) -> Set[str]:
    """
    获取数据库中已有的 job_id
    
    Args:
        db: VectorDB 实例
        
    Returns:
        已有的 job_id 集合
    """
    try:
        all_data = db.collection.get()
        existing_ids = set(all_data['ids'])
        logger.info(f"数据库中已有 {len(existing_ids)} 条数据")
        return existing_ids
    except Exception as e:
        logger.error(f"获取现有数据失败: {e}")
        return set()


def filter_new_jobs(jobs: List[dict], existing_ids: Set[str]) -> List[dict]:
    """
    过滤出新数据（不在数据库中的）
    
    Args:
        jobs: 所有岗位数据
        existing_ids: 已有的 job_id 集合
        
    Returns:
        新的岗位数据列表
    """
    new_jobs = []
    duplicate_count = 0
    
    for job in jobs:
        job_id = job.get('job_id')
        if not job_id:
            logger.warning("发现没有job_id的数据，跳过")
            continue
        
        if job_id in existing_ids:
            duplicate_count += 1
        else:
            new_jobs.append(job)
    
    logger.info(f"总数据: {len(jobs)} 条")
    logger.info(f"已存在: {duplicate_count} 条")
    logger.info(f"新数据: {len(new_jobs)} 条")
    
    return new_jobs


def update_vector_database(
    data_source: str = 'cleaned',
    skip_duplicates: bool = True,
    force_update: bool = False
):
    """
    增量更新向量数据库
    
    Args:
        data_source: 数据源类型 ('cleaned' 或 'enhanced')
        skip_duplicates: 是否跳过重复数据（True=只添加新数据，False=更新所有数据）
        force_update: 是否强制更新已有数据
    """
    print("="*80)
    print("📦 增量更新向量数据库")
    print("="*80)
    print()
    
    # 1. 初始化VectorDB
    logger.info("【步骤1: 连接向量数据库】")
    db = VectorDB()
    
    # 检查当前数据量
    current_stats = db.get_stats()
    current_count = current_stats['total_documents']
    logger.info(f"✅ 数据库连接成功")
    logger.info(f"  当前文档数: {current_count:,}")
    logger.info(f"  模型: {current_stats['model_name']}")
    
    if current_count == 0:
        logger.warning("\n⚠️  数据库为空！")
        logger.warning("建议使用 init_vector_db.py 进行首次初始化")
        
        user_input = input("\n是否继续？(y/n): ").strip().lower()
        if user_input != 'y':
            logger.info("取消操作")
            return
    
    # 2. 加载数据
    logger.info("\n【步骤2: 加载数据】")
    
    if data_source == 'enhanced':
        data_dir = project_root / 'data' / 'enhanced'
        pattern = 'boss_*_enhanced.json'
        logger.info("数据源: LLM增强数据")
    else:
        data_dir = project_root / 'data' / 'cleaned'
        pattern = 'boss_*_cleaned.json'
        logger.info("数据源: 清洗数据")
    
    jobs = load_data_from_dir(data_dir, pattern)
    
    if not jobs:
        logger.error("没有数据可导入")
        return
    
    # 3. 过滤重复数据（如果需要）
    logger.info("\n【步骤3: 检查重复】")
    
    if skip_duplicates and not force_update:
        existing_ids = get_existing_job_ids(db)
        new_jobs = filter_new_jobs(jobs, existing_ids)
        
        if not new_jobs:
            print("\n" + "="*80)
            print("✅ 没有新数据需要添加")
            print("="*80)
            print(f"\n数据库中已有全部 {len(jobs)} 条数据")
            print("\n如果需要更新已有数据，请使用:")
            print("  python scripts/update_vector_db.py --force-update")
            return
        
        jobs_to_add = new_jobs
        logger.info(f"将添加 {len(jobs_to_add)} 条新数据")
    else:
        jobs_to_add = jobs
        logger.info(f"将添加/更新 {len(jobs_to_add)} 条数据")
    
    # 4. 询问确认
    print(f"\n准备添加 {len(jobs_to_add)} 条数据到向量数据库")
    
    # 估算时间和空间
    estimated_minutes = len(jobs_to_add) / 1000  # 约1000条/分钟
    estimated_size_mb = len(jobs_to_add) * 0.01  # 约10KB/条
    
    print(f"预计耗时: {estimated_minutes:.1f} 分钟")
    print(f"预计占用空间: {estimated_size_mb:.1f} MB")
    
    user_input = input("\n确认继续？(y/n): ").strip().lower()
    if user_input != 'y':
        logger.info("取消操作")
        return
    
    # 5. 向量化并添加
    logger.info("\n【步骤4: 向量化并添加】")
    logger.info(f"开始处理 {len(jobs_to_add)} 条数据...")
    
    try:
        # 批量添加（带进度条）
        db.add_jobs(jobs_to_add, batch_size=50, show_progress=True)
        
        # 6. 验证
        logger.info("\n【步骤5: 验证】")
        final_stats = db.get_stats()
        final_count = final_stats['total_documents']
        
        added_count = final_count - current_count
        
        print("\n" + "="*80)
        print("✅ 向量数据库更新完成！")
        print("="*80)
        print(f"\n📊 更新统计:")
        print(f"  更新前: {current_count:,} 条")
        print(f"  更新后: {final_count:,} 条")
        print(f"  新增: {added_count:,} 条")
        print(f"\n💾 存储位置: data/vector_db/")
        
        # 7. 测试搜索
        logger.info("\n【步骤6: 测试搜索】")
        test_queries = [
            "Python后端开发",
            "前端React开发",
            "数据分析师"
        ]
        
        print(f"\n🔍 测试搜索功能:")
        for query in test_queries:
            results = db.search(query, top_k=3)
            if results['metadatas'] and results['metadatas'][0]:
                print(f"\n查询: {query}")
                for i, meta in enumerate(results['metadatas'][0]):
                    distance = results['distances'][0][i]
                    similarity = 1 / (1 + max(0, distance))
                    print(f"  {i+1}. {meta['title']} | {meta['city']} (相似度: {similarity:.3f})")
        
        print("\n" + "="*80)
        print("🎉 更新完成！")
        print("="*80)
        print("\n下一步:")
        print("  - 启动API服务: uvicorn src.api.main:app --reload")
        print("  - 测试RAG检索: python src/rag/rag_service.py")
        print()
        
    except Exception as e:
        logger.error(f"\n❌ 更新失败: {e}")
        logger.error("\n可能的原因:")
        logger.error("1. 内存不足")
        logger.error("2. 磁盘空间不足")
        logger.error("3. 数据格式错误")
        raise


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="增量更新向量数据库",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 增量添加清洗数据（只添加新数据）
  python scripts/update_vector_db.py
  
  # 增量添加LLM增强数据
  python scripts/update_vector_db.py --source enhanced
  
  # 强制更新所有数据（包括已有数据）
  python scripts/update_vector_db.py --force-update
  
  # 添加所有数据（不跳过重复）
  python scripts/update_vector_db.py --no-skip-duplicates
        """
    )
    
    parser.add_argument(
        '--source',
        choices=['cleaned', 'enhanced'],
        default='cleaned',
        help='数据源类型（默认：cleaned）'
    )
    
    parser.add_argument(
        '--no-skip-duplicates',
        action='store_true',
        help='不跳过重复数据（会更新已有数据）'
    )
    
    parser.add_argument(
        '--force-update',
        action='store_true',
        help='强制更新所有数据（包括已有数据）'
    )
    
    args = parser.parse_args()
    
    try:
        update_vector_database(
            data_source=args.source,
            skip_duplicates=not args.no_skip_duplicates,
            force_update=args.force_update
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    except Exception as e:
        logger.error(f"\n执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
