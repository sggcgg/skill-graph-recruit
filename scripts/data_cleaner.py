#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据清洗独立脚本（支持所有城市 / 指定城市 / 指定文件）

用法:
  # 清洗 data/raw/ 下所有新增城市（推荐，自动检测）
  python scripts/data_cleaner.py

  # 只清洗指定城市
  python scripts/data_cleaner.py --cities 天津 郑州 重庆

  # 清洗单个文件
  python scripts/data_cleaner.py --input data/raw/boss_天津.json

  # 强制重新清洗（覆盖已有 cleaned 文件）
  python scripts/data_cleaner.py --force

  # 保留 _raw 字段（默认剔除）
  python scripts/data_cleaner.py --keep-raw

  # 不预构建 jd_text 字段
  python scripts/data_cleaner.py --no-jd-text

  # 保留 skills 为空的数据
  python scripts/data_cleaner.py --keep-empty-skills
"""
import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data_processing.data_cleaner import JobDataCleaner

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def clean_city_file(input_file: Path, output_dir: Path, extra_config: dict = None) -> dict:
    """清洗单个城市文件，输出到 data/cleaned/"""
    city_name = input_file.stem.replace('boss_', '')
    output_file = output_dir / f'boss_{city_name}_cleaned.json'

    # 若已有 cleaned 文件则跳过（避免重复清洗）
    if output_file.exists():
        try:
            with open(output_file, 'r', encoding='utf-8') as _f:
                existing_count = len(json.load(_f))
            print(f"  ⏭️  跳过 {city_name}（已存在 {existing_count:,} 条，若需重新清洗请先删除该文件）")
        except Exception:
            existing_count = 0
            print(f"  ⚠️  跳过 {city_name}（cleaned 文件存在但无法解析，建议用 --force 重新清洗）")
        return {'city': city_name, 'skipped': True, 'cleaned': existing_count}

    config = JobDataCleaner.get_default_config()
    if extra_config:
        config.update(extra_config)

    cleaner = JobDataCleaner(config=config)
    print(f"\n🔧 清洗: {city_name} ({input_file.name})")
    stats = cleaner.clean_dataset(input_file, output_file)
    stats['city'] = city_name
    print(cleaner.generate_report())
    return stats


def main():
    parser = argparse.ArgumentParser(description='招聘数据清洗脚本')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--cities', nargs='+', help='指定要清洗的城市名称列表，如: --cities 天津 郑州 重庆')
    group.add_argument('--input', type=str, help='指定单个原始文件路径，如: --input data/raw/boss_天津.json')
    parser.add_argument('--force', action='store_true', help='强制重新清洗（覆盖已有 cleaned 文件）')
    parser.add_argument('--keep-raw', action='store_true', help='保留 _raw 字段（默认剔除以减小文件体积）')
    parser.add_argument('--no-jd-text', action='store_true', help='不预构建 jd_text 字段')
    parser.add_argument('--keep-empty-skills', action='store_true', help='保留 skills 为空的数据')
    args = parser.parse_args()

    raw_dir     = project_root / 'data' / 'raw'
    cleaned_dir = project_root / 'data' / 'cleaned'
    cleaned_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("📦 招聘数据清洗工具")
    print("=" * 70)

    # ── 确定待清洗文件列表 ─────────────────────────────────────────
    if args.input:
        input_path = project_root / args.input
        if not input_path.exists():
            print(f"❌ 文件不存在: {input_path}")
            sys.exit(1)
        files_to_clean = [input_path]

    elif args.cities:
        files_to_clean = []
        for city in args.cities:
            f = raw_dir / f'boss_{city}.json'
            if not f.exists():
                print(f"⚠️  未找到 {city} 的原始数据文件: {f}")
            else:
                files_to_clean.append(f)
        if not files_to_clean:
            print("❌ 指定的城市均未找到对应原始文件，请检查 data/raw/ 目录")
            sys.exit(1)

    else:
        # 自动检测 data/raw/ 下所有 boss_*.json
        files_to_clean = sorted(raw_dir.glob('boss_*.json'))
        if not files_to_clean:
            print(f"❌ data/raw/ 下未找到任何 boss_*.json 文件")
            sys.exit(1)

    print(f"\n共发现 {len(files_to_clean)} 个待处理文件:\n")
    for f in files_to_clean:
        cleaned_file = cleaned_dir / f'boss_{f.stem.replace("boss_", "")}_cleaned.json'
        status = "✅ 已清洗" if cleaned_file.exists() and not args.force else "🔧 待清洗"
        print(f"  {status}  {f.name}")

    # 强制重清洗时，删除已有 cleaned 文件
    if args.force:
        print("\n⚠️  --force 模式：将覆盖已有的 cleaned 文件")

    print()

    # ── 构建额外配置覆盖 ──────────────────────────────────────────
    extra_config = {}
    if args.keep_raw:
        extra_config['strip_raw'] = False
    if args.no_jd_text:
        extra_config['build_jd_text'] = False
    if args.keep_empty_skills:
        extra_config['keep_empty_skills'] = True

    # ── 执行清洗 ──────────────────────────────────────────────────
    all_stats = []
    for f in files_to_clean:
        if args.force:
            city_name = f.stem.replace('boss_', '')
            old = cleaned_dir / f'boss_{city_name}_cleaned.json'
            if old.exists():
                try:
                    old.unlink()
                except OSError as e:
                    print(f"  ❌ 无法删除旧文件 {old.name}: {e}")
                    continue
        try:
            stats = clean_city_file(f, cleaned_dir, extra_config=extra_config)
        except Exception as e:
            city_name = f.stem.replace('boss_', '')
            logger.error(f"清洗 {f.name} 时发生错误: {e}", exc_info=True)
            print(f"  ❌ {city_name} 清洗失败: {e}")
            stats = {'city': city_name, 'error': str(e), 'total': 0, 'cleaned': 0}
        all_stats.append(stats)

    # ── 汇总 ──────────────────────────────────────────────────────
    processed = [s for s in all_stats if not s.get('skipped') and not s.get('error')]
    skipped   = [s for s in all_stats if s.get('skipped')]
    failed    = [s for s in all_stats if s.get('error')]

    print("\n" + "=" * 70)
    print("📊 清洗汇总")
    print("=" * 70)

    if not processed and not skipped:
        print("  （无任何城市被处理）")
    else:
        # 本次新处理的城市
        if processed:
            total_raw     = sum(s.get('total',   0) for s in processed)
            total_cleaned = sum(s.get('cleaned', 0) for s in processed)
            for s in processed:
                city  = s.get('city', '?')
                total = s.get('total', 0)
                clean = s.get('cleaned', 0)
                rate  = clean / total * 100 if total else 0
                print(f"  🔧 {city:<8} {total:>8,} → {clean:>8,}  保留率 {rate:.1f}%")
            print("-" * 70)
            rate_all = total_cleaned / total_raw * 100 if total_raw else 0
            print(f"  {'本次合计':<7} {total_raw:>8,} → {total_cleaned:>8,}  保留率 {rate_all:.1f}%")

        # 已跳过的城市（已有 cleaned 文件）
        if skipped:
            if processed:
                print()
            for s in skipped:
                city  = s.get('city', '?')
                clean = s.get('cleaned', 0)
                print(f"  ⏭️  {city:<8} {'(已跳过)':>10}   现有 {clean:,} 条")

        # 失败的城市
        if failed:
            print()
            for s in failed:
                city = s.get('city', '?')
                err  = s.get('error', '未知错误')
                print(f"  ❌ {city:<8} {'(失败)':>10}   {err}")

        # 更新并保存汇总统计（合并历史数据）
        summary_file = cleaned_dir / 'cleaning_summary.json'
        existing_summary = {}
        if summary_file.exists():
            try:
                existing_summary = json.loads(summary_file.read_text(encoding='utf-8'))
            except Exception:
                pass

        existing_cities = {c['city']: c for c in existing_summary.get('cities', [])}
        for s in processed:
            existing_cities[s['city']] = s
        # 跳过的城市用旧数据（existing_summary 里已有）保持不变
        merged_stats = list(existing_cities.values())
        merged_total = sum(s.get('cleaned', 0) for s in merged_stats if not s.get('skipped'))
        merged_raw   = sum(s.get('total',   0) for s in merged_stats if not s.get('skipped'))

        if processed:
            summary_file.write_text(
                json.dumps({
                    'last_updated': datetime.now().isoformat(),
                    'cities': merged_stats,
                    'total': {
                        'total_raw':     merged_raw,
                        'total_cleaned': merged_total,
                        'retention_rate': merged_total / merged_raw if merged_raw else 0
                    }
                }, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
            print(f"\n✅ cleaned 文件保存在: {cleaned_dir}")
            print(f"📄 汇总统计保存在: {summary_file.name}")
        else:
            print(f"\n💡 所有城市均已清洗，无需重新处理。如需强制重清洗请加 --force")

    print("\n下一步: python scripts/enhance_with_qwen3.py")


if __name__ == '__main__':
    main()
