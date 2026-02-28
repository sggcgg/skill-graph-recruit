"""
一键运行完整数据处理流程
"""
import sys
from pathlib import Path
import logging

# 设置项目根目录
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(project_root / 'pipeline.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """运行完整流程"""
    
    print("="*80)
    print("智能招聘信息聚合分析系统 - 数据处理流程")
    print("="*80)
    print()
    
    # 步骤1：数据清洗
    print("【步骤 1/3】数据清洗")
    print("-"*80)
    try:
        from src.data_processing.data_cleaner import clean_all_cities
        clean_all_cities()
        print("\n✅ 数据清洗完成\n")
    except Exception as e:
        logger.error(f"数据清洗失败: {e}")
        print(f"\n❌ 数据清洗失败: {e}\n")
        return
    
    # 步骤2：生成报告
    print("\n【步骤 2/3】生成数据质量报告")
    print("-"*80)
    try:
        from scripts.generate_report import DataQualityReport
        
        raw_dir = project_root / 'data' / 'raw'
        cleaned_dir = project_root / 'data' / 'cleaned'
        output_dir = project_root / 'reports'
        
        reporter = DataQualityReport(raw_dir, cleaned_dir, output_dir)
        reporter.generate_full_report()
        print("\n✅ 报告生成完成\n")
    except Exception as e:
        logger.error(f"报告生成失败: {e}")
        print(f"\n❌ 报告生成失败: {e}\n")
    
    # 步骤3：导入Neo4j（需要用户确认）
    print("\n【步骤 3/3】导入Neo4j图数据库")
    print("-"*80)
    print("⚠️  注意：此步骤需要Neo4j服务正在运行")
    print("   请确保:")
    print("   1. Neo4j已启动（默认端口7687）")
    print("   2. 已修改neo4j_importer.py中的密码")
    print()
    
    choice = input("是否继续导入Neo4j? (y/n): ").strip().lower()
    
    if choice == 'y':
        try:
            print("\n正在导入Neo4j...")
            # 这里不直接执行，而是给出提示
            print("\n请运行以下命令导入Neo4j:")
            print("  python src/graph_builder/neo4j_importer.py")
            print("\n或手动修改密码后导入")
        except Exception as e:
            logger.error(f"Neo4j导入失败: {e}")
            print(f"\n❌ Neo4j导入失败: {e}")
    else:
        print("\n跳过Neo4j导入")
    
    # 完成
    print("\n" + "="*80)
    print("🎉 数据处理流程完成!")
    print("="*80)
    print("\n生成的文件:")
    print(f"  📁 清洗后数据: data/cleaned/")
    print(f"  📄 清洗统计: data/cleaned/cleaning_summary.json")
    print(f"  📊 数据报告: reports/data_quality_report.html")
    print(f"  📈 图表: reports/*.png")
    print()
    print("下一步:")
    print("  1. 查看报告: 用浏览器打开 reports/data_quality_report.html")
    print("  2. 导入Neo4j: python src/graph_builder/neo4j_importer.py")
    print("  3. 查询图谱: 浏览器访问 http://localhost:7474")
    print()
    print("详细文档: README_USAGE.md")
    print()


if __name__ == '__main__':
    main()
