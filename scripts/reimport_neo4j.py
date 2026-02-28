"""
重新导入Neo4j数据库（清空+导入）
"""
import sys
import logging
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def select_data_source():
    """
    选择数据源（清洗数据 vs 增强数据）
    
    Returns:
        (data_dir, data_type, files)
    """
    cleaned_dir = project_root / 'data' / 'cleaned'
    enhanced_dir = project_root / 'data' / 'enhanced'
    
    cleaned_files = list(cleaned_dir.glob('boss_*_cleaned.json'))
    # Python 3.12 在目录不存在时 glob() 会抛 OSError，先做存在性检查
    if enhanced_dir.exists():
        enhanced_files = sorted(enhanced_dir.glob('*.json'), key=lambda f: f.stat().st_mtime, reverse=True)
    else:
        enhanced_files = []

    print("\n【数据源选择】")
    print("-"*80)

    if enhanced_files:
        print(f"\n发现增强数据（按修改时间排序）:")
        for i, f in enumerate(enhanced_files):
            size_mb = f.stat().st_size / 1024 / 1024
            tag = "← 最新" if i == 0 else ""
            print(f"  {i+1}. {f.name} ({size_mb:.2f} MB) {tag}")

        print(f"\n清洗数据: {len(cleaned_files)} 个文件")
        for f in cleaned_files:
            size_mb = f.stat().st_size / 1024 / 1024
            print(f"  - {f.name} ({size_mb:.2f} MB)")

        print("\n请选择数据源:")
        print("  1. 最新增强数据（推荐）")
        print("  2. 清洗数据（仅规则抽取）")

        choice = input("\n请输入选项 (1/2，默认1): ").strip() or '1'

        if choice == '1':
            # 只使用最新的 enhanced 文件（单文件包含所有城市）
            latest = enhanced_files[0]
            logger.info(f"使用最新 enhanced 文件: {latest.name}")
            return enhanced_dir, 'enhanced', [latest]
        else:
            return cleaned_dir, 'cleaned', cleaned_files

    elif cleaned_files:
        print(f"\n仅发现清洗数据: {len(cleaned_files)} 个文件")
        for f in cleaned_files:
            size_mb = f.stat().st_size / 1024 / 1024
            print(f"  - {f.name} ({size_mb:.2f} MB)")

        print("\n提示: 可以先运行 scripts/enhance_with_qwen3.py 进行LLM增强")
        print("使用清洗数据导入")

        return cleaned_dir, 'cleaned', cleaned_files

    else:
        logger.error("未找到数据文件！")
        logger.error("请先运行数据清洗或LLM增强")
        return None, None, None


def reimport_all():
    """重新导入所有数据"""
    
    print("="*80)
    print("Neo4j数据库重新导入")
    print("="*80)
    print()
    
    # 步骤0: 选择数据源
    data_dir, data_type, data_files = select_data_source()
    
    if not data_files:
        return
    
    # 步骤1: 清空数据库
    print("\n【步骤 1/3】清空Neo4j数据库")
    print("-"*80)
    
    # 从config.yaml读取配置
    import yaml
    config_file = project_root / 'config.yaml'
    
    if not config_file.exists():
        logger.error("配置文件 config.yaml 不存在")
        return
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    NEO4J_URI = config['neo4j']['uri']
    NEO4J_USER = config['neo4j']['user']
    NEO4J_PASSWORD = config['neo4j']['password']
    NEO4J_DATABASE = config['neo4j'].get('database', 'neo4j')
    
    logger.info(f"连接到 Neo4j: {NEO4J_URI}")
    
    from neo4j import GraphDatabase
    
    driver = None  # 初始化driver变量
    
    try:
        # 使用标准 neo4j 驱动
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
        logger.info("✅ 成功连接到Neo4j")
        
        # 统计当前数据
        with driver.session(database=NEO4J_DATABASE) as session:
            result = session.run("MATCH (n) RETURN COUNT(n) as count")
            node_count = result.single()['count']
            
            result = session.run("MATCH ()-[r]->() RETURN COUNT(r) as count")
            rel_count = result.single()['count']
        
        print(f"当前节点数: {node_count}")
        print(f"当前关系数: {rel_count}")
        
        if node_count > 0:
            print("\n⚠️  数据库中已有数据，需要清空")
            confirm = input("确认清空数据库？(yes/no): ").strip().lower()
            
            if confirm != 'yes':
                print("取消导入")
                driver.close()
                return
            
            # 清空数据（batch_size 调小避免 Neo4j 事务内存超限）
            print("\n清空数据中...")
            batch_size = 1000
            deleted_total = 0
            
            with driver.session(database=NEO4J_DATABASE) as session:
                while True:
                    result = session.run(f"""
                        MATCH (n)
                        WITH n LIMIT {batch_size}
                        DETACH DELETE n
                        RETURN COUNT(n) as deleted
                    """)
                    
                    deleted = result.single()['deleted']
                    deleted_total += deleted
                    
                    if deleted == 0:
                        break
                    
                    print(f"  已删除 {deleted_total} 个节点...")
            
            print(f"✅ 清空完成！共删除 {deleted_total} 个节点\n")
        
        # 保持driver连接，后续还需要使用
        
    except Exception as e:
        logger.error(f"清空数据库失败: {e}")
        import traceback
        traceback.print_exc()
        if driver:
            driver.close()
        return
    
    # 步骤2: 加载数据统计
    print("\n【步骤 2/3】数据统计")
    print("-"*80)
    
    import json
    total_jobs = 0
    total_skills_per_job = []
    
    for f in data_files:
        with open(f, encoding='utf-8') as file:
            jobs = json.load(file)
            total_jobs += len(jobs)
            for job in jobs:
                skills = job.get('skills', [])
                total_skills_per_job.append(len(skills))
    
    avg_skills = sum(total_skills_per_job) / len(total_skills_per_job) if total_skills_per_job else 0
    
    print(f"数据类型: {data_type}")
    print(f"文件数量: {len(data_files)}")
    print(f"岗位总数: {total_jobs}")
    print(f"平均技能数/岗位: {avg_skills:.2f}")
    
    if data_type == 'enhanced':
        print("✅ 将使用LLM增强数据（包含规则+LLM合并后的技能）")
    else:
        print("⚠️  将使用清洗数据（仅规则抽取的技能）")
    
    # 步骤3: 导入数据
    print("\n【步骤 3/3】导入数据到Neo4j")
    print("-"*80)
    
    from src.graph_builder.neo4j_importer import import_data_pipeline
    
    skill_dict_path = str(project_root / 'data' / 'skill_dict' / 'skill_taxonomy.json')
    
    try:
        import_data_pipeline(
            skill_dict_path=skill_dict_path,
            cleaned_data_paths=[str(f) for f in data_files],
            neo4j_uri=NEO4J_URI,
            neo4j_user=NEO4J_USER,
            neo4j_password=NEO4J_PASSWORD
        )
        
        print("\n" + "="*80)
        print("[OK] 重新导入完成！")
        print("="*80)
        
        # 显示导入统计
        print(f"\n【导入统计】")
        print(f"  数据源: {data_type}")
        print(f"  岗位数: {total_jobs}")
        
        # 查询Neo4j统计（用独立查询，避免多步 MATCH 链式结构因空结果导致 None）
        with driver.session(database=NEO4J_DATABASE) as session:
            skill_count   = session.run("MATCH (s:Skill)   RETURN COUNT(s) AS c").single()['c']
            company_count = session.run("MATCH (c:Company) RETURN COUNT(c) AS c").single()['c']
            req_count     = session.run("MATCH ()-[r:REQUIRES]->() RETURN COUNT(r) AS c").single()['c']
            print(f"  技能数: {skill_count}")
            print(f"  公司数: {company_count}")
            print(f"  技能关系数: {req_count}")
        
        driver.close()
        
        print("\n【下一步】")
        print("  1. 浏览Neo4j:")
        print("     http://localhost:7474")
        print()
        print("  2. 测试查询:")
        print("     # 查看技能")
        print("     MATCH (s:Skill)")
        print("     RETURN s.name, s.category, s.hot_score, s.demand_count")
        print("     ORDER BY s.demand_count DESC LIMIT 20")
        print()
        print("     # 查看岗位")
        print("     MATCH (j:Job)")
        print("     RETURN j.title, j.city, j.salary_text, j.skill_count")
        print("     ORDER BY j.salary_min DESC LIMIT 20")
        print()
        print("  3. 重建向量数据库（使用增强后的数据）:")
        print("     python scripts/rebuild_vector_db.py")
        print()
        print("  4. 启动API服务:")
        print("     python run_api.py")
        print()
        
    except Exception as e:
        logger.error(f"导入失败: {e}")
        import traceback
        traceback.print_exc()
        if driver:
            driver.close()


if __name__ == '__main__':
    reimport_all()
