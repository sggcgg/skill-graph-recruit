"""
初始化向量数据库
将清洗后的招聘数据向量化并存入ChromaDB
"""
import json
import logging
import sys
from pathlib import Path
from tqdm import tqdm

# 添加项目根目录到path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.rag.vector_db import VectorDB

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_cleaned_data(project_root: Path) -> list:
    """
    加载清洗后的数据
    
    Args:
        project_root: 项目根目录
        
    Returns:
        所有岗位数据列表
    """
    all_jobs = []
    
    # 数据目录（使用绝对路径）
    data_dir = project_root / 'data' / 'cleaned'
    
    # 查找所有清洗后的JSON文件
    cleaned_files = list(data_dir.glob("boss_*_cleaned.json"))
    
    if not cleaned_files:
        logger.error(f"未找到清洗后的数据文件: {data_dir}")
        logger.error("请先运行数据清洗: python src/data_processing/data_cleaner.py")
        return []
    
    logger.info(f"找到 {len(cleaned_files)} 个数据文件")
    
    for file_path in cleaned_files:
        logger.info(f"加载: {file_path.name}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            jobs = json.load(f)
            all_jobs.extend(jobs)
            logger.info(f"  加载了 {len(jobs)} 条数据")
    
    logger.info(f"总计加载 {len(all_jobs)} 条岗位数据")
    return all_jobs


def init_vector_database(force_recreate: bool = False):
    """
    初始化向量数据库
    
    Args:
        force_recreate: 是否强制重新创建（清空已有数据）
    """
    print("="*80)
    print("📦 初始化向量数据库")
    print("="*80)
    
    # 1. 初始化VectorDB
    logger.info("\n【步骤1: 初始化向量数据库】")
    db = VectorDB()
    
    # 检查是否已有数据
    current_count = db.get_stats()['total_documents']
    logger.info(f"当前数据库文档数: {current_count}")
    
    if current_count > 0 and not force_recreate:
        logger.info("数据库已有数据")
        user_input = input("\n是否清空并重新导入? (y/n): ").strip().lower()
        if user_input != 'y':
            logger.info("取消操作")
            return
        
        logger.info("清空数据库...")
        db.clear()
    elif current_count > 0 and force_recreate:
        logger.info("强制重新创建，清空数据库...")
        db.clear()
    
    # 2. 加载数据
    logger.info("\n【步骤2: 加载清洗后的数据】")
    jobs = load_cleaned_data(project_root)
    
    if not jobs:
        logger.error("没有数据可导入")
        return
    
    # 3. 向量化并添加到数据库
    logger.info("\n【步骤3: 向量化并导入】")
    logger.info(f"开始向量化 {len(jobs)} 条数据...")
    logger.info(f"这可能需要一些时间，请耐心等待...")
    
    # 根据数据量估算时间
    estimated_minutes = len(jobs) / 1000  # 大约每1000条需要1分钟
    logger.info(f"预计时间: {estimated_minutes:.1f} 分钟")
    
    try:
        # 批量添加（带进度条）
        db.add_jobs(jobs, batch_size=50, show_progress=True)
        
        # 4. 验证
        logger.info("\n【步骤4: 验证】")
        final_stats = db.get_stats()
        
        print("\n" + "="*80)
        print("✅ 向量数据库初始化完成！")
        print("="*80)
        print(f"\n📊 统计信息:")
        print(f"  总文档数: {final_stats['total_documents']:,}")
        print(f"  向量维度: {final_stats['embedding_dim']}")
        print(f"  模型: {final_stats['model_name']}")
        print(f"\n💾 存储位置: data/vector_db/")
        
        # 5. 测试搜索
        logger.info("\n【步骤5: 测试搜索】")
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
                    similarity = 1 / (1 + max(0, distance))   # L2距离转相似度
                    print(f"  {i+1}. {meta['title']} | {meta['city']} (相似度: {similarity:.3f})")
        
        print("\n" + "="*80)
        print("🎉 全部完成！现在可以使用RAG检索功能了！")
        print("="*80)
        print("\n下一步:")
        print("  - 测试RAG服务: python src/rag/rag_service.py")
        print("  - 启动API服务: uvicorn src.api.main:app --reload")
        print()
        
    except Exception as e:
        logger.error(f"\n❌ 初始化失败: {e}")
        logger.error("\n可能的原因:")
        logger.error("1. 内存不足（向量化需要大量内存）")
        logger.error("2. 模型未下载（请先运行 python scripts/download_m3e_model.py）")
        logger.error("3. 磁盘空间不足")
        raise


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="初始化向量数据库")
    parser.add_argument(
        '--force',
        action='store_true',
        help='强制重新创建（清空已有数据）'
    )
    
    args = parser.parse_args()
    
    try:
        init_vector_database(force_recreate=args.force)
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    except Exception as e:
        logger.error(f"\n执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
