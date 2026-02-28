"""
重建向量数据库
使用 enhanced 数据（包含更多字段），用改进后的 _build_document 重新向量化。
文档格式：岗位 | 技能要求×2 | 城市 | 经验 | 薪资 | 行业 | 公司 | 福利

用法:
    python scripts/rebuild_vector_db.py
"""
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.rag.vector_db import VectorDB


def main():
    # ── 1. 自动选择数据源（优先最新的 enhanced，降级用 cleaned 合并）───────
    enhanced_dir = project_root / "data" / "enhanced"

    # Python 3.12 在目录不存在时 glob() 会抛 OSError，先做存在性检查
    if enhanced_dir.exists():
        enhanced_files = sorted(enhanced_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    else:
        enhanced_files = []

    if enhanced_files:
        enhanced_file = enhanced_files[0]   # 取最新修改的 enhanced 文件
        logger.info(f"使用 enhanced 数据（最新）: {enhanced_file.name}")
        if len(enhanced_files) > 1:
            logger.info(f"  其他 enhanced 文件: {[f.name for f in enhanced_files[1:]]}")
        with open(enhanced_file, encoding="utf-8") as fp:
            all_jobs = json.load(fp)
    else:
        logger.warning("未找到 enhanced 文件，降级使用 cleaned 数据（建议先运行 enhance_with_qwen3.py）")
        data_dir = project_root / "data" / "cleaned"
        city_files = sorted(data_dir.glob("boss_*_cleaned.json"))
        if not city_files:
            logger.error("未找到任何数据文件，请检查 data/ 目录")
            sys.exit(1)
        all_jobs = []
        for f in city_files:
            with open(f, encoding="utf-8") as fp:
                jobs = json.load(fp)
            city = f.stem.replace("boss_", "").replace("_cleaned", "")
            logger.info(f"  {city}: {len(jobs):,} 条")
            all_jobs.extend(jobs)

    logger.info(f"原始加载: {len(all_jobs):,} 条")

    # ── 1.5 按 job_id 去重（同一批次内有重复 ID 会导致 upsert 报错）────────
    seen: dict = {}
    for job in all_jobs:
        jid = job.get('job_id', '')
        if jid and jid not in seen:
            seen[jid] = job
    deduped = len(all_jobs) - len(seen)
    all_jobs = list(seen.values())
    if deduped > 0:
        logger.info(f"去重（job_id 重复）: 移除 {deduped:,} 条")

    # ── 2. 数据过滤 ──────────────────────────────────────────────────────
    MAX_SKILLS = 30   # 超过30个技能视为脏数据（LLM过度提取或异常）
    MIN_TITLE_LEN = 2

    before = len(all_jobs)
    all_jobs = [
        j for j in all_jobs
        if j.get("title") and len(j["title"].strip()) >= MIN_TITLE_LEN
        and len(j.get("skills", [])) <= MAX_SKILLS
    ]
    filtered = before - len(all_jobs)
    logger.info(f"过滤脏数据（技能数>{MAX_SKILLS} 或无标题）: 移除 {filtered:,} 条")
    logger.info(f"有效数据: {len(all_jobs):,} 条")

    if not all_jobs:
        logger.error("过滤后数据为空，请检查数据文件")
        sys.exit(1)

    # ── 3. 初始化向量数据库 ──────────────────────────────────────────────
    logger.info("初始化向量数据库...")
    db = VectorDB()
    old_count = db.collection.count()
    logger.info(f"当前向量库文档数: {old_count:,}")

    # ── 4. 清空旧数据 ────────────────────────────────────────────────────
    if old_count > 0:
        logger.info(f"清空旧数据（{old_count:,} 条）...")
        db.clear()
        logger.info("清空完成")

    # ── 5. 重新导入（使用新的 _build_document） ─────────────────────────
    logger.info("开始重新向量化并导入...")
    logger.info("文档格式：岗位 | 技能要求 | 城市 | 经验 | 薪资 | 公司")

    db.add_jobs(all_jobs, batch_size=64, show_progress=True)

    new_count = db.collection.count()
    logger.info(f"重建完成！向量库文档数: {new_count:,}")

    # ── 6. 验证搜索效果 ──────────────────────────────────────────────────
    logger.info("\n搜索效果验证:")
    test_queries = [
        "Python后端开发",
        "React前端工程师",
        "Java微服务架构",
        "数据分析师 SQL Excel",
        "机器学习算法工程师",
    ]
    for q in test_queries:
        results = db.search(q, top_k=3)
        hits   = results["metadatas"][0] if results["metadatas"] else []
        dists  = results["distances"][0] if results["distances"] else []
        logger.info(f"\n  查询: {q}")
        for hit, d in zip(hits, dists):
            sim = round(1 / (1 + max(0, d)), 3)
            logger.info(f"    → {hit.get('title',''):<28}  {hit.get('city','')}  相似度:{sim:.3f}")

    logger.info("\n✅ 向量数据库重建完成！")


if __name__ == "__main__":
    main()
