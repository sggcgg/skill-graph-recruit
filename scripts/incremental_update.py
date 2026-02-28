"""
增量数据更新脚本
支持向量数据库和Neo4j的增量更新
"""
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict

# 添加项目根目录到path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.rag.vector_db import VectorDB
from src.graph_builder.neo4j_importer import Neo4jImporter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def incremental_update_vector_db(new_data_file: Path, batch_size: int = 50):
    """
    增量更新向量数据库
    
    Args:
        new_data_file: 新数据文件路径
        batch_size: 批处理大小
    """
    print("="*80)
    print("📦 增量更新向量数据库")
    print("="*80)
    
    # 1. 初始化VectorDB
    logger.info("【步骤1: 连接向量数据库】")
    db = VectorDB()
    
    # 检查当前状态
    stats_before = db.get_stats()
    logger.info(f"当前文档数: {stats_before['total_documents']}")
    
    # 2. 加载新数据
    logger.info("\n【步骤2: 加载新数据】")
    with open(new_data_file, 'r', encoding='utf-8') as f:
        new_jobs = json.load(f)
    logger.info(f"待添加数据: {len(new_jobs)} 条")
    
    # 3. 增量添加
    logger.info("\n【步骤3: 增量添加到向量库】")
    db.add_jobs(new_jobs, batch_size=batch_size, show_progress=True)
    
    # 4. 检查结果
    stats_after = db.get_stats()
    logger.info(f"\n✅ 更新完成！")
    logger.info(f"   更新前: {stats_before['total_documents']} 条")
    logger.info(f"   更新后: {stats_after['total_documents']} 条")
    logger.info(f"   新增: {stats_after['total_documents'] - stats_before['total_documents']} 条")


def incremental_update_neo4j(new_data_file: Path):
    """
    增量更新Neo4j图数据库
    
    Args:
        new_data_file: 新数据文件路径
    """
    print("\n" + "="*80)
    print("📊 增量更新Neo4j图数据库")
    print("="*80)
    
    # 1. 加载新数据
    logger.info("【步骤1: 加载新数据】")
    with open(new_data_file, 'r', encoding='utf-8') as f:
        new_jobs = json.load(f)
    logger.info(f"待添加数据: {len(new_jobs)} 条")
    
    # 2. 初始化Neo4j Importer
    logger.info("\n【步骤2: 连接Neo4j】")
    importer = Neo4jImporter()
    
    # 3. 增量导入（使用MERGE，不会重复）
    logger.info("\n【步骤3: 增量导入岗位数据】")
    importer.import_jobs(new_jobs, batch_size=100)
    
    # 4. 更新技能关联关系
    logger.info("\n【步骤4: 更新技能关联】")
    importer.create_skill_relationships()
    
    logger.info("\n✅ Neo4j增量更新完成！")


def main():
    """主函数"""
    print("="*80)
    print("🔄 增量数据更新工具")
    print("="*80)
    
    # 1. 选择新数据文件
    print("\n【选择新数据文件】")
    data_dir = project_root / 'data'
    
    # 查找可用的数据文件
    enhanced_files = list((data_dir / 'enhanced').glob('*.json'))
    cleaned_files = list((data_dir / 'cleaned').glob('boss_*_cleaned.json'))
    
    print("\n可用的数据文件:")
    all_files = []
    
    if enhanced_files:
        print("\n增强数据（推荐）:")
        for i, f in enumerate(enhanced_files):
            size_mb = f.stat().st_size / 1024 / 1024
            print(f"  [{i+1}] {f.name} ({size_mb:.2f} MB)")
            all_files.append(f)
    
    if cleaned_files:
        print("\n清洗数据（仅规则提取）:")
        start_idx = len(all_files) + 1
        for i, f in enumerate(cleaned_files):
            size_mb = f.stat().st_size / 1024 / 1024
            print(f"  [{start_idx+i}] {f.name} ({size_mb:.2f} MB)")
            all_files.append(f)
    
    if not all_files:
        print("❌ 未找到数据文件！")
        return
    
    # 选择文件
    choice = int(input(f"\n请选择文件 (1-{len(all_files)}): ")) - 1
    selected_file = all_files[choice]
    
    print(f"\n已选择: {selected_file.name}")
    
    # 2. 选择更新目标
    print("\n【选择更新目标】")
    print("  [1] 仅更新向量数据库")
    print("  [2] 仅更新Neo4j")
    print("  [3] 同时更新两者（推荐）")
    
    target = int(input("\n请选择 (1-3): "))
    
    # 3. 执行更新
    try:
        if target == 1 or target == 3:
            incremental_update_vector_db(selected_file)
        
        if target == 2 or target == 3:
            incremental_update_neo4j(selected_file)
        
        print("\n" + "="*80)
        print("✅ 增量更新全部完成！")
        print("="*80)
        
    except Exception as e:
        logger.error(f"❌ 更新失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
