"""
从技能词典生成爬虫关键词列表
根据热度、级别筛选高价值关键词
"""
import json
import sys
sys.path.append('.')

def generate_crawl_keywords():
    """生成爬虫关键词列表"""
    
    # 1. 加载技能词典
    with open('data/skill_dict/skill_taxonomy.json', 'r', encoding='utf-8') as f:
        skill_dict = json.load(f)
    
    # 2. 提取所有技能
    all_skills = []
    for category_key, skills_list in skill_dict['技能分类体系'].items():
        category_name = category_key.split('_')[1] if '_' in category_key else category_key
        for skill in skills_list:
            skill['category'] = category_name
            all_skills.append(skill)
    
    print(f"技能词典总数: {len(all_skills)}")
    
    # 3. 筛选策略1: 高热度核心技能
    high_value_skills = [
        s for s in all_skills 
        if s.get('hot_score', 0) >= 85 and s.get('level') in ['核心', '常用']
    ]
    
    # 4. 筛选策略2: 框架类技能(搜索结果质量高)
    framework_categories = ['后端框架', '前端技术', '数据库', '云原生与DevOps']
    framework_skills = [
        s for s in all_skills
        if s.get('category') in framework_categories and s.get('hot_score', 0) >= 70
    ]
    
    # 5. 组合去重
    selected_skills = {s['name']: s for s in high_value_skills + framework_skills}
    
    # 6. 按分类整理
    keywords_by_category = {}
    for skill in selected_skills.values():
        cat = skill['category']
        if cat not in keywords_by_category:
            keywords_by_category[cat] = []
        keywords_by_category[cat].append({
            'name': skill['name'],
            'hot_score': skill.get('hot_score', 0),
            'level': skill.get('level', '')
        })
    
    # 7. 每个分类排序并选择Top N
    final_keywords = []
    print("\n" + "="*60)
    print("推荐爬虫关键词列表 (按分类)")
    print("="*60)
    
    for cat, skills in sorted(keywords_by_category.items()):
        # 按热度排序，每个分类取Top 8
        top_skills = sorted(skills, key=lambda x: x['hot_score'], reverse=True)[:8]
        
        print(f"\n【{cat}】({len(top_skills)}个)")
        for skill in top_skills:
            final_keywords.append(skill['name'])
            print(f"  - {skill['name']:20s} (热度:{skill['hot_score']}, 级别:{skill['level']})")
    
    # 8. 额外添加岗位类型关键词
    job_type_keywords = [
        "Python开发", "Java开发", "前端开发", "后端开发",
        "算法工程师", "数据分析", "大数据开发", "测试工程师",
        "运维工程师", "全栈工程师", "Go开发", "移动开发"
    ]
    
    print(f"\n【岗位类型】({len(job_type_keywords)}个)")
    for job in job_type_keywords:
        print(f"  - {job}")
        final_keywords.append(job)
    
    # 9. 输出总结
    print("\n" + "="*60)
    print(f"总关键词数: {len(final_keywords)}")
    print("="*60)
    
    # 10. 数据量估算
    print("\n【数据量估算】")
    print(f"关键词数: {len(final_keywords)}")
    print(f"每个关键词抓取: 300条 (Boss翻到底)")
    print(f"理论总数: {len(final_keywords)} × 300 = {len(final_keywords) * 300:,}条")
    print(f"去重后预计: {int(len(final_keywords) * 300 * 0.5):,} - {int(len(final_keywords) * 300 * 0.7):,}条")
    
    # 11. 保存到文件
    output = {
        'skill_keywords': [k for k in final_keywords if k not in job_type_keywords],
        'job_type_keywords': job_type_keywords,
        'all_keywords': final_keywords,
        'cities': ["北京", "上海", "深圳", "杭州", "广州", "成都"],
        'estimated_total': len(final_keywords) * 300,
        'estimated_after_dedup': int(len(final_keywords) * 300 * 0.6)
    }
    
    with open('data/crawl_keywords.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n[OK] 关键词列表已保存到: data/crawl_keywords.json")
    
    return final_keywords

if __name__ == "__main__":
    keywords = generate_crawl_keywords()
